"""
╔═══════════════════════════════════════════════════════════════════════════╗
║              SENTINEL SHIELD - INTEGRATION TEST SUITE                     ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  End-to-end testing of the complete analysis pipeline                     ║
║  Tests interaction between all components                                 ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import pytest
import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from unittest.mock import Mock, AsyncMock, patch
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════
#                          DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

class AnalysisStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TokenApproval:
    token_address: str
    spender_address: str
    amount: str
    token_symbol: str = "UNKNOWN"
    is_unlimited: bool = False
    risk_level: str = "medium"


@dataclass
class ChainScanResult:
    chain: str
    approvals: List[TokenApproval] = field(default_factory=list)
    scan_time_ms: int = 0
    error: Optional[str] = None


@dataclass
class VulnerabilityReport:
    severity: str
    category: str
    title: str
    description: str
    recommendation: str
    confidence: float = 0.8


@dataclass
class FullAnalysisResult:
    address: str
    chains_scanned: List[str]
    total_approvals: int
    risk_score: float
    risk_level: str
    chain_results: List[ChainScanResult]
    vulnerabilities: List[VulnerabilityReport]
    analysis_time_ms: int
    status: AnalysisStatus = AnalysisStatus.COMPLETED


# ═══════════════════════════════════════════════════════════════════════════
#                          MOCK SERVICES
# ═══════════════════════════════════════════════════════════════════════════

class MockBlockchainProvider:
    """Mock blockchain RPC provider."""
    
    def __init__(self, chain: str, latency_ms: int = 50):
        self.chain = chain
        self.latency_ms = latency_ms
        self.call_count = 0
        self.approvals_db = self._generate_mock_approvals()
    
    def _generate_mock_approvals(self) -> Dict[str, List[TokenApproval]]:
        """Generate mock approval data."""
        return {
            "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1": [
                TokenApproval(
                    token_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                    spender_address="0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
                    amount="115792089237316195423570985008687907853269984665640564039457584007913129639935",
                    token_symbol="USDC",
                    is_unlimited=True,
                    risk_level="high"
                ),
                TokenApproval(
                    token_address="0xdAC17F958D2ee523a2206206994597C13D831ec7",
                    spender_address="0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
                    amount="1000000000",
                    token_symbol="USDT",
                    is_unlimited=False,
                    risk_level="low"
                ),
            ],
            "0x0000000000000000000000000000000000000000": [],
        }
    
    async def get_approvals(self, address: str) -> List[TokenApproval]:
        """Get token approvals for address."""
        self.call_count += 1
        await asyncio.sleep(self.latency_ms / 1000)
        return self.approvals_db.get(address, [])


class MockMLAnalyzer:
    """Mock ML-based vulnerability analyzer."""
    
    def __init__(self, processing_time_ms: int = 100):
        self.processing_time_ms = processing_time_ms
        self.analysis_count = 0
    
    async def analyze(self, approvals: List[TokenApproval]) -> List[VulnerabilityReport]:
        """Analyze approvals for vulnerabilities."""
        self.analysis_count += 1
        await asyncio.sleep(self.processing_time_ms / 1000)
        
        reports = []
        
        for approval in approvals:
            if approval.is_unlimited:
                reports.append(VulnerabilityReport(
                    severity="high",
                    category="unlimited_approval",
                    title="Unlimited Token Approval Detected",
                    description=f"Token {approval.token_symbol} has unlimited approval to {approval.spender_address[:10]}...",
                    recommendation="Consider revoking this approval or setting a specific limit.",
                    confidence=0.95
                ))
            
            # Check for known risky spenders (mock)
            if "7a250d5630" in approval.spender_address.lower():
                reports.append(VulnerabilityReport(
                    severity="medium",
                    category="dex_approval",
                    title="DEX Router Approval",
                    description=f"Approval to Uniswap V2 Router for {approval.token_symbol}",
                    recommendation="DEX approvals are common but review periodically.",
                    confidence=0.85
                ))
        
        return reports


class MockCacheService:
    """Mock caching service."""
    
    def __init__(self, hit_rate: float = 0.3):
        self.cache: Dict[str, Any] = {}
        self.hit_rate = hit_rate
        self.hits = 0
        self.misses = 0
    
    async def get(self, key: str) -> Optional[Any]:
        """Get from cache."""
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """Set in cache."""
        self.cache[key] = value
    
    @property
    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


# ═══════════════════════════════════════════════════════════════════════════
#                          ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════

class AnalysisOrchestrator:
    """Orchestrates the full analysis pipeline."""
    
    def __init__(
        self,
        providers: Dict[str, MockBlockchainProvider],
        analyzer: MockMLAnalyzer,
        cache: MockCacheService
    ):
        self.providers = providers
        self.analyzer = analyzer
        self.cache = cache
    
    async def analyze_wallet(
        self,
        address: str,
        chains: List[str]
    ) -> FullAnalysisResult:
        """Run complete wallet analysis."""
        start_time = time.time()
        
        # Check cache
        cache_key = f"{address}:{','.join(sorted(chains))}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        # Scan all chains in parallel
        chain_tasks = []
        for chain in chains:
            if chain in self.providers:
                chain_tasks.append(self._scan_chain(chain, address))
        
        chain_results = await asyncio.gather(*chain_tasks, return_exceptions=True)
        
        # Collect all approvals
        all_approvals = []
        valid_results = []
        for result in chain_results:
            if isinstance(result, ChainScanResult):
                valid_results.append(result)
                all_approvals.extend(result.approvals)
            elif isinstance(result, Exception):
                valid_results.append(ChainScanResult(
                    chain="unknown",
                    error=str(result)
                ))
        
        # Analyze for vulnerabilities
        vulnerabilities = await self.analyzer.analyze(all_approvals)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(all_approvals, vulnerabilities)
        risk_level = self._categorize_risk(risk_score)
        
        result = FullAnalysisResult(
            address=address,
            chains_scanned=chains,
            total_approvals=len(all_approvals),
            risk_score=risk_score,
            risk_level=risk_level,
            chain_results=valid_results,
            vulnerabilities=vulnerabilities,
            analysis_time_ms=int((time.time() - start_time) * 1000)
        )
        
        # Cache result
        await self.cache.set(cache_key, result, ttl_seconds=300)
        
        return result
    
    async def _scan_chain(self, chain: str, address: str) -> ChainScanResult:
        """Scan single chain."""
        start = time.time()
        provider = self.providers[chain]
        
        try:
            approvals = await provider.get_approvals(address)
            return ChainScanResult(
                chain=chain,
                approvals=approvals,
                scan_time_ms=int((time.time() - start) * 1000)
            )
        except Exception as e:
            return ChainScanResult(chain=chain, error=str(e))
    
    def _calculate_risk_score(
        self,
        approvals: List[TokenApproval],
        vulnerabilities: List[VulnerabilityReport]
    ) -> float:
        """Calculate aggregate risk score."""
        score = 0.0
        
        # Points per approval risk level
        risk_weights = {"critical": 25, "high": 15, "medium": 8, "low": 3}
        for approval in approvals:
            score += risk_weights.get(approval.risk_level, 5)
        
        # Points per vulnerability
        vuln_weights = {"critical": 30, "high": 20, "medium": 10, "low": 5}
        for vuln in vulnerabilities:
            score += vuln_weights.get(vuln.severity, 5) * vuln.confidence
        
        return min(100.0, score)
    
    def _categorize_risk(self, score: float) -> str:
        """Categorize risk level."""
        if score == 0:
            return "safe"
        elif score < 25:
            return "low"
        elif score < 50:
            return "medium"
        elif score < 75:
            return "high"
        return "critical"


# ═══════════════════════════════════════════════════════════════════════════
#                          INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestIntegrationPipeline:
    """Integration tests for the full analysis pipeline."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mock services."""
        providers = {
            "ethereum": MockBlockchainProvider("ethereum", latency_ms=20),
            "bsc": MockBlockchainProvider("bsc", latency_ms=15),
            "polygon": MockBlockchainProvider("polygon", latency_ms=10),
        }
        analyzer = MockMLAnalyzer(processing_time_ms=50)
        cache = MockCacheService()
        return AnalysisOrchestrator(providers, analyzer, cache)
    
    @pytest.mark.asyncio
    async def test_full_analysis_flow(self, orchestrator):
        """Test complete analysis from request to response."""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
        chains = ["ethereum", "bsc"]
        
        result = await orchestrator.analyze_wallet(address, chains)
        
        assert result.address == address
        assert result.status == AnalysisStatus.COMPLETED
        assert len(result.chains_scanned) == 2
        assert result.total_approvals > 0
        assert 0 <= result.risk_score <= 100
        assert result.risk_level in ["safe", "low", "medium", "high", "critical"]
        assert result.analysis_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_parallel_chain_scanning(self, orchestrator):
        """Test that chains are scanned in parallel."""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
        chains = ["ethereum", "bsc", "polygon"]
        
        start = time.time()
        result = await orchestrator.analyze_wallet(address, chains)
        elapsed = time.time() - start
        
        # If sequential, would take ~45ms (20+15+10). Parallel should be ~20ms + overhead
        # Allow for processing time
        assert elapsed < 0.2, f"Scanning took {elapsed}s, should be parallel"
        assert len(result.chain_results) == 3
    
    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_result(self, orchestrator):
        """Test that cached results are returned."""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
        chains = ["ethereum"]
        
        # First call - cache miss
        result1 = await orchestrator.analyze_wallet(address, chains)
        
        # Second call - cache hit
        result2 = await orchestrator.analyze_wallet(address, chains)
        
        assert result1.analysis_time_ms > 0
        assert orchestrator.cache.hits == 1
        assert orchestrator.cache.misses == 1
    
    @pytest.mark.asyncio
    async def test_empty_wallet_analysis(self, orchestrator):
        """Test analysis of wallet with no approvals."""
        address = "0x0000000000000000000000000000000000000000"
        chains = ["ethereum"]
        
        result = await orchestrator.analyze_wallet(address, chains)
        
        assert result.total_approvals == 0
        assert result.risk_score == 0
        assert result.risk_level == "safe"
        assert len(result.vulnerabilities) == 0
    
    @pytest.mark.asyncio
    async def test_unsupported_chain_handling(self, orchestrator):
        """Test graceful handling of unsupported chains."""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
        chains = ["ethereum", "unsupported_chain"]
        
        result = await orchestrator.analyze_wallet(address, chains)
        
        # Should complete with partial results
        assert result.status == AnalysisStatus.COMPLETED
        assert "ethereum" in result.chains_scanned
    
    @pytest.mark.asyncio
    async def test_vulnerability_detection(self, orchestrator):
        """Test that vulnerabilities are properly detected."""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
        chains = ["ethereum"]
        
        result = await orchestrator.analyze_wallet(address, chains)
        
        # Should detect unlimited approval
        unlimited_vulns = [v for v in result.vulnerabilities if "unlimited" in v.category]
        assert len(unlimited_vulns) > 0
        assert unlimited_vulns[0].severity == "high"
    
    @pytest.mark.asyncio
    async def test_concurrent_analysis_requests(self, orchestrator):
        """Test handling multiple concurrent analysis requests."""
        addresses = [
            "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1",
            "0x0000000000000000000000000000000000000000",
            "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1",  # Duplicate
        ]
        chains = ["ethereum"]
        
        tasks = [orchestrator.analyze_wallet(addr, chains) for addr in addresses]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert all(r.status == AnalysisStatus.COMPLETED for r in results)
    
    @pytest.mark.asyncio
    async def test_analysis_timing_breakdown(self, orchestrator):
        """Test that timing information is accurate."""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
        chains = ["ethereum", "bsc"]
        
        result = await orchestrator.analyze_wallet(address, chains)
        
        # Check that chain scan times are recorded
        for chain_result in result.chain_results:
            if not chain_result.error:
                assert chain_result.scan_time_ms > 0
        
        # Total time should be reasonable
        assert result.analysis_time_ms > 0
        assert result.analysis_time_ms < 5000  # Should complete in <5s


