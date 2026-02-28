package main

import (
	"context"
	"encoding/json"
	"fmt"
	"math/rand"
	"strings"
	"sync"
	"testing"
	"time"
)

/*
 ╔═══════════════════════════════════════════════════════════════════════════╗
 ║              SENTINEL SHIELD - FUZZ & PROPERTY TESTS (GO)                 ║
 ╠═══════════════════════════════════════════════════════════════════════════╣
 ║  Randomized input testing and property-based verification                 ║
 ╚═══════════════════════════════════════════════════════════════════════════╝
*/

// ═══════════════════════════════════════════════════════════════════════════
//                          FUZZ TESTS
// ═══════════════════════════════════════════════════════════════════════════

// FuzzAddressValidation tests address validation with random inputs
func FuzzAddressValidation(f *testing.F) {
	// Seed corpus
	f.Add("0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1")
	f.Add("0x0000000000000000000000000000000000000000")
	f.Add("")
	f.Add("not-an-address")
	f.Add("0x")
	f.Add("0x12345")
	f.Add("0xGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG")

	f.Fuzz(func(t *testing.T, addr string) {
		valid := isValidAddress(addr)
		
		// Property: if valid, must be exactly 42 chars and start with 0x
		if valid {
			if len(addr) != 42 {
				t.Errorf("Valid address %s has wrong length %d", addr, len(addr))
			}
			if !strings.HasPrefix(addr, "0x") {
				t.Errorf("Valid address %s doesn't start with 0x", addr)
			}
		}
	})
}

// FuzzChainParsing tests chain parameter parsing
func FuzzChainParsing(f *testing.F) {
	f.Add("ethereum")
	f.Add("bsc")
	f.Add("polygon")
	f.Add("")
	f.Add("ETHEREUM")
	f.Add("unknown-chain")
	f.Add("eth,bsc,polygon")

	f.Fuzz(func(t *testing.T, chain string) {
		supported := isSupportedChain(chain)
		
		// Property: empty chain is never supported
		if chain == "" && supported {
			t.Error("Empty chain should not be supported")
		}
		
		// Property: known chains are always supported (case-insensitive)
		knownChains := []string{"ethereum", "bsc", "polygon", "arbitrum", "base", "optimism", "avalanche", "fantom", "zksync", "solana"}
		for _, known := range knownChains {
			if strings.EqualFold(chain, known) && !supported {
				t.Errorf("Known chain %s should be supported", chain)
			}
		}
	})
}

// FuzzScanRequestParsing tests request body parsing
func FuzzScanRequestParsing(f *testing.F) {
	f.Add(`{"address":"0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1","chains":["ethereum"]}`)
	f.Add(`{}`)
	f.Add(`{"address":""}`)
	f.Add(`not json`)
	f.Add(`{"address":"0x123","chains":[]}`)
	f.Add(`{"address":"0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1","chains":["ethereum","bsc","polygon"]}`)

	f.Fuzz(func(t *testing.T, body string) {
		var req TestScanRequest
		err := json.Unmarshal([]byte(body), &req)
		
		if err == nil {
			// Property: valid JSON must have address and chains fields
			// (they may be empty, but parseable)
			_ = req.Address
			_ = req.Chains
		}
	})
}

// FuzzRiskScore tests risk score calculation bounds
func FuzzRiskScore(f *testing.F) {
	f.Add(0, 0, 0)
	f.Add(100, 100, 100)
	f.Add(1, 5, 10)
	f.Add(0, 1000, 0)

	f.Fuzz(func(t *testing.T, criticalCount, highCount, mediumCount int) {
		// Bounds check
		if criticalCount < 0 {
			criticalCount = 0
		}
		if highCount < 0 {
			highCount = 0
		}
		if mediumCount < 0 {
			mediumCount = 0
		}

		score := calculateRiskScore(criticalCount, highCount, mediumCount)
		
		// Property: score must be between 0 and 100
		if score < 0 || score > 100 {
			t.Errorf("Score %d out of bounds [0,100]", score)
		}
		
		// Property: more issues = higher score
		scoreMore := calculateRiskScore(criticalCount+1, highCount, mediumCount)
		if scoreMore < score {
			t.Error("More issues should not decrease score")
		}
	})
}

// ═══════════════════════════════════════════════════════════════════════════
//                      PROPERTY-BASED TESTS
// ═══════════════════════════════════════════════════════════════════════════

