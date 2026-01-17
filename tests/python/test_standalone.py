"""
═══════════════════════════════════════════════════════════════════════════════
 SENTINEL SHIELD - Python Analyzer Tests (Simplified)
 Standalone test suite that works without full dependencies
 Author: SENTINEL Team
═══════════════════════════════════════════════════════════════════════════════
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import hashlib

# ═══════════════════════════════════════════════════════════════════════════════
#                          INLINE DEFINITIONS (for testing)
# ═══════════════════════════════════════════════════════════════════════════════

class RiskLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SAFE = "safe"


class VulnerabilityType(Enum):
    HONEYPOT = "honeypot"
    RUG_PULL = "rug_pull"
    HIDDEN_FEE = "hidden_fee"
    REENTRANCY = "reentrancy"
    MINT_FUNCTION = "mint_function"
    SELFDESTRUCT = "selfdestruct"


@dataclass
class Vulnerability:
    vuln_type: VulnerabilityType
    severity: RiskLevel
    title: str
    description: str
    location: Optional[str] = None
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "type": self.vuln_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "confidence": self.confidence
        }


@dataclass
class ContractAnalysis:
    address: str
    chain: str
    bytecode_hash: str
    is_verified: bool = False
    is_proxy: bool = False
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    risk_score: int = 0
    risk_level: RiskLevel = RiskLevel.SAFE
    function_selectors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "address": self.address,
            "chain": self.chain,
            "bytecode_hash": self.bytecode_hash,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
            "function_selectors": self.function_selectors
        }


class PatternDatabase:
    DANGEROUS_SELECTORS = {
        "0x40c10f19": ("mint", "Can mint new tokens"),
        "0x8456cb59": ("pause", "Can pause all transfers"),
    }
    WHITELISTED = {"0x7a250d5630b4cf539739df2c5dacb4c659f2488d"}


class HoneypotDetector:
    @staticmethod
    def analyze(bytecode: bytes, selectors: List[str]) -> List[Vulnerability]:
        vulnerabilities = []
        
        if b"\x32" in bytecode:  # ORIGIN opcode
            vulnerabilities.append(Vulnerability(
                vuln_type=VulnerabilityType.HONEYPOT,
                severity=RiskLevel.CRITICAL,
                title="Possible Honeypot - ORIGIN Check",
                description="Uses tx.origin which is common in honeypots",
                confidence=0.75
            ))
        
        if b"\x60\x64\x04" in bytecode:  # PUSH1 100 DIV
            vulnerabilities.append(Vulnerability(
                vuln_type=VulnerabilityType.HIDDEN_FEE,
                severity=RiskLevel.HIGH,
                title="Dynamic Fee Detected",
                description="Contract can modify transaction fees",
                confidence=0.80
            ))
        
        return vulnerabilities


class ReentrancyDetector:
    @staticmethod
    def analyze(bytecode: bytes, external_calls: int, storage_writes: int) -> List[Vulnerability]:
        vulnerabilities = []
        
        if external_calls > 0 and storage_writes > 0:
            vulnerabilities.append(Vulnerability(
                vuln_type=VulnerabilityType.REENTRANCY,
                severity=RiskLevel.HIGH,
                title="Potential Reentrancy Risk",
                description=f"{external_calls} external calls with {storage_writes} storage writes",
                confidence=0.60
            ))
        
        return vulnerabilities


class OwnerPrivilegeDetector:
    DANGEROUS_FUNCTIONS = {
        "0x40c10f19": ("mint", RiskLevel.HIGH, "Owner can mint unlimited tokens"),
        "0x8456cb59": ("pause", RiskLevel.HIGH, "Owner can pause all transfers"),
    }
    
    @staticmethod
    def analyze(selectors: List[str], has_selfdestruct: bool) -> List[Vulnerability]:
        vulnerabilities = []
        
        for selector in selectors:
            if selector in OwnerPrivilegeDetector.DANGEROUS_FUNCTIONS:
                name, severity, desc = OwnerPrivilegeDetector.DANGEROUS_FUNCTIONS[selector]
                vulnerabilities.append(Vulnerability(
                    vuln_type=VulnerabilityType.MINT_FUNCTION if name == "mint" else VulnerabilityType.REENTRANCY,
                    severity=severity,
                    title=f"Dangerous Function: {name}",
                    description=desc,
                    confidence=0.90
                ))
        
        if has_selfdestruct:
            vulnerabilities.append(Vulnerability(
                vuln_type=VulnerabilityType.SELFDESTRUCT,
                severity=RiskLevel.CRITICAL,
                title="Contract Can Self-Destruct",
                description="Contract contains SELFDESTRUCT opcode",
                confidence=1.0
            ))
        
        return vulnerabilities


class VulnerabilityAnalyzer:
    def __init__(self):
        self.pattern_db = PatternDatabase()
    
    async def analyze_contract(
        self,
        address: str,
        chain: str,
        bytecode: bytes,
        decompiler_result: Optional[Dict] = None
    ) -> ContractAnalysis:
        bytecode_hash = "0x" + hashlib.sha256(bytecode).hexdigest()
        
        analysis = ContractAnalysis(
            address=address,
            chain=chain,
            bytecode_hash=bytecode_hash
        )
        
        # Check whitelist
        if address.lower() in self.pattern_db.WHITELISTED:
            return analysis
        
        # Extract info from decompiler
        security = decompiler_result.get("security", {}) if decompiler_result else {}
        selectors = security.get("function_selectors", [])
        external_calls = security.get("external_calls", 0)
        storage_writes = security.get("storage_writes", 0)
        has_selfdestruct = security.get("has_selfdestruct", False)
        has_delegatecall = security.get("has_delegatecall", False)
        
        analysis.function_selectors = selectors
        analysis.is_proxy = has_delegatecall
        
        # Run detectors
        analysis.vulnerabilities.extend(HoneypotDetector.analyze(bytecode, selectors))
        analysis.vulnerabilities.extend(ReentrancyDetector.analyze(bytecode, external_calls, storage_writes))
        analysis.vulnerabilities.extend(OwnerPrivilegeDetector.analyze(selectors, has_selfdestruct))
        
        # Calculate risk score
        analysis.risk_score = self._calculate_risk_score(analysis.vulnerabilities)
        analysis.risk_level = self._risk_level_from_score(analysis.risk_score)
        
        return analysis
    
    def _calculate_risk_score(self, vulnerabilities: List[Vulnerability]) -> int:
        score = 0
        for v in vulnerabilities:
            if v.severity == RiskLevel.CRITICAL:
                score += 30
            elif v.severity == RiskLevel.HIGH:
                score += 20
            elif v.severity == RiskLevel.MEDIUM:
                score += 10
            else:
                score += 5
        return min(score, 100)
    
    def _risk_level_from_score(self, score: int) -> RiskLevel:
        if score >= 75:
            return RiskLevel.CRITICAL
        elif score >= 50:
            return RiskLevel.HIGH
        elif score >= 25:
            return RiskLevel.MEDIUM
        elif score >= 10:
            return RiskLevel.LOW
        return RiskLevel.SAFE


class AnalyzerService:
    def __init__(self):
        self.analyzer = VulnerabilityAnalyzer()
    
    async def analyze(self, request: Dict) -> Dict:
        bytecode_str = request.get("bytecode", "")
        if bytecode_str.startswith("0x"):
            bytecode_str = bytecode_str[2:]
        bytecode = bytes.fromhex(bytecode_str) if bytecode_str else b""
        
        result = await self.analyzer.analyze_contract(
            address=request.get("address", ""),
            chain=request.get("chain", "ethereum"),
            bytecode=bytecode,
            decompiler_result=request.get("decompiler_result")
        )
        return result.to_dict()


# ═══════════════════════════════════════════════════════════════════════════════
#                              TESTS
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


class TestHoneypotDetector:
    def test_detect_origin_check(self):
        bytecode = bytes([0x32])  # ORIGIN opcode
        vulns = HoneypotDetector.analyze(bytecode, [])
        
        honeypot_vulns = [v for v in vulns if v.vuln_type == VulnerabilityType.HONEYPOT]
        assert len(honeypot_vulns) > 0

    def test_safe_bytecode(self):
        bytecode = bytes([0x60, 0x80])  # PUSH1 0x80
        vulns = HoneypotDetector.analyze(bytecode, [])
        
        honeypot_vulns = [v for v in vulns if v.vuln_type == VulnerabilityType.HONEYPOT]
        assert len(honeypot_vulns) == 0

    def test_fee_manipulation_detection(self):
        bytecode = bytes([0x60, 0x64, 0x04])  # PUSH1 100 DIV
        vulns = HoneypotDetector.analyze(bytecode, [])
        
        fee_vulns = [v for v in vulns if v.vuln_type == VulnerabilityType.HIDDEN_FEE]
        assert len(fee_vulns) > 0


class TestReentrancyDetector:
    def test_detect_reentrancy_risk(self):
        vulns = ReentrancyDetector.analyze(b"", external_calls=3, storage_writes=5)
        
        assert len(vulns) > 0
        assert vulns[0].vuln_type == VulnerabilityType.REENTRANCY

    def test_no_reentrancy_without_external_calls(self):
        vulns = ReentrancyDetector.analyze(b"", external_calls=0, storage_writes=10)
        assert len(vulns) == 0

    def test_no_reentrancy_without_storage_writes(self):
        vulns = ReentrancyDetector.analyze(b"", external_calls=5, storage_writes=0)
        assert len(vulns) == 0


class TestOwnerPrivilegeDetector:
    def test_detect_mint_function(self):
        vulns = OwnerPrivilegeDetector.analyze(["0x40c10f19"], False)
        
        mint_vulns = [v for v in vulns if "mint" in v.title.lower()]
        assert len(mint_vulns) > 0

    def test_detect_pause_function(self):
        vulns = OwnerPrivilegeDetector.analyze(["0x8456cb59"], False)
        
        pause_vulns = [v for v in vulns if "pause" in v.title.lower()]
        assert len(pause_vulns) > 0

    def test_detect_selfdestruct(self):
        vulns = OwnerPrivilegeDetector.analyze([], has_selfdestruct=True)
        
        sd_vulns = [v for v in vulns if v.vuln_type == VulnerabilityType.SELFDESTRUCT]
        assert len(sd_vulns) > 0
        assert sd_vulns[0].severity == RiskLevel.CRITICAL
        assert sd_vulns[0].confidence == 1.0


class TestVulnerabilityAnalyzer:
    @pytest.mark.asyncio
    async def test_analyze_contract_basic(self):
        analyzer = VulnerabilityAnalyzer()
        bytecode = bytes.fromhex("6080604052")
        
        result = await analyzer.analyze_contract(
            address="0x1234567890123456789012345678901234567890",
            chain="ethereum",
            bytecode=bytecode
        )
        
        assert isinstance(result, ContractAnalysis)
        assert result.address == "0x1234567890123456789012345678901234567890"
        assert result.chain == "ethereum"

    @pytest.mark.asyncio
    async def test_whitelisted_contract(self):
        analyzer = VulnerabilityAnalyzer()
        
        result = await analyzer.analyze_contract(
            address="0x7a250d5630b4cf539739df2c5dacb4c659f2488d",  # Uniswap
            chain="ethereum",
            bytecode=bytes([0xff])  # SELFDESTRUCT
        )
        
        assert len(result.vulnerabilities) == 0

    @pytest.mark.asyncio
    async def test_with_decompiler_result(self):
        analyzer = VulnerabilityAnalyzer()
        
        result = await analyzer.analyze_contract(
            address="0xtest",
            chain="polygon",
            bytecode=b"",
            decompiler_result={
                "security": {
                    "function_selectors": ["0x40c10f19"],
                    "external_calls": 2,
                    "storage_writes": 5,
                    "has_selfdestruct": False,
                    "has_delegatecall": True
                }
            }
        )
        
        assert "0x40c10f19" in result.function_selectors
        assert result.is_proxy is True

    def test_risk_level_from_score(self):
        analyzer = VulnerabilityAnalyzer()
        assert analyzer._risk_level_from_score(80) == RiskLevel.CRITICAL
        assert analyzer._risk_level_from_score(60) == RiskLevel.HIGH
        assert analyzer._risk_level_from_score(30) == RiskLevel.MEDIUM
        assert analyzer._risk_level_from_score(15) == RiskLevel.LOW
        assert analyzer._risk_level_from_score(5) == RiskLevel.SAFE


class TestAnalyzerService:
    @pytest.mark.asyncio
    async def test_analyze_request(self):
        service = AnalyzerService()
        
        request = {
            "address": "0x1234567890123456789012345678901234567890",
            "chain": "ethereum",
            "bytecode": "0x6080604052"
        }
        
        result = await service.analyze(request)
        
        assert isinstance(result, dict)
        assert result["address"] == request["address"]
        assert result["chain"] == "ethereum"

    @pytest.mark.asyncio
    async def test_analyze_empty_bytecode(self):
        service = AnalyzerService()
        
        request = {
            "address": "0xtest",
            "chain": "arbitrum",
            "bytecode": ""
        }
        
        result = await service.analyze(request)
        assert result["risk_score"] == 0


class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_analysis_pipeline(self):
        service = AnalyzerService()
        
        request = {
            "address": "0xabcdef1234567890abcdef1234567890abcdef12",
            "chain": "ethereum",
            "bytecode": "0x6080604052",
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
        
        assert "address" in result
        assert "chain" in result
        assert "bytecode_hash" in result
        assert "risk_score" in result
        assert "risk_level" in result
        assert "vulnerabilities" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
