package main

import (
	"fmt"
	"testing"
	"time"
)

/*
 ╔═══════════════════════════════════════════════════════════════════════════╗
 ║              SENTINEL SHIELD - BENCHMARK SUITE (GO)                       ║
 ╠═══════════════════════════════════════════════════════════════════════════╣
 ║  Performance measurement for all critical operations                      ║
 ║  Run with: go test -bench=. -benchmem                                     ║
 ╚═══════════════════════════════════════════════════════════════════════════╝
*/

// ═══════════════════════════════════════════════════════════════════════════
//                      CACHE BENCHMARKS (Extended)
// ═══════════════════════════════════════════════════════════════════════════

func BenchmarkCache_Set_Extended(b *testing.B) {
	cache := NewCache(time.Minute)
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		cache.Set(fmt.Sprintf("key-%d", i), fmt.Sprintf("value-%d", i))
	}
}

func BenchmarkCache_Get_Extended(b *testing.B) {
	cache := NewCache(time.Minute)
	
	// Pre-populate
	for i := 0; i < 1000; i++ {
		cache.Set(fmt.Sprintf("key-%d", i), fmt.Sprintf("value-%d", i))
	}
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		cache.Get(fmt.Sprintf("key-%d", i%1000))
	}
}

func BenchmarkCache_SetGet_Parallel(b *testing.B) {
	cache := NewCache(time.Minute)
	
	b.RunParallel(func(pb *testing.PB) {
		i := 0
		for pb.Next() {
			key := fmt.Sprintf("key-%d", i%1000)
			if i%2 == 0 {
				cache.Set(key, "value")
			} else {
				cache.Get(key)
			}
			i++
		}
	})
}

// ═══════════════════════════════════════════════════════════════════════════
//                      ADDRESS VALIDATION BENCHMARKS
// ═══════════════════════════════════════════════════════════════════════════

func BenchmarkAddressValidation_Valid(b *testing.B) {
	addr := "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		isValidAddress(addr)
	}
}

func BenchmarkAddressValidation_Invalid(b *testing.B) {
	addr := "not-an-address"
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		isValidAddress(addr)
	}
}

// ═══════════════════════════════════════════════════════════════════════════
//                      CHAIN LOOKUP BENCHMARKS
// ═══════════════════════════════════════════════════════════════════════════

func BenchmarkChainLookup_Supported(b *testing.B) {
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		isSupportedChain("ethereum")
	}
}

func BenchmarkChainLookup_Unsupported(b *testing.B) {
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		isSupportedChain("unknown-chain")
	}
}

// ═══════════════════════════════════════════════════════════════════════════
//                      RISK SCORE BENCHMARKS
// ═══════════════════════════════════════════════════════════════════════════

func BenchmarkRiskScore_Calculate(b *testing.B) {
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		calculateRiskScore(i%5, i%10, i%20)
	}
}

func BenchmarkRiskScore_Categorize(b *testing.B) {
	scores := []int{0, 15, 45, 75, 95}
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		categorizeRisk(scores[i%5])
	}
}

// ═══════════════════════════════════════════════════════════════════════════
//                      SCANNER BENCHMARKS
// ═══════════════════════════════════════════════════════════════════════════

func BenchmarkScanner_SingleChain(b *testing.B) {
	scanner := &TestMultiChainScanner{
		chains: map[string]TestChainScanner{
			"ethereum": &MockTestChainScanner{},
		},
	}
	addr := "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
	chains := []string{"ethereum"}
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		scanner.Scan(nil, addr, chains)
	}
}

func BenchmarkScanner_MultiChain(b *testing.B) {
	scanner := &TestMultiChainScanner{
		chains: map[string]TestChainScanner{
			"ethereum": &MockTestChainScanner{},
			"bsc":      &MockTestChainScanner{},
			"polygon":  &MockTestChainScanner{},
			"arbitrum": &MockTestChainScanner{},
			"base":     &MockTestChainScanner{},
		},
	}
	addr := "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
	chains := []string{"ethereum", "bsc", "polygon", "arbitrum", "base"}
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		scanner.Scan(nil, addr, chains)
	}
}

func BenchmarkScanner_AllChains(b *testing.B) {
	scanner := &TestMultiChainScanner{
		chains: map[string]TestChainScanner{
			"ethereum":  &MockTestChainScanner{},
			"bsc":       &MockTestChainScanner{},
			"polygon":   &MockTestChainScanner{},
			"arbitrum":  &MockTestChainScanner{},
			"base":      &MockTestChainScanner{},
			"optimism":  &MockTestChainScanner{},
			"avalanche": &MockTestChainScanner{},
			"fantom":    &MockTestChainScanner{},
			"zksync":    &MockTestChainScanner{},
			"solana":    &MockTestChainScanner{},
		},
	}
	addr := "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
	chains := []string{"ethereum", "bsc", "polygon", "arbitrum", "base", "optimism", "avalanche", "fantom", "zksync", "solana"}
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		scanner.Scan(nil, addr, chains)
	}
}