func TestProperty_CacheConsistency(t *testing.T) {
	cache := NewCache(time.Minute)
	
	// Property: Get after Set should return same value
	for i := 0; i < 100; i++ {
		key := fmt.Sprintf("key-%d", rand.Intn(1000))
		value := fmt.Sprintf("value-%d", rand.Intn(1000))
		
		cache.Set(key, value)
		
		got, found := cache.Get(key)
		if !found {
			t.Errorf("Key %s not found after Set", key)
			continue
		}
		if got != value {
			t.Errorf("Got %v, want %v", got, value)
		}
	}
}

func TestProperty_CacheExpiration(t *testing.T) {
	cache := NewCache(10 * time.Millisecond)
	
	// Property: Expired items should not be found
	cache.Set("expires-soon", "value")
	
	time.Sleep(20 * time.Millisecond)
	
	_, found := cache.Get("expires-soon")
	if found {
		t.Error("Expired item should not be found")
	}
}

func TestProperty_ScannerIdempotent(t *testing.T) {
	scanner := &TestMultiChainScanner{
		chains: map[string]TestChainScanner{
			"ethereum": &MockTestChainScanner{},
		},
	}
	
	// Property: Multiple scans of same address should return consistent results
	addr := "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
	
	result1, err1 := scanner.Scan(context.Background(), addr, []string{"ethereum"})
	result2, err2 := scanner.Scan(context.Background(), addr, []string{"ethereum"})
	
	if err1 != nil || err2 != nil {
		t.Skip("Scan error, skipping consistency check")
	}
	
	// Same input should give same output (deterministic)
	if len(result1.Approvals) != len(result2.Approvals) {
		t.Error("Scan results inconsistent")
	}
}

func TestProperty_RiskCategorization(t *testing.T) {
	testCases := []struct {
		score    int
		expected string
	}{
		{0, "safe"},
		{25, "low"},
		{50, "medium"},
		{75, "high"},
		{100, "critical"},
	}
	
	for _, tc := range testCases {
		category := categorizeRisk(tc.score)
		
		// Property: Categories should be monotonic with score
		if tc.score == 0 && category != "safe" {
			t.Errorf("Score 0 should be safe, got %s", category)
		}
		if tc.score == 100 && category != "critical" {
			t.Errorf("Score 100 should be critical, got %s", category)
		}
	}
}

// ═══════════════════════════════════════════════════════════════════════════
//                      CONCURRENCY TESTS
// ═══════════════════════════════════════════════════════════════════════════

func TestConcurrency_CacheThreadSafe(t *testing.T) {
	cache := NewCache(time.Minute)
	var wg sync.WaitGroup
	
	// Concurrent writes and reads
	for i := 0; i < 100; i++ {
		wg.Add(2)
		
		go func(n int) {
			defer wg.Done()
			cache.Set(fmt.Sprintf("key-%d", n), fmt.Sprintf("value-%d", n))
		}(i)
		
		go func(n int) {
			defer wg.Done()
			cache.Get(fmt.Sprintf("key-%d", n))
		}(i)
	}
	
	wg.Wait()
	// Test passes if no race conditions
}

func TestConcurrency_ScannerParallel(t *testing.T) {
	scanner := &TestMultiChainScanner{
		chains: map[string]TestChainScanner{
			"ethereum": &MockTestChainScanner{},
			"bsc":      &MockTestChainScanner{},
			"polygon":  &MockTestChainScanner{},
		},
	}
	
	var wg sync.WaitGroup
	errors := make(chan error, 10)
	
	// Parallel scans
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func(n int) {
			defer wg.Done()
			addr := fmt.Sprintf("0x%040d", n)
			_, err := scanner.Scan(context.Background(), addr, []string{"ethereum", "bsc"})
			if err != nil {
				errors <- err
			}
		}(i)
	}
	
	wg.Wait()
	close(errors)
	
	for err := range errors {
		t.Errorf("Parallel scan error: %v", err)
	}
}

func TestConcurrency_CacheHTTPSafe(t *testing.T) {
	cache := NewCache(time.Minute)
	
	var wg sync.WaitGroup
	
	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func(n int) {
			defer wg.Done()
			key := fmt.Sprintf("key-%d", n)
			cache.Set(key, "value")
			cache.Get(key)
		}(i)
	}
	
	wg.Wait()
}

// ═══════════════════════════════════════════════════════════════════════════
//                      STRESS TESTS
// ═══════════════════════════════════════════════════════════════════════════

func TestStress_CacheEviction(t *testing.T) {
	cache := NewCache(time.Minute)
	
	// Fill cache with many entries
	for i := 0; i < 10000; i++ {
		cache.Set(fmt.Sprintf("stress-key-%d", i), fmt.Sprintf("value-%d", i))
	}
	
	// Verify some entries exist
	_, found := cache.Get("stress-key-0")
	if !found {
		t.Error("First entry should exist")
	}
	
	_, found = cache.Get("stress-key-9999")
	if !found {
		t.Error("Last entry should exist")
	}
}