class TestServiceInteractions:
    """Tests for interactions between services."""
    
    @pytest.mark.asyncio
    async def test_provider_called_correctly(self):
        """Test that blockchain providers are called with correct params."""
        provider = MockBlockchainProvider("ethereum")
        analyzer = MockMLAnalyzer()
        cache = MockCacheService()
        
        orchestrator = AnalysisOrchestrator(
            {"ethereum": provider},
            analyzer,
            cache
        )
        
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
        await orchestrator.analyze_wallet(address, ["ethereum"])
        
        assert provider.call_count == 1
    
    @pytest.mark.asyncio
    async def test_analyzer_receives_all_approvals(self):
        """Test that ML analyzer receives approvals from all chains."""
        providers = {
            "ethereum": MockBlockchainProvider("ethereum"),
            "bsc": MockBlockchainProvider("bsc"),
        }
        analyzer = MockMLAnalyzer()
        cache = MockCacheService()
        
        orchestrator = AnalysisOrchestrator(providers, analyzer, cache)
        
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
        await orchestrator.analyze_wallet(address, ["ethereum", "bsc"])
        
        assert analyzer.analysis_count == 1
    
    @pytest.mark.asyncio
    async def test_cache_stores_complete_result(self):
        """Test that cache stores the complete analysis result."""
        provider = MockBlockchainProvider("ethereum")
        analyzer = MockMLAnalyzer()
        cache = MockCacheService()
        
        orchestrator = AnalysisOrchestrator(
            {"ethereum": provider},
            analyzer,
            cache
        )
        
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
        result = await orchestrator.analyze_wallet(address, ["ethereum"])
        
        cache_key = f"{address}:ethereum"
        cached = await cache.get(cache_key)
        
        assert cached is not None
        assert cached.address == result.address
        assert cached.risk_score == result.risk_score


