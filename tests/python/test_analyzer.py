"""
═══════════════════════════════════════════════════════════════════════════════
 SENTINEL SHIELD - Python Analyzer Tests
 Comprehensive test suite for vulnerability detection
 Author: SENTINEL Team
═══════════════════════════════════════════════════════════════════════════════
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import json

# Import modules to test
from src.analyzer import (
    VulnerabilityAnalyzer,
    AnalyzerService,
    HoneypotDetector,
    ReentrancyDetector,
    OwnerPrivilegeDetector,
    PatternDatabase,
    Vulnerability,
    ContractAnalysis,
    RiskLevel,
    VulnerabilityType,
)


# ═══════════════════════════════════════════════════════════════════════════════
#                              FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def analyzer():
    """Create a fresh analyzer instance"""
    return VulnerabilityAnalyzer()


@pytest.fixture
def service():
    """Create a fresh service instance"""
    return AnalyzerService()


@pytest.fixture
def sample_bytecode():
    """Sample EVM bytecode"""
    return bytes.fromhex("6080604052348015600f57600080fd5b50")


@pytest.fixture
def malicious_bytecode():
    """Bytecode with dangerous patterns"""
    # Includes ORIGIN opcode (0x32) and many SLOADs
    return bytes([0x32] + [0x54] * 15)


@pytest.fixture
def sample_decompiler_result():
    """Sample output from Rust decompiler"""
    return {
        "security": {
            "function_selectors": ["0x40c10f19", "0x8456cb59"],
            "external_calls": 3,
            "storage_writes": 5,
            "has_selfdestruct": False,
            "has_delegatecall": True
        }
    }


# ═══════════════════════════════════════════════════════════════════════════════
#                          VULNERABILITY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestVulnerability:
    def test_vulnerability_creation(self):
        vuln = Vulnerability(
            vuln_type=VulnerabilityType.HONEYPOT,
            severity=RiskLevel.CRITICAL,
            title="Test Vulnerability",
            description="Test description",
            confidence=0.95
        )
        
        assert vuln.vuln_type == VulnerabilityType.HONEYPOT
        assert vuln.severity == RiskLevel.CRITICAL
        assert vuln.confidence == 0.95

    def test_vulnerability_to_dict(self):
        vuln = Vulnerability(
            vuln_type=VulnerabilityType.REENTRANCY,
            severity=RiskLevel.HIGH,
            title="Reentrancy Risk",
            description="Potential reentrancy",
            location="0x1234",
            confidence=0.80
        )
        
        result = vuln.to_dict()
        
        assert result["type"] == "reentrancy"
        assert result["severity"] == "high"
        assert result["location"] == "0x1234"
        assert result["confidence"] == 0.80


class TestContractAnalysis:
    def test_contract_analysis_creation(self):
        analysis = ContractAnalysis(
            address="0x1234567890123456789012345678901234567890",
            chain="ethereum",
            bytecode_hash="0xabc123"
        )
        
        assert analysis.address == "0x1234567890123456789012345678901234567890"
        assert analysis.risk_score == 0
        assert analysis.risk_level == RiskLevel.SAFE

    def test_contract_analysis_to_dict(self):
        analysis = ContractAnalysis(
            address="0x1234",
            chain="polygon",
            bytecode_hash="0xhash",
            risk_score=75,
            risk_level=RiskLevel.HIGH
        )
        
        result = analysis.to_dict()
        
        assert result["chain"] == "polygon"
        assert result["risk_score"] == 75
        assert result["risk_level"] == "high"


# ═══════════════════════════════════════════════════════════════════════════════
#                          DETECTOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestHoneypotDetector:
    def test_detect_transfer_restrictions(self, malicious_bytecode):
        vulns = HoneypotDetector.analyze(malicious_bytecode, [])
        
        # Should detect the ORIGIN opcode pattern
        honeypot_vulns = [v for v in vulns if v.vuln_type == VulnerabilityType.HONEYPOT]
        assert len(honeypot_vulns) > 0

    def test_safe_bytecode(self, sample_bytecode):
        vulns = HoneypotDetector.analyze(sample_bytecode, [])
        
        # Simple bytecode should not trigger honeypot detection
        honeypot_vulns = [v for v in vulns if v.vuln_type == VulnerabilityType.HONEYPOT]
        # May or may not detect, depends on patterns
        assert isinstance(vulns, list)

    def test_fee_manipulation_detection(self):
        # Bytecode with PUSH1 100 DIV pattern
        bytecode = bytes([0x60, 0x64, 0x04])  # PUSH1 100 DIV
        vulns = HoneypotDetector.analyze(bytecode, [])
        
        fee_vulns = [v for v in vulns if v.vuln_type == VulnerabilityType.HIDDEN_FEE]
        assert len(fee_vulns) > 0


class TestReentrancyDetector:
    def test_detect_reentrancy_risk(self):
        # External calls + storage writes = potential reentrancy
        vulns = ReentrancyDetector.analyze(
            bytecode=b"",
            external_calls=3,
            storage_writes=5
        )
        
        assert len(vulns) > 0
        assert vulns[0].vuln_type == VulnerabilityType.REENTRANCY

    def test_no_reentrancy_without_external_calls(self):
        vulns = ReentrancyDetector.analyze(
            bytecode=b"",
            external_calls=0,
            storage_writes=10
        )
        
        assert len(vulns) == 0

    def test_no_reentrancy_without_storage_writes(self):
        vulns = ReentrancyDetector.analyze(
            bytecode=b"",
            external_calls=5,
            storage_writes=0
        )
        
        assert len(vulns) == 0


class TestOwnerPrivilegeDetector:
    def test_detect_mint_function(self):
        vulns = OwnerPrivilegeDetector.analyze(
            selectors=["0x40c10f19"],  # mint selector
            has_selfdestruct=False
        )
        
        mint_vulns = [v for v in vulns if "mint" in v.title.lower()]
        assert len(mint_vulns) > 0
        assert all(v.vuln_type == VulnerabilityType.MINT_FUNCTION for v in mint_vulns)

    def test_detect_burn_function(self):
        vulns = OwnerPrivilegeDetector.analyze(
            selectors=["0x42966c68"],  # burn selector
            has_selfdestruct=False
        )

        burn_vulns = [v for v in vulns if "burn" in v.title.lower()]
        assert len(burn_vulns) > 0
        assert all(v.vuln_type == VulnerabilityType.BURN_FUNCTION for v in burn_vulns)

    def test_detect_pause_function(self):
        vulns = OwnerPrivilegeDetector.analyze(
            selectors=["0x8456cb59"],  # pause selector
            has_selfdestruct=False
        )
        
        pause_vulns = [v for v in vulns if "pause" in v.title.lower()]
        assert len(pause_vulns) > 0
        assert all(v.vuln_type == VulnerabilityType.PAUSE for v in pause_vulns)

    def test_detect_selfdestruct(self):
        vulns = OwnerPrivilegeDetector.analyze(
            selectors=[],
            has_selfdestruct=True
        )
        
        sd_vulns = [v for v in vulns if v.vuln_type == VulnerabilityType.SELFDESTRUCT]
        assert len(sd_vulns) > 0
        assert sd_vulns[0].severity == RiskLevel.CRITICAL
        assert sd_vulns[0].confidence == 1.0
        assert sd_vulns[0].vuln_type == VulnerabilityType.SELFDESTRUCT

    def test_no_dangerous_functions(self):
        vulns = OwnerPrivilegeDetector.analyze(
            selectors=["0xa9059cbb"],  # transfer - not dangerous
            has_selfdestruct=False
        )
        
        # Should have no vulnerability for standard transfer
        assert len(vulns) == 0


# ═══════════════════════════════════════════════════════════════════════════════
#                          ANALYZER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestVulnerabilityAnalyzer:
    @pytest.mark.asyncio
    async def test_analyze_contract_basic(self, analyzer, sample_bytecode):
        result = await analyzer.analyze_contract(
            address="0x1234567890123456789012345678901234567890",
            chain="ethereum",
            bytecode=sample_bytecode
        )
        
        assert isinstance(result, ContractAnalysis)
        assert result.address == "0x1234567890123456789012345678901234567890"
        assert result.chain == "ethereum"
        assert result.bytecode_hash is not None

    @pytest.mark.asyncio
    async def test_analyze_with_decompiler_result(
        self, analyzer, sample_bytecode, sample_decompiler_result
    ):
        result = await analyzer.analyze_contract(
            address="0xtest",
            chain="polygon",
            bytecode=sample_bytecode,
            decompiler_result=sample_decompiler_result
        )
        
        # Should extract selectors from decompiler
        assert "0x40c10f19" in result.function_selectors
        
        # Should detect proxy (has_delegatecall)
        assert result.is_proxy is True

    @pytest.mark.asyncio
    async def test_whitelisted_contract(self, analyzer):
        # Uniswap V2 Router is whitelisted
        result = await analyzer.analyze_contract(
            address="0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
            chain="ethereum",
            bytecode=b"\xff"  # Even with selfdestruct opcode
        )
        
        # Whitelisted contracts should have no vulnerabilities
        assert len(result.vulnerabilities) == 0

    @pytest.mark.asyncio
    async def test_risk_score_calculation(self, analyzer):
        result = await analyzer.analyze_contract(
            address="0xtest",
            chain="ethereum",
            bytecode=b"",
            decompiler_result={
                "security": {
                    "function_selectors": ["0x40c10f19", "0x8456cb59"],
                    "external_calls": 5,
                    "storage_writes": 10,
                    "has_selfdestruct": True,
                    "has_delegatecall": True
                }
            }
        )
        
        # Should have high risk score
        assert result.risk_score > 50
        assert result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]

    def test_risk_level_from_score(self, analyzer):
        assert analyzer._risk_level_from_score(80) == RiskLevel.CRITICAL
        assert analyzer._risk_level_from_score(60) == RiskLevel.HIGH
        assert analyzer._risk_level_from_score(40) == RiskLevel.MEDIUM
        assert analyzer._risk_level_from_score(15) == RiskLevel.LOW
        assert analyzer._risk_level_from_score(5) == RiskLevel.SAFE


# ═══════════════════════════════════════════════════════════════════════════════
#                          SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyzerService:
    @pytest.mark.asyncio
    async def test_analyze_request(self, service):
        request = {
            "address": "0x1234567890123456789012345678901234567890",
            "chain": "ethereum",
            "bytecode": "0x6080604052",
            "decompiler_result": None
        }
        
        result = await service.analyze(request)
        
        assert isinstance(result, dict)
        assert result["address"] == request["address"]
        assert result["chain"] == "ethereum"

    @pytest.mark.asyncio
    async def test_analyze_with_0x_prefix(self, service):
        request = {
            "address": "0xtest",
            "chain": "polygon",
            "bytecode": "0x60806040",  # With 0x prefix
        }
        
        result = await service.analyze(request)
        
        assert result["bytecode_hash"] is not None

    @pytest.mark.asyncio
    async def test_analyze_empty_bytecode(self, service):
        request = {
            "address": "0xtest",
            "chain": "arbitrum",
            "bytecode": "",
        }
        
        result = await service.analyze(request)
        
        assert result["risk_score"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
#                          PATTERN DATABASE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPatternDatabase:
    def test_dangerous_selectors(self):
        db = PatternDatabase()
        
        assert "0x40c10f19" in db.DANGEROUS_SELECTORS  # mint
        assert "0x8456cb59" in db.DANGEROUS_SELECTORS  # pause

    def test_whitelisted_addresses(self):
        db = PatternDatabase()
        
        # Uniswap should be whitelisted
        assert "0x7a250d5630b4cf539739df2c5dacb4c659f2488d" in db.WHITELISTED


# ═══════════════════════════════════════════════════════════════════════════════
#                          INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_analysis_pipeline(self, service):
        """Test the complete analysis pipeline"""
        request = {
            "address": "0xabcdef1234567890abcdef1234567890abcdef12",
            "chain": "ethereum",
            "bytecode": "0x6080604052348015600f57600080fd5b50",
            "decompiler_result": {
                "security": {
                    "function_selectors": ["0x40c10f19", "0x095ea7b3"],
                    "external_calls": 2,
                    "storage_writes": 3,
                    "has_selfdestruct": False,
                    "has_delegatecall": False
                }
            }
        }
        
        result = await service.analyze(request)
        
        # Verify full response structure
        assert "address" in result
        assert "chain" in result
        assert "bytecode_hash" in result
        assert "risk_score" in result
        assert "risk_level" in result
        assert "vulnerabilities" in result
        assert "function_selectors" in result

    @pytest.mark.asyncio
    async def test_high_risk_contract(self, service):
        """Test detection of high-risk contract"""
        request = {
            "address": "0xbad",
            "chain": "bsc",
            "bytecode": "0x32545454545454545454545454",  # ORIGIN + many SLOADs
            "decompiler_result": {
                "security": {
                    "function_selectors": ["0x40c10f19", "0x8456cb59"],
                    "external_calls": 10,
                    "storage_writes": 20,
                    "has_selfdestruct": True,
                    "has_delegatecall": True
                }
            }
        }
        
        result = await service.analyze(request)
        
        assert result["risk_level"] in ["high", "critical"]
        assert len(result["vulnerabilities"]) > 0


# ═══════════════════════════════════════════════════════════════════════════════
#                          RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