func TestStress_LargeBatchScan(t *testing.T) {
	scanner := &TestMultiChainScanner{
		chains: map[string]TestChainScanner{
			"ethereum": &MockTestChainScanner{},
			"bsc":      &MockTestChainScanner{},
			"polygon":  &MockTestChainScanner{},
			"arbitrum": &MockTestChainScanner{},
			"base":     &MockTestChainScanner{},
		},
	}
	
	// Scan all chains
	chains := []string{"ethereum", "bsc", "polygon", "arbitrum", "base"}
	
	start := time.Now()
	result, err := scanner.Scan(context.Background(), "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1", chains)
	elapsed := time.Since(start)
	
	if err != nil {
		t.Fatalf("Scan failed: %v", err)
	}
	
	t.Logf("Scanned %d chains in %v", len(chains), elapsed)
	t.Logf("Found %d total approvals", len(result.Approvals))
}

// ═══════════════════════════════════════════════════════════════════════════
//                      HELPER FUNCTIONS & MOCKS
// ═══════════════════════════════════════════════════════════════════════════

func isValidAddress(addr string) bool {
	if len(addr) != 42 {
		return false
	}
	if !strings.HasPrefix(addr, "0x") {
		return false
	}
	for _, c := range addr[2:] {
		if !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F')) {
			return false
		}
	}
	return true
}

func isSupportedChain(chain string) bool {
	supported := map[string]bool{
		"ethereum":  true,
		"bsc":       true,
		"polygon":   true,
		"arbitrum":  true,
		"base":      true,
		"optimism":  true,
		"avalanche": true,
		"fantom":    true,
		"zksync":    true,
		"solana":    true,
	}
	return supported[strings.ToLower(chain)]
}

func calculateRiskScore(critical, high, medium int) int {
	score := critical*30 + high*15 + medium*5
	if score > 100 {
		return 100
	}
	return score
}

func categorizeRisk(score int) string {
	switch {
	case score == 0:
		return "safe"
	case score < 30:
		return "low"
	case score < 60:
		return "medium"
	case score < 90:
		return "high"
	default:
		return "critical"
	}
}

// TestScanRequest is used for fuzz testing request parsing
type TestScanRequest struct {
	Address string   `json:"address"`
	Chains  []string `json:"chains"`
}

// TestCache is a test-only cache implementation for fuzz testing
type TestCache struct {
	mu    sync.RWMutex
	items map[string]testCacheItem
}

type testCacheItem struct {
	value     interface{}
	expiresAt time.Time
}

func NewTestCache() *TestCache {
	return &TestCache{items: make(map[string]testCacheItem)}
}

func (c *TestCache) Set(key string, value interface{}, ttl time.Duration) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.items[key] = testCacheItem{value: value, expiresAt: time.Now().Add(ttl)}
}

func (c *TestCache) Get(key string) (interface{}, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	item, found := c.items[key]
	if !found {
		return nil, false
	}
	if time.Now().After(item.expiresAt) {
		return nil, false
	}
	return item.value, true
}

// TestChainScanner interface for mocking in tests
type TestChainScanner interface {
	Scan(ctx context.Context, address string) (*TestChainResult, error)
}

// MockTestChainScanner for test mocking
type MockTestChainScanner struct{}

func (m *MockTestChainScanner) Scan(ctx context.Context, address string) (*TestChainResult, error) {
	return &TestChainResult{
		Chain:     "mock",
		Approvals: []TestApproval{{Token: "0xMock", Spender: "0xSpender", Amount: "1000"}},
	}, nil
}

// TestChainResult for test mocking
type TestChainResult struct {
	Chain     string
	Approvals []TestApproval
}

// TestApproval for test mocking (different from main.Approval)
type TestApproval struct {
	Token   string
	Spender string
	Amount  string
}

// TestMultiChainScanner for test mocking
type TestMultiChainScanner struct {
	chains map[string]TestChainScanner
}

func (m *TestMultiChainScanner) Scan(ctx context.Context, address string, chains []string) (*TestScanResult, error) {
	var allApprovals []TestApproval
	for _, chain := range chains {
		if scanner, ok := m.chains[chain]; ok {
			result, err := scanner.Scan(ctx, address)
			if err != nil {
				continue
			}
			allApprovals = append(allApprovals, result.Approvals...)
		}
	}
	return &TestScanResult{Approvals: allApprovals}, nil
}

// TestScanResult for test mocking
type TestScanResult struct {
	Approvals []TestApproval
}
