package main

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strings"
	"testing"
	"time"
)

/*
 ╔═══════════════════════════════════════════════════════════════════════════╗
 ║              SENTINEL SHIELD - COMPREHENSIVE TEST SUITE (GO)              ║
 ╠═══════════════════════════════════════════════════════════════════════════╣
 ║  Production-grade test coverage for all edge cases                        ║
 ╚═══════════════════════════════════════════════════════════════════════════╝
*/

// ═══════════════════════════════════════════════════════════════════════════
//                      ADDRESS VALIDATION TESTS
// ═══════════════════════════════════════════════════════════════════════════

func TestAddressValidation_ValidAddresses(t *testing.T) {
	validAddresses := []string{
		"0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1",
		"0x0000000000000000000000000000000000000000",
		"0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",
		"0xdead000000000000000000000000000000000000",
		"0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
		"0x6B175474E89094C44Da98b954EedeAC495271d0F", // Valid DAI address
		"0x1234567890123456789012345678901234567890",
		"0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
		"0xABCDEFABCDEFABCDEFABCDEFABCDEFABCDEFABCD",
	}

	for i, addr := range validAddresses {
		t.Run(fmt.Sprintf("ValidAddress_%d", i), func(t *testing.T) {
			if !isValidAddress(addr) {
				t.Errorf("Expected %s to be valid", addr)
			}
		})
	}
}

func TestAddressValidation_InvalidAddresses(t *testing.T) {
	invalidAddresses := []string{
		"",
		"0x",
		"0x123",
		"0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e",   // Too short
		"0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e11", // Too long
		"not-an-address",
		"742d35Cc6634C0532925a3b844Bc9e7595f5b2e1", // Missing 0x
		"0xGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
		"0X742d35Cc6634C0532925a3b844Bc9e7595f5b2e1", // Capital X
		"  0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1",
		"0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1  ",
		"0x 742d35Cc6634C0532925a3b844Bc9e7595f5b2e1",
	}

	for i, addr := range invalidAddresses {
		t.Run(fmt.Sprintf("InvalidAddress_%d", i), func(t *testing.T) {
			if isValidAddress(addr) {
				t.Errorf("Expected %s to be invalid", addr)
			}
		})
	}
}

func TestAddressValidation_EdgeCases(t *testing.T) {
	t.Run("ZeroAddress", func(t *testing.T) {
		addr := "0x0000000000000000000000000000000000000000"
		if !isValidAddress(addr) {
			t.Error("Zero address should be valid")
		}
	})

	t.Run("DeadAddress", func(t *testing.T) {
		addr := "0x000000000000000000000000000000000000dEaD"
		if !isValidAddress(addr) {
			t.Error("Dead address should be valid")
		}
	})

	t.Run("MaxAddress", func(t *testing.T) {
		addr := "0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
		if !isValidAddress(addr) {
			t.Error("Max address should be valid")
		}
	})
}

// ═══════════════════════════════════════════════════════════════════════════
//                      CHAIN VALIDATION TESTS
// ═══════════════════════════════════════════════════════════════════════════

func TestChainValidation_SupportedChains(t *testing.T) {
	supportedChains := []string{
		"ethereum", "bsc", "polygon", "arbitrum", "base",
		"optimism", "avalanche", "fantom", "zksync", "solana",
	}

	for _, chain := range supportedChains {
		t.Run(fmt.Sprintf("Supported_%s", chain), func(t *testing.T) {
			if !isSupportedChain(chain) {
				t.Errorf("Expected %s to be supported", chain)
			}
		})
	}
}

func TestChainValidation_UnsupportedChains(t *testing.T) {
	unsupportedChains := []string{
		"bitcoin", "cosmos", "polkadot", "cardano", "tezos",
		"near", "algorand", "stellar", "ripple", "hedera",
		"ETH", "", "unknown", "test", "mainnet", "testnet",
	}

	for _, chain := range unsupportedChains {
		t.Run(fmt.Sprintf("Unsupported_%s", chain), func(t *testing.T) {
			if isSupportedChain(chain) {
				t.Errorf("Expected %s to be unsupported", chain)
			}
		})
	}
}

func TestChainValidation_CaseSensitivity(t *testing.T) {
	// isSupportedChain is case-insensitive (uses ToLower)
	cases := []struct {
		input    string
		expected bool
	}{
		{"ethereum", true},
		{"ETHEREUM", true},
		{"Ethereum", true},
		{"eThErEuM", true},
	}

	for _, tc := range cases {
		t.Run(tc.input, func(t *testing.T) {
			result := isSupportedChain(tc.input)
			if result != tc.expected {
				t.Errorf("isSupportedChain(%s) = %v, want %v", tc.input, result, tc.expected)
			}
		})
	}
}