func BenchmarkScanner_Parallel(b *testing.B) {
	scanner := &TestMultiChainScanner{
		chains: map[string]TestChainScanner{
			"ethereum": &MockTestChainScanner{},
			"bsc":      &MockTestChainScanner{},
			"polygon":  &MockTestChainScanner{},
		},
	}
	addr := "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
	chains := []string{"ethereum", "bsc", "polygon"}
	
	b.RunParallel(func(pb *testing.PB) {
		for pb.Next() {
			scanner.Scan(nil, addr, chains)
		}
	})
}

// ═══════════════════════════════════════════════════════════════════════════
//                      MEMORY BENCHMARKS
// ═══════════════════════════════════════════════════════════════════════════

func BenchmarkMemory_ScanResult(b *testing.B) {
	b.ReportAllocs()
	
	for i := 0; i < b.N; i++ {
		result := &TestScanResult{
			Approvals: make([]TestApproval, 100),
		}
		for j := 0; j < 100; j++ {
			result.Approvals[j] = TestApproval{
				Token:   fmt.Sprintf("0x%040d", j),
				Spender: fmt.Sprintf("0x%040d", j+1000),
				Amount:  "1000000000000000000",
			}
		}
	}
}

func BenchmarkMemory_CacheEntry(b *testing.B) {
	cache := NewCache(time.Minute)
	b.ReportAllocs()
	
	for i := 0; i < b.N; i++ {
		cache.Set(
			fmt.Sprintf("0x%040d", i),
			&TestScanResult{
				Approvals: []TestApproval{
					{Token: "0xToken", Spender: "0xSpender", Amount: "1000"},
				},
			},
		)
	}
}

// ═══════════════════════════════════════════════════════════════════════════
//                      THROUGHPUT BENCHMARKS
// ═══════════════════════════════════════════════════════════════════════════

func BenchmarkThroughput_RequestsPerSecond(b *testing.B) {
	scanner := &TestMultiChainScanner{
		chains: map[string]TestChainScanner{
			"ethereum": &MockTestChainScanner{},
		},
	}
	cache := NewCache(5 * time.Minute)
	addr := "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
	chains := []string{"ethereum"}
	
	b.ResetTimer()
	b.RunParallel(func(pb *testing.PB) {
		for pb.Next() {
			// Check cache
			cacheKey := addr + ":ethereum"
			if _, found := cache.Get(cacheKey); found {
				continue
			}
			
			// Scan
			result, _ := scanner.Scan(nil, addr, chains)
			
			// Cache result
			cache.Set(cacheKey, result)
		}
	})
	
	b.ReportMetric(float64(b.N)/b.Elapsed().Seconds(), "req/s")
}

// ═══════════════════════════════════════════════════════════════════════════
//                      COMPARISON BENCHMARKS
// ═══════════════════════════════════════════════════════════════════════════

func BenchmarkComparison_MapVsSlice(b *testing.B) {
	// Map lookup
	b.Run("Map", func(b *testing.B) {
		chains := map[string]bool{
			"ethereum": true, "bsc": true, "polygon": true,
			"arbitrum": true, "base": true, "optimism": true,
		}
		
		for i := 0; i < b.N; i++ {
			_ = chains["ethereum"]
		}
	})
	
	// Slice search
	b.Run("Slice", func(b *testing.B) {
		chains := []string{"ethereum", "bsc", "polygon", "arbitrum", "base", "optimism"}
		
		for i := 0; i < b.N; i++ {
			for _, c := range chains {
				if c == "ethereum" {
					break
				}
			}
		}
	})
}

func BenchmarkComparison_StringConcat(b *testing.B) {
	addr := "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
	chain := "ethereum"
	
	// Plus operator
	b.Run("Plus", func(b *testing.B) {
		for i := 0; i < b.N; i++ {
			_ = addr + ":" + chain
		}
	})
	
	// fmt.Sprintf
	b.Run("Sprintf", func(b *testing.B) {
		for i := 0; i < b.N; i++ {
			_ = fmt.Sprintf("%s:%s", addr, chain)
		}
	})
}

// ═══════════════════════════════════════════════════════════════════════════
//                      BASELINE BENCHMARKS
// ═══════════════════════════════════════════════════════════════════════════

func BenchmarkBaseline_NOP(b *testing.B) {
	// Baseline: empty loop
	for i := 0; i < b.N; i++ {
	}
}

func BenchmarkBaseline_TimeNow(b *testing.B) {
	for i := 0; i < b.N; i++ {
		_ = time.Now()
	}
}

func BenchmarkBaseline_FmtSprintf(b *testing.B) {
	for i := 0; i < b.N; i++ {
		_ = fmt.Sprintf("key-%d", i)
	}
}
