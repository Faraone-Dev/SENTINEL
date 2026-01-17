/*
 ═══════════════════════════════════════════════════════════════════════════════
  SENTINEL SHIELD - Go API Server Tests
  Author: SENTINEL Team
 ═══════════════════════════════════════════════════════════════════════════════
*/

package main

import (
	"context"
	"encoding/json"
	"math/big"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

// ═══════════════════════════════════════════════════════════════════════════════
//                              CACHE TESTS
// ═══════════════════════════════════════════════════════════════════════════════

func TestCache_SetAndGet(t *testing.T) {
	cache := NewCache(5 * time.Minute)

	// Set a value
	cache.Set("test_key", "test_value")

	// Get the value
	val, ok := cache.Get("test_key")
	if !ok {
		t.Fatal("Expected to find key in cache")
	}
	if val != "test_value" {
		t.Errorf("Expected 'test_value', got '%v'", val)
	}
}

func TestCache_Expiration(t *testing.T) {
	// Create cache with very short TTL
	cache := NewCache(1 * time.Millisecond)

	cache.Set("expire_key", "expire_value")

	// Wait for expiration
	time.Sleep(5 * time.Millisecond)

	// Should not find expired key
	_, ok := cache.Get("expire_key")
	if ok {
		t.Error("Expected key to be expired")
	}
}

func TestCache_MissingKey(t *testing.T) {
	cache := NewCache(5 * time.Minute)

	_, ok := cache.Get("nonexistent")
	if ok {
		t.Error("Expected key to not be found")
	}
}

func TestCache_Overwrite(t *testing.T) {
	cache := NewCache(5 * time.Minute)

	cache.Set("key", "value1")
	cache.Set("key", "value2")

	val, _ := cache.Get("key")
	if val != "value2" {
		t.Errorf("Expected 'value2', got '%v'", val)
	}
}

// ═══════════════════════════════════════════════════════════════════════════════
//                              SCANNER TESTS
// ═══════════════════════════════════════════════════════════════════════════════

func TestScanner_NewScanner(t *testing.T) {
	scanner := NewScanner()

	if scanner == nil {
		t.Fatal("Expected scanner to be created")
	}

	if len(scanner.clients) == 0 {
		t.Error("Expected scanner to have chain clients")
	}
}

func TestScanner_ScanWallet(t *testing.T) {
	scanner := NewScanner()
	ctx := context.Background()

	// Test with valid address
	result, err := scanner.ScanWallet(ctx, "0x1234567890123456789012345678901234567890", []ChainID{Ethereum})

	if err != nil {
		t.Fatalf("Unexpected error: %v", err)
	}

	if result == nil {
		t.Fatal("Expected result to be returned")
	}

	if result.WalletAddress != "0x1234567890123456789012345678901234567890" {
		t.Error("Wallet address mismatch")
	}

	if len(result.ChainsScanned) != 1 {
		t.Errorf("Expected 1 chain scanned, got %d", len(result.ChainsScanned))
	}
}

func TestScanner_MultiChainScan(t *testing.T) {
	scanner := NewScanner()
	ctx := context.Background()

	chains := []ChainID{Ethereum, Polygon, Arbitrum}
	result, err := scanner.ScanWallet(ctx, "0xabcdef1234567890abcdef1234567890abcdef12", chains)

	if err != nil {
		t.Fatalf("Unexpected error: %v", err)
	}

	if len(result.ChainsScanned) != 3 {
		t.Errorf("Expected 3 chains scanned, got %d", len(result.ChainsScanned))
	}
}

func TestScanner_RiskScoreCalculation(t *testing.T) {
	scanner := NewScanner()

	result := &WalletScanResult{
		Approvals: []Approval{
			{RiskLevel: "critical"},
			{RiskLevel: "critical"},
			{RiskLevel: "warning"},
		},
	}

	scanner.calculateRiskScores(result)

	if result.CriticalRisks != 2 {
		t.Errorf("Expected 2 critical risks, got %d", result.CriticalRisks)
	}

	if result.Warnings != 1 {
		t.Errorf("Expected 1 warning, got %d", result.Warnings)
	}

	expectedScore := 70 // 2*30 + 1*10
	if result.OverallRiskScore != expectedScore {
		t.Errorf("Expected risk score %d, got %d", expectedScore, result.OverallRiskScore)
	}
}

func TestScanner_RiskScoreCapped(t *testing.T) {
	scanner := NewScanner()

	// Create many critical risks
	result := &WalletScanResult{
		Approvals: []Approval{
			{RiskLevel: "critical"},
			{RiskLevel: "critical"},
			{RiskLevel: "critical"},
			{RiskLevel: "critical"},
			{RiskLevel: "critical"},
		},
	}

	scanner.calculateRiskScores(result)

	// Score should be capped at 100
	if result.OverallRiskScore > 100 {
		t.Errorf("Risk score should be capped at 100, got %d", result.OverallRiskScore)
	}
}

// ═══════════════════════════════════════════════════════════════════════════════
//                              HTTP HANDLER TESTS
// ═══════════════════════════════════════════════════════════════════════════════

func TestHandler_Health(t *testing.T) {
	server := NewServer()

	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()

	server.handleHealth(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var response map[string]string
	json.NewDecoder(w.Body).Decode(&response)

	if response["status"] != "healthy" {
		t.Errorf("Expected status 'healthy', got '%s'", response["status"])
	}
}

func TestHandler_Chains(t *testing.T) {
	server := NewServer()

	req := httptest.NewRequest("GET", "/api/v1/chains", nil)
	w := httptest.NewRecorder()

	server.handleChains(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var response map[string][]ChainID
	json.NewDecoder(w.Body).Decode(&response)

	if len(response["chains"]) == 0 {
		t.Error("Expected chains to be returned")
	}
}

func TestHandler_Scan_MissingWallet(t *testing.T) {
	server := NewServer()

	req := httptest.NewRequest("GET", "/api/v1/scan", nil)
	w := httptest.NewRecorder()

	server.handleScan(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d", w.Code)
	}
}

func TestHandler_Scan_ValidWallet(t *testing.T) {
	server := NewServer()

	req := httptest.NewRequest("GET", "/api/v1/scan?wallet=0x1234567890123456789012345678901234567890", nil)
	w := httptest.NewRecorder()

	server.handleScan(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var result WalletScanResult
	json.NewDecoder(w.Body).Decode(&result)

	if result.WalletAddress == "" {
		t.Error("Expected wallet address in response")
	}
}

func TestHandler_CORS(t *testing.T) {
	handler := corsMiddleware(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	req := httptest.NewRequest("OPTIONS", "/test", nil)
	w := httptest.NewRecorder()

	handler(w, req)

	if w.Header().Get("Access-Control-Allow-Origin") != "*" {
		t.Error("Expected CORS header to be set")
	}
}

// ═══════════════════════════════════════════════════════════════════════════════
//                              CHAIN CLIENT TESTS
// ═══════════════════════════════════════════════════════════════════════════════

func TestChainClient_New(t *testing.T) {
	client := NewChainClient(Ethereum, "https://eth.example.com")

	if client.ChainID != Ethereum {
		t.Error("Chain ID mismatch")
	}

	if client.RPC != "https://eth.example.com" {
		t.Error("RPC URL mismatch")
	}
}

// ═══════════════════════════════════════════════════════════════════════════════
//                              APPROVAL TESTS
// ═══════════════════════════════════════════════════════════════════════════════

func TestApproval_Struct(t *testing.T) {
	approval := Approval{
		Chain:          Ethereum,
		TokenAddress:   "0xtoken",
		TokenSymbol:    "TEST",
		SpenderAddress: "0xspender",
		IsUnlimited:    true,
		RiskLevel:      "critical",
	}

	if approval.Chain != Ethereum {
		t.Error("Chain mismatch")
	}

	if !approval.IsUnlimited {
		t.Error("Should be unlimited")
	}
}

// ═══════════════════════════════════════════════════════════════════════════════
//                              BENCHMARK TESTS
// ═══════════════════════════════════════════════════════════════════════════════

func BenchmarkCache_Set(b *testing.B) {
	cache := NewCache(5 * time.Minute)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		cache.Set("key", "value")
	}
}

func BenchmarkCache_Get(b *testing.B) {
	cache := NewCache(5 * time.Minute)
	cache.Set("key", "value")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		cache.Get("key")
	}
}

func BenchmarkScanner_RiskCalculation(b *testing.B) {
	scanner := NewScanner()
	result := &WalletScanResult{
		Approvals: make([]Approval, 100),
	}
	for i := range result.Approvals {
		result.Approvals[i] = Approval{RiskLevel: "warning"}
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		scanner.calculateRiskScores(result)
	}
}

// ═══════════════════════════════════════════════════════════════════════════════
//                         16 CHAIN SUPPORT TESTS
// ═══════════════════════════════════════════════════════════════════════════════

func TestAllChains_Count(t *testing.T) {
	expected := 16
	if len(AllChains) != expected {
		t.Errorf("Expected %d chains, got %d", expected, len(AllChains))
	}
}

func TestAllChains_HaveRPCConfig(t *testing.T) {
	for _, chain := range AllChains {
		rpc, ok := config.RPC[string(chain)]
		if !ok {
			t.Errorf("Chain %s has no RPC configured", chain)
		}
		if rpc == "" {
			t.Errorf("Chain %s has empty RPC URL", chain)
		}
	}
}

func TestChainCategories(t *testing.T) {
	// Ethereum L2s
	l2s := []ChainID{Ethereum, Arbitrum, Optimism, Base, ZkSync, Linea, Scroll, ZkEVM}
	for _, chain := range l2s {
		found := false
		for _, c := range AllChains {
			if c == chain {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("L2 chain %s not in AllChains", chain)
		}
	}

	// Alt L1s
	l1s := []ChainID{BSC, Polygon, Avalanche, Fantom, Cronos, Gnosis, Celo, Moonbeam}
	for _, chain := range l1s {
		found := false
		for _, c := range AllChains {
			if c == chain {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("Alt L1 chain %s not in AllChains", chain)
		}
	}
}

// ═══════════════════════════════════════════════════════════════════════════════
//                         FORMAT ALLOWANCE TESTS
// ═══════════════════════════════════════════════════════════════════════════════

func TestFormatAllowance_Unlimited(t *testing.T) {
	maxUint := new(big.Int)
	maxUint.SetString("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff", 16)

	result := formatAllowance(maxUint)
	if result != "UNLIMITED" {
		t.Errorf("Expected UNLIMITED, got %s", result)
	}
}

func TestFormatAllowance_SmallAmount(t *testing.T) {
	amount := big.NewInt(1e18) // 1 token
	result := formatAllowance(amount)
	if result != "1.0000" {
		t.Errorf("Expected 1.0000, got %s", result)
	}
}

func TestFormatAllowance_Thousands(t *testing.T) {
	amount := new(big.Int)
	amount.SetString("5000000000000000000000", 10) // 5000 tokens
	result := formatAllowance(amount)
	if !strings.HasSuffix(result, "K") {
		t.Errorf("Expected K suffix, got %s", result)
	}
}

func TestFormatAllowance_Millions(t *testing.T) {
	amount := new(big.Int)
	amount.SetString("2000000000000000000000000", 10) // 2M tokens
	result := formatAllowance(amount)
	if !strings.HasSuffix(result, "M") {
		t.Errorf("Expected M suffix, got %s", result)
	}
}

func TestFormatAllowance_Billions(t *testing.T) {
	amount := new(big.Int)
	amount.SetString("3000000000000000000000000000", 10) // 3B tokens
	result := formatAllowance(amount)
	if !strings.HasSuffix(result, "B") {
		t.Errorf("Expected B suffix, got %s", result)
	}
}

// ═══════════════════════════════════════════════════════════════════════════════
//                      CONTRACT ANALYZER TESTS
// ═══════════════════════════════════════════════════════════════════════════════

func TestNewContractAnalyzer(t *testing.T) {
	clients := make(map[ChainID]*ChainClient)
	clients[Ethereum] = NewChainClient(Ethereum, "https://eth.drpc.org")

	analyzer := NewContractAnalyzer(clients)

	if analyzer == nil {
		t.Error("Expected non-nil ContractAnalyzer")
	}
	if analyzer.decompiler == nil {
		t.Error("Expected decompiler client to be initialized")
	}
	if analyzer.analyzer == nil {
		t.Error("Expected analyzer client to be initialized")
	}
}

// ═══════════════════════════════════════════════════════════════════════════════
//                         ANALYZE HANDLER TESTS
// ═══════════════════════════════════════════════════════════════════════════════

func TestHandleAnalyze_MissingContract(t *testing.T) {
	server := NewServer()
	req := httptest.NewRequest("GET", "/api/v1/analyze", nil)
	w := httptest.NewRecorder()

	server.handleAnalyze(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected 400, got %d", w.Code)
	}
}

func TestHandleAnalyze_InvalidAddress(t *testing.T) {
	server := NewServer()
	req := httptest.NewRequest("GET", "/api/v1/analyze?contract=notanaddress", nil)
	w := httptest.NewRecorder()

	server.handleAnalyze(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected 400, got %d", w.Code)
	}
}

func TestHandleAnalyze_InvalidChain(t *testing.T) {
	server := NewServer()
	req := httptest.NewRequest("GET", "/api/v1/analyze?contract=0x1234567890123456789012345678901234567890&chain=fakechain", nil)
	w := httptest.NewRecorder()

	server.handleAnalyze(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected 400 for invalid chain, got %d", w.Code)
	}
}

func TestHandleBatchAnalyze_NotPost(t *testing.T) {
	server := NewServer()
	req := httptest.NewRequest("GET", "/api/v1/analyze/batch", nil)
	w := httptest.NewRecorder()

	server.handleBatchAnalyze(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Errorf("Expected 405, got %d", w.Code)
	}
}

func TestHandleBatchAnalyze_EmptyBody(t *testing.T) {
	server := NewServer()
	req := httptest.NewRequest("POST", "/api/v1/analyze/batch", strings.NewReader("{}"))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	server.handleBatchAnalyze(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected 400 for empty contracts, got %d", w.Code)
	}
}

// ═══════════════════════════════════════════════════════════════════════════════
//                      SCANNER RECOMMENDATIONS TESTS
// ═══════════════════════════════════════════════════════════════════════════════

func TestGenerateRecommendations_CriticalRisks(t *testing.T) {
	scanner := NewScanner()
	result := &WalletScanResult{
		CriticalRisks: 3,
		Approvals:     []Approval{},
	}

	scanner.generateRecommendations(result)

	hasUrgent := false
	for _, rec := range result.Recommendations {
		if strings.Contains(rec, "URGENT") {
			hasUrgent = true
		}
	}
	if !hasUrgent {
		t.Error("Expected URGENT recommendation for critical risks")
	}
}

func TestGenerateRecommendations_UnlimitedApprovals(t *testing.T) {
	scanner := NewScanner()
	result := &WalletScanResult{
		Approvals: []Approval{
			{IsUnlimited: true},
			{IsUnlimited: true},
		},
	}

	scanner.generateRecommendations(result)

	hasUnlimited := false
	for _, rec := range result.Recommendations {
		if strings.Contains(rec, "unlimited") {
			hasUnlimited = true
		}
	}
	if !hasUnlimited {
		t.Error("Expected recommendation about unlimited approvals")
	}
}

func TestGenerateRecommendations_UnknownSpenders(t *testing.T) {
	scanner := NewScanner()
	result := &WalletScanResult{
		Approvals: []Approval{
			{SpenderName: "Unknown"},
		},
	}

	scanner.generateRecommendations(result)

	hasUnknown := false
	for _, rec := range result.Recommendations {
		if strings.Contains(rec, "unknown") || strings.Contains(rec, "Unknown") {
			hasUnknown = true
		}
	}
	if !hasUnknown {
		t.Error("Expected recommendation about unknown spenders")
	}
}

func TestGenerateRecommendations_HighRiskScore(t *testing.T) {
	scanner := NewScanner()
	result := &WalletScanResult{
		OverallRiskScore: 75,
		Approvals:        []Approval{},
	}

	scanner.generateRecommendations(result)

	hasRiskWarning := false
	for _, rec := range result.Recommendations {
		if strings.Contains(rec, "elevated risk") {
			hasRiskWarning = true
		}
	}
	if !hasRiskWarning {
		t.Error("Expected elevated risk warning")
	}
}