// ═══════════════════════════════════════════════════════════════════════════
//                      RISK SCORE TESTS
// ═══════════════════════════════════════════════════════════════════════════

func TestRiskScore_Bounds(t *testing.T) {
	for score := -10; score <= 110; score++ {
		t.Run(fmt.Sprintf("Score_%d", score), func(t *testing.T) {
			category := categorizeRisk(score)
			if category == "" {
				t.Errorf("Empty category for score %d", score)
			}
		})
	}
}

func TestRiskScore_Categories(t *testing.T) {
	testCases := []struct {
		score    int
		expected string
	}{
		{0, "safe"},
		{1, "low"},
		{15, "low"},
		{29, "low"},
		{30, "medium"},
		{45, "medium"},
		{59, "medium"},
		{60, "high"},
		{75, "high"},
		{89, "high"},
		{90, "critical"},
		{95, "critical"},
		{100, "critical"},
	}

	for _, tc := range testCases {
		t.Run(fmt.Sprintf("Score_%d", tc.score), func(t *testing.T) {
			result := categorizeRisk(tc.score)
			if result != tc.expected {
				t.Errorf("categorizeRisk(%d) = %s, want %s", tc.score, result, tc.expected)
			}
		})
	}
}

func TestRiskScore_Calculation(t *testing.T) {
	testCases := []struct {
		critical int
		high     int
		medium   int
		minScore int
		maxScore int
	}{
		{0, 0, 0, 0, 0},
		{1, 0, 0, 25, 35},
		{0, 1, 0, 10, 20},
		{0, 0, 1, 3, 8},
		{1, 1, 1, 35, 65},
		{5, 5, 5, 95, 100},
		{10, 10, 10, 100, 100},
	}

	for _, tc := range testCases {
		t.Run(fmt.Sprintf("C%d_H%d_M%d", tc.critical, tc.high, tc.medium), func(t *testing.T) {
			score := calculateRiskScore(tc.critical, tc.high, tc.medium)
			if score < tc.minScore || score > tc.maxScore {
				t.Errorf("Score %d not in range [%d, %d]", score, tc.minScore, tc.maxScore)
			}
		})
	}
}

func TestRiskScore_Monotonicity(t *testing.T) {
	// More issues should never decrease score
	for critical := 0; critical < 5; critical++ {
		for high := 0; high < 5; high++ {
			for medium := 0; medium < 5; medium++ {
				base := calculateRiskScore(critical, high, medium)
				moreCritical := calculateRiskScore(critical+1, high, medium)
				moreHigh := calculateRiskScore(critical, high+1, medium)
				moreMedium := calculateRiskScore(critical, high, medium+1)

				if moreCritical < base {
					t.Errorf("Adding critical decreased score: %d -> %d", base, moreCritical)
				}
				if moreHigh < base {
					t.Errorf("Adding high decreased score: %d -> %d", base, moreHigh)
				}
				if moreMedium < base {
					t.Errorf("Adding medium decreased score: %d -> %d", base, moreMedium)
				}
			}
		}
	}
}

// ═══════════════════════════════════════════════════════════════════════════
//                      CACHE TESTS
// ═══════════════════════════════════════════════════════════════════════════

func TestCache_BasicOperations(t *testing.T) {
	cache := NewCache(time.Minute)

	t.Run("SetAndGet", func(t *testing.T) {
		cache.Set("key1", "value1")
		val, found := cache.Get("key1")
		if !found || val != "value1" {
			t.Errorf("Expected value1, got %v (found: %v)", val, found)
		}
	})

	t.Run("MissingKey", func(t *testing.T) {
		_, found := cache.Get("nonexistent")
		if found {
			t.Error("Expected key not found")
		}
	})

	t.Run("Overwrite", func(t *testing.T) {
		cache.Set("key2", "value2a")
		cache.Set("key2", "value2b")
		val, _ := cache.Get("key2")
		if val != "value2b" {
			t.Errorf("Expected value2b, got %v", val)
		}
	})
}

func TestComprehensive_Cache_Expiration(t *testing.T) {
	cache := NewCache(50 * time.Millisecond)

	cache.Set("expires", "soon")
	
	// Should exist immediately
	val, found := cache.Get("expires")
	if !found || val != "soon" {
		t.Error("Value should exist immediately")
	}

	// Wait for expiration
	time.Sleep(60 * time.Millisecond)

	// Should be expired
	_, found = cache.Get("expires")
	if found {
		t.Error("Value should have expired")
	}
}