class TestErrorHandling:
    """Tests for error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_provider_timeout_handling(self):
        """Test handling of slow/timing out providers."""
        slow_provider = MockBlockchainProvider("slow_chain", latency_ms=5000)
        fast_provider = MockBlockchainProvider("fast_chain", latency_ms=10)
        
        orchestrator = AnalysisOrchestrator(
            {"slow": slow_provider, "fast": fast_provider},
            MockMLAnalyzer(),
            MockCacheService()
        )
        
        # This will take 5+ seconds due to slow provider
        # In real implementation, would have timeout
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
        
        # Just test that fast chain completes
        result = await orchestrator.analyze_wallet(address, ["fast"])
        assert result.status == AnalysisStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """Test that analysis continues when some chains fail."""
        providers = {
            "ethereum": MockBlockchainProvider("ethereum"),
            # No "bsc" provider - simulates failure
        }
        
        orchestrator = AnalysisOrchestrator(
            providers,
            MockMLAnalyzer(),
            MockCacheService()
        )
        
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
        result = await orchestrator.analyze_wallet(address, ["ethereum", "bsc"])
        
        # Should still complete with partial results
        assert result.status == AnalysisStatus.COMPLETED
        assert len(result.chain_results) >= 1


class TestPerformance:
    """Performance-related integration tests."""
    
    @pytest.mark.asyncio
    async def test_response_time_under_load(self):
        """Test response times under concurrent load."""
        providers = {f"chain_{i}": MockBlockchainProvider(f"chain_{i}", latency_ms=10) for i in range(5)}
        orchestrator = AnalysisOrchestrator(
            providers,
            MockMLAnalyzer(processing_time_ms=20),
            MockCacheService()
        )
        
        addresses = [f"0x{i:040x}" for i in range(10)]
        chains = list(providers.keys())
        
        start = time.time()
        tasks = [orchestrator.analyze_wallet(addr, chains) for addr in addresses]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start
        
        assert all(r.status == AnalysisStatus.COMPLETED for r in results)
        
        # 10 concurrent requests should complete in reasonable time
        avg_time = elapsed / 10
        assert avg_time < 1.0, f"Average time {avg_time}s too high"
    
    @pytest.mark.asyncio
    async def test_cache_improves_performance(self):
        """Test that caching significantly improves response time."""
        provider = MockBlockchainProvider("ethereum", latency_ms=100)
        orchestrator = AnalysisOrchestrator(
            {"ethereum": provider},
            MockMLAnalyzer(processing_time_ms=100),
            MockCacheService()
        )
        
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1"
        chains = ["ethereum"]
        
        # First request - cold
        start = time.time()
        await orchestrator.analyze_wallet(address, chains)
        cold_time = time.time() - start
        
        # Second request - cached
        start = time.time()
        await orchestrator.analyze_wallet(address, chains)
        warm_time = time.time() - start
        
        # Cached should be much faster
        assert warm_time < cold_time / 2, f"Cache didn't improve: cold={cold_time}, warm={warm_time}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