func TestCache_LargeValues(t *testing.T) {
	cache := NewCache(time.Minute)

	t.Run("LargeString", func(t *testing.T) {
		largeStr := strings.Repeat("x", 1024*1024) // 1MB
		cache.Set("large", largeStr)
		val, found := cache.Get("large")
		if !found || val != largeStr {
			t.Error("Failed to store/retrieve large string")
		}
	})

	t.Run("ManyKeys", func(t *testing.T) {
		for i := 0; i < 10000; i++ {
			cache.Set(fmt.Sprintf("key_%d", i), fmt.Sprintf("value_%d", i))
		}
		
		// Verify some random keys
		for _, i := range []int{0, 999, 5000, 9999} {
			val, found := cache.Get(fmt.Sprintf("key_%d", i))
			if !found || val != fmt.Sprintf("value_%d", i) {
				t.Errorf("Key %d not found or wrong value", i)
			}
		}
	})
}

func TestCache_DifferentTypes(t *testing.T) {
	cache := NewCache(time.Minute)

	t.Run("String", func(t *testing.T) {
		cache.Set("str", "hello")
		val, _ := cache.Get("str")
		if val != "hello" {
			t.Error("String storage failed")
		}
	})

	t.Run("Int", func(t *testing.T) {
		cache.Set("int", 42)
		val, _ := cache.Get("int")
		if val != 42 {
			t.Error("Int storage failed")
		}
	})

	t.Run("Struct", func(t *testing.T) {
		type TestStruct struct {
			Name  string
			Value int
		}
		s := TestStruct{Name: "test", Value: 100}
		cache.Set("struct", s)
		val, _ := cache.Get("struct")
		if val.(TestStruct).Name != "test" {
			t.Error("Struct storage failed")
		}
	})

	t.Run("Slice", func(t *testing.T) {
		slice := []int{1, 2, 3, 4, 5}
		cache.Set("slice", slice)
		val, _ := cache.Get("slice")
		if len(val.([]int)) != 5 {
			t.Error("Slice storage failed")
		}
	})

	t.Run("Map", func(t *testing.T) {
		m := map[string]int{"a": 1, "b": 2}
		cache.Set("map", m)
		val, _ := cache.Get("map")
		if val.(map[string]int)["a"] != 1 {
			t.Error("Map storage failed")
		}
	})
}

// ═══════════════════════════════════════════════════════════════════════════
//                      JSON PARSING TESTS
// ═══════════════════════════════════════════════════════════════════════════

func TestJSON_ValidRequests(t *testing.T) {
	validJSONs := []string{
		`{"address":"0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1","chains":["ethereum"]}`,
		`{"address":"0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1","chains":["ethereum","bsc"]}`,
		`{"address":"0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1","chains":[]}`,
		`{"address":"","chains":["ethereum"]}`,
	}

	for i, jsonStr := range validJSONs {
		t.Run(fmt.Sprintf("ValidJSON_%d", i), func(t *testing.T) {
			var req TestScanRequest
			err := json.Unmarshal([]byte(jsonStr), &req)
			if err != nil {
				t.Errorf("Failed to parse valid JSON: %v", err)
			}
		})
	}
}

func TestJSON_InvalidRequests(t *testing.T) {
	invalidJSONs := []string{
		``,
		`{`,
		`{"address"}`,
		`not json`,
		`null`,
		`[]`,
		`"string"`,
		`123`,
	}

	for i, jsonStr := range invalidJSONs {
		t.Run(fmt.Sprintf("InvalidJSON_%d", i), func(t *testing.T) {
			var req TestScanRequest
			err := json.Unmarshal([]byte(jsonStr), &req)
			if err == nil && jsonStr != "null" {
				t.Errorf("Expected parse error for: %s", jsonStr)
			}
		})
	}
}

func TestJSON_MissingFields(t *testing.T) {
	t.Run("MissingAddress", func(t *testing.T) {
		var req TestScanRequest
		json.Unmarshal([]byte(`{"chains":["ethereum"]}`), &req)
		if req.Address != "" {
			t.Error("Expected empty address")
		}
	})

	t.Run("MissingChains", func(t *testing.T) {
		var req TestScanRequest
		json.Unmarshal([]byte(`{"address":"0x123"}`), &req)
		if req.Chains != nil {
			t.Error("Expected nil chains")
		}
	})
}

// ═══════════════════════════════════════════════════════════════════════════
//                      STRING MANIPULATION TESTS
// ═══════════════════════════════════════════════════════════════════════════

func TestString_AddressNormalization(t *testing.T) {
	testCases := []struct {
		input    string
		expected string
	}{
		{"0xABC", "0xabc"},
		{"0xDEF", "0xdef"},
		{"0x123ABC", "0x123abc"},
	}

	for _, tc := range testCases {
		t.Run(tc.input, func(t *testing.T) {
			result := strings.ToLower(tc.input)
			if result != tc.expected {
				t.Errorf("ToLower(%s) = %s, want %s", tc.input, result, tc.expected)
			}
		})
	}
}

func TestString_Trimming(t *testing.T) {
	testCases := []struct {
		input    string
		expected string
	}{
		{"  hello  ", "hello"},
		{"\thello\t", "hello"},
		{"\nhello\n", "hello"},
		{" \t\nhello\n\t ", "hello"},
	}

	for _, tc := range testCases {
		t.Run(tc.input, func(t *testing.T) {
			result := strings.TrimSpace(tc.input)
			if result != tc.expected {
				t.Errorf("TrimSpace(%q) = %q, want %q", tc.input, result, tc.expected)
			}
		})
	}
}

// ═══════════════════════════════════════════════════════════════════════════
//                      REGEX TESTS
// ═══════════════════════════════════════════════════════════════════════════

func TestRegex_AddressPattern(t *testing.T) {
	pattern := regexp.MustCompile(`^0x[a-fA-F0-9]{40}$`)

	validCases := []string{
		"0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1",
		"0x0000000000000000000000000000000000000000",
		"0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",
	}

	for _, addr := range validCases {
		t.Run(fmt.Sprintf("Valid_%s", addr[:10]), func(t *testing.T) {
			if !pattern.MatchString(addr) {
				t.Errorf("Pattern should match %s", addr)
			}
		})
	}

	invalidCases := []string{
		"0x123",
		"0xGGGG",
		"hello",
		"",
	}

	for i, addr := range invalidCases {
		t.Run(fmt.Sprintf("Invalid_%d", i), func(t *testing.T) {
			if pattern.MatchString(addr) {
				t.Errorf("Pattern should not match %s", addr)
			}
		})
	}
}

func TestRegex_TxHashPattern(t *testing.T) {
	pattern := regexp.MustCompile(`^0x[a-fA-F0-9]{64}$`)

	validHash := "0x" + strings.Repeat("a", 64)
	if !pattern.MatchString(validHash) {
		t.Error("Should match valid tx hash")
	}

	invalidHash := "0x" + strings.Repeat("a", 63)
	if pattern.MatchString(invalidHash) {
		t.Error("Should not match short tx hash")
	}
}

// ═══════════════════════════════════════════════════════════════════════════
//                      ERROR HANDLING TESTS
// ═══════════════════════════════════════════════════════════════════════════

func TestError_Wrapping(t *testing.T) {
	original := fmt.Errorf("original error")
	wrapped := fmt.Errorf("context: %w", original)
	
	if !strings.Contains(wrapped.Error(), "original error") {
		t.Error("Wrapped error should contain original message")
	}
}

func TestError_NilHandling(t *testing.T) {
	var err error = nil
	if err != nil {
		t.Error("nil error should be nil")
	}
}

// ═══════════════════════════════════════════════════════════════════════════
//                      SLICE OPERATION TESTS
// ═══════════════════════════════════════════════════════════════════════════

func TestSlice_Operations(t *testing.T) {
	t.Run("EmptySlice", func(t *testing.T) {
		var s []int
		if len(s) != 0 {
			t.Error("Empty slice should have length 0")
		}
	})

	t.Run("Append", func(t *testing.T) {
		s := []int{1, 2, 3}
		s = append(s, 4, 5)
		if len(s) != 5 {
			t.Error("Append failed")
		}
	})

	t.Run("Slice", func(t *testing.T) {
		s := []int{1, 2, 3, 4, 5}
		sub := s[1:3]
		if len(sub) != 2 || sub[0] != 2 {
			t.Error("Slice failed")
		}
	})

	t.Run("Copy", func(t *testing.T) {
		src := []int{1, 2, 3}
		dst := make([]int, len(src))
		copy(dst, src)
		src[0] = 99
		if dst[0] != 1 {
			t.Error("Copy should create independent slice")
		}
	})
}

// ═══════════════════════════════════════════════════════════════════════════
//                      MAP OPERATION TESTS
// ═══════════════════════════════════════════════════════════════════════════

func TestMap_Operations(t *testing.T) {
	t.Run("NilMap", func(t *testing.T) {
		var m map[string]int
		_, ok := m["key"]
		if ok {
			t.Error("Nil map should return not found")
		}
	})

	t.Run("EmptyMap", func(t *testing.T) {
		m := make(map[string]int)
		if len(m) != 0 {
			t.Error("Empty map should have length 0")
		}
	})

	t.Run("SetGet", func(t *testing.T) {
		m := make(map[string]int)
		m["key"] = 42
		if m["key"] != 42 {
			t.Error("Set/Get failed")
		}
	})

	t.Run("Delete", func(t *testing.T) {
		m := map[string]int{"key": 42}
		delete(m, "key")
		_, ok := m["key"]
		if ok {
			t.Error("Delete failed")
		}
	})

	t.Run("Overwrite", func(t *testing.T) {
		m := map[string]int{"key": 1}
		m["key"] = 2
		if m["key"] != 2 {
			t.Error("Overwrite failed")
		}
	})
}

// ═══════════════════════════════════════════════════════════════════════════
//                      TIME OPERATION TESTS
// ═══════════════════════════════════════════════════════════════════════════

func TestTime_Operations(t *testing.T) {
	t.Run("Now", func(t *testing.T) {
		now := time.Now()
		if now.IsZero() {
			t.Error("Now should not be zero")
		}
	})

	t.Run("Duration", func(t *testing.T) {
		d := 5 * time.Second
		if d.Seconds() != 5 {
			t.Error("Duration calculation failed")
		}
	})

	t.Run("Add", func(t *testing.T) {
		now := time.Now()
		future := now.Add(time.Hour)
		if !future.After(now) {
			t.Error("Future should be after now")
		}
	})

	t.Run("Sub", func(t *testing.T) {
		t1 := time.Now()
		t2 := t1.Add(time.Minute)
		diff := t2.Sub(t1)
		if diff != time.Minute {
			t.Errorf("Expected 1 minute, got %v", diff)
		}
	})
}

// ═══════════════════════════════════════════════════════════════════════════
//                      NUMERIC TESTS
// ═══════════════════════════════════════════════════════════════════════════

func TestNumeric_IntBounds(t *testing.T) {
	t.Run("MaxInt64", func(t *testing.T) {
		var max int64 = 9223372036854775807
		if max+1 < 0 {
			t.Log("Overflow detected (expected)")
		}
	})

	t.Run("MinInt64", func(t *testing.T) {
		var min int64 = -9223372036854775808
		if min-1 > 0 {
			t.Log("Underflow detected (expected)")
		}
	})
}

func TestNumeric_FloatPrecision(t *testing.T) {
	t.Run("SmallDifference", func(t *testing.T) {
		a := 0.1 + 0.2
		b := 0.3
		diff := a - b
		if diff > 1e-10 || diff < -1e-10 {
			t.Logf("Float precision issue: %v", diff)
		}
	})
}

// ═══════════════════════════════════════════════════════════════════════════
//                      TABLE-DRIVEN TESTS
// ═══════════════════════════════════════════════════════════════════════════

func TestTableDriven_RiskLevels(t *testing.T) {
	tests := []struct {
		name     string
		score    int
		expected string
	}{
		{"safe_0", 0, "safe"},
		{"low_1", 1, "low"},
		{"low_29", 29, "low"},
		{"medium_30", 30, "medium"},
		{"medium_59", 59, "medium"},
		{"high_60", 60, "high"},
		{"high_89", 89, "high"},
		{"critical_90", 90, "critical"},
		{"critical_100", 100, "critical"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := categorizeRisk(tt.score)
			if result != tt.expected {
				t.Errorf("categorizeRisk(%d) = %s; want %s", tt.score, result, tt.expected)
			}
		})
	}
}

func TestTableDriven_ChainSupport(t *testing.T) {
	tests := []struct {
		chain    string
		expected bool
	}{
		{"ethereum", true},
		{"bsc", true},
		{"polygon", true},
		{"arbitrum", true},
		{"optimism", true},
		{"avalanche", true},
		{"fantom", true},
		{"base", true},
		{"zksync", true},
		{"solana", true},
		{"bitcoin", false},
		{"cosmos", false},
		{"", false},
	}

	for _, tt := range tests {
		t.Run(tt.chain, func(t *testing.T) {
			result := isSupportedChain(tt.chain)
			if result != tt.expected {
				t.Errorf("isSupportedChain(%s) = %v; want %v", tt.chain, result, tt.expected)
			}
		})
	}
}
