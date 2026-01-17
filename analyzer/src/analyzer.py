"""
 ██████╗ ███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗
██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║
███████╗ █████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║
╚════██║ ██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║
███████║ ███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
╚══════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝

SENTINEL SHIELD - ML-based Vulnerability Pattern Analyzer
Author: SENTINEL Team

This module provides intelligent pattern detection for:
- Honeypot tokens
- Rug pull patterns  
- Hidden fee mechanisms
- Malicious owner functions
- Reentrancy vulnerabilities
"""

import json
import asyncio
import hashlib
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from enum import Enum
from pathlib import Path
import logging

# ═══════════════════════════════════════════════════════════════════════════════
#                              LOGGING SETUP
# ═══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("sentinel.analyzer")

# ═══════════════════════════════════════════════════════════════════════════════
#                              ENUMS & TYPES
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
    BURN_FUNCTION = "burn_function"
    BLACKLIST = "blacklist"
    PAUSE = "pause"
    PROXY_UPGRADE = "proxy_upgrade"
    SELFDESTRUCT = "selfdestruct"
    APPROVAL_EXPLOIT = "approval_exploit"
    FLASH_LOAN_ATTACK = "flash_loan_attack"

# ═══════════════════════════════════════════════════════════════════════════════
#                              DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Vulnerability:
    """Represents a detected vulnerability"""
    vuln_type: VulnerabilityType
    severity: RiskLevel
    title: str
    description: str
    location: Optional[str] = None
    confidence: float = 0.0  # 0-1
    
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
    """Complete analysis result for a contract"""
    address: str
    chain: str
    bytecode_hash: str
    is_verified: bool = False
    is_proxy: bool = False
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    risk_score: int = 0  # 0-100
    risk_level: RiskLevel = RiskLevel.SAFE
    function_selectors: List[str] = field(default_factory=list)
    owner_address: Optional[str] = None
    token_info: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "address": self.address,
            "chain": self.chain,
            "bytecode_hash": self.bytecode_hash,
            "is_verified": self.is_verified,
            "is_proxy": self.is_proxy,
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "function_selectors": self.function_selectors,
            "owner_address": self.owner_address,
            "token_info": self.token_info
        }

# ═══════════════════════════════════════════════════════════════════════════════
#                          PATTERN DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

class PatternDatabase:
    """
    Known vulnerability patterns and function signatures
    These are heuristics based on common attack patterns
    """
    
    # Known malicious function selectors
    DANGEROUS_SELECTORS = {
        "0x42966c68": ("burn", "Can burn tokens from any address"),
        "0x40c10f19": ("mint", "Can mint new tokens"),
        "0x095ea7b3": ("approve", "Standard approval function"),
        "0xa9059cbb": ("transfer", "Standard transfer function"),
        "0x23b872dd": ("transferFrom", "Standard transferFrom"),
        "0x8456cb59": ("pause", "Can pause all transfers"),
        "0x3f4ba83a": ("unpause", "Can unpause transfers"),
        "0xf2fde38b": ("transferOwnership", "Can transfer ownership"),
        "0x715018a6": ("renounceOwnership", "Can renounce ownership"),
        "0x5c975abb": ("paused", "Check if paused"),
        "0x8da5cb5b": ("owner", "Get owner address"),
    }
    
    # Honeypot patterns in bytecode
    HONEYPOT_PATTERNS = [
        # Cannot sell pattern - transfer always reverts for non-owner
        b"\x60\x00\x80\xfd",  # PUSH1 0x00, DUP1, REVERT
        # Hidden fee modification
        b"\x55\x60\x64",  # SSTORE with 100% fee
    ]
    
    # Known rug pull bytecode patterns
    RUG_PATTERNS = [
        # Drain function pattern
        b"\xf0\x70\x39\x58\x57",  # CREATE followed by PUSH/JUMPI
    ]
    
    # Known safe contracts (whitelisted)
    WHITELISTED = {
        # Uniswap V2
        "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
        # Uniswap V3
        "0xe592427a0aece92de3edee1f18e0157c05861564",
        # OpenZeppelin implementations
    }

# ═══════════════════════════════════════════════════════════════════════════════
#                          PATTERN MATCHERS
# ═══════════════════════════════════════════════════════════════════════════════

class HoneypotDetector:
    """Detects honeypot token patterns"""
    
    @staticmethod
    def analyze(bytecode: bytes, selectors: List[str]) -> List[Vulnerability]:
        vulnerabilities = []
        
        # Check for hidden transfer restrictions
        if HoneypotDetector._check_transfer_restrictions(bytecode):
            vulnerabilities.append(Vulnerability(
                vuln_type=VulnerabilityType.HONEYPOT,
                severity=RiskLevel.CRITICAL,
                title="Possible Honeypot - Transfer Restriction",
                description="Contract may restrict selling or transferring tokens",
                confidence=0.75
            ))
        
        # Check for dynamic fee manipulation
        if HoneypotDetector._check_fee_manipulation(bytecode):
            vulnerabilities.append(Vulnerability(
                vuln_type=VulnerabilityType.HIDDEN_FEE,
                severity=RiskLevel.HIGH,
                title="Dynamic Fee Detected",
                description="Contract can modify transaction fees dynamically",
                confidence=0.80
            ))
        
        return vulnerabilities
    
    @staticmethod
    def _check_transfer_restrictions(bytecode: bytes) -> bool:
        """Check for patterns that restrict transfers"""
        # Look for tx.origin checks (common in honeypots)
        if b"\x32" in bytecode:  # ORIGIN opcode
            return True
        
        # Look for blacklist mapping access patterns
        # SLOAD after hashing sender address
        if bytecode.count(b"\x54") > 10:  # Many SLOAD operations
            return True
        
        return False
    
    @staticmethod
    def _check_fee_manipulation(bytecode: bytes) -> bool:
        """Check for dynamic fee patterns"""
        # Look for percentage calculations that could be fees
        # Division by 100 or similar patterns
        if b"\x60\x64\x04" in bytecode:  # PUSH1 100, DIV
            return True
        return False


class ReentrancyDetector:
    """Detects reentrancy vulnerability patterns"""
    
    @staticmethod
    def analyze(bytecode: bytes, external_calls: int, storage_writes: int) -> List[Vulnerability]:
        vulnerabilities = []
        
        # If there are external calls followed by storage writes
        if external_calls > 0 and storage_writes > 0:
            # This is a simplified check - real analysis would trace execution paths
            vulnerabilities.append(Vulnerability(
                vuln_type=VulnerabilityType.REENTRANCY,
                severity=RiskLevel.HIGH,
                title="Potential Reentrancy Risk",
                description=f"Contract has {external_calls} external calls and {storage_writes} storage writes. Verify CEI pattern.",
                confidence=0.60
            ))
        
        return vulnerabilities


class OwnerPrivilegeDetector:
    """Detects dangerous owner privileges"""
    
    DANGEROUS_FUNCTIONS = {
        "0x40c10f19": (
            "mint",
            RiskLevel.HIGH,
            "Owner can mint unlimited tokens",
            VulnerabilityType.MINT_FUNCTION,
        ),
        "0x42966c68": (
            "burn",
            RiskLevel.MEDIUM,
            "Owner can burn tokens",
            VulnerabilityType.BURN_FUNCTION,
        ),
        "0x8456cb59": (
            "pause",
            RiskLevel.HIGH,
            "Owner can pause all transfers",
            VulnerabilityType.PAUSE,
        ),
        "0xff": (
            "selfdestruct",
            RiskLevel.CRITICAL,
            "Contract can be destroyed",
            VulnerabilityType.SELFDESTRUCT,
        ),
    }
    
    @staticmethod
    def analyze(selectors: List[str], has_selfdestruct: bool) -> List[Vulnerability]:
        vulnerabilities = []
        
        for selector in selectors:
            if selector in OwnerPrivilegeDetector.DANGEROUS_FUNCTIONS:
                name, severity, desc, vuln_type = OwnerPrivilegeDetector.DANGEROUS_FUNCTIONS[selector]
                vulnerabilities.append(Vulnerability(
                    vuln_type=vuln_type,
                    severity=severity,
                    title=f"Dangerous Function: {name}()",
                    description=desc,
                    location=selector,
                    confidence=0.95
                ))
        
        if has_selfdestruct:
            vulnerabilities.append(Vulnerability(
                vuln_type=VulnerabilityType.SELFDESTRUCT,
                severity=RiskLevel.CRITICAL,
                title="SELFDESTRUCT Capability",
                description="Contract can be destroyed and all funds transferred to owner",
                confidence=1.0
            ))
        
        return vulnerabilities

# ═══════════════════════════════════════════════════════════════════════════════
#                          MAIN ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

class VulnerabilityAnalyzer:
    """
    Main vulnerability analyzer that coordinates all detection modules
    """
    
    def __init__(self):
        self.pattern_db = PatternDatabase()
        self.honeypot_detector = HoneypotDetector()
        self.reentrancy_detector = ReentrancyDetector()
        self.owner_detector = OwnerPrivilegeDetector()
    
    async def analyze_contract(
        self,
        address: str,
        chain: str,
        bytecode: bytes,
        decompiler_result: Optional[Dict] = None
    ) -> ContractAnalysis:
        """
        Perform comprehensive vulnerability analysis on a contract
        
        Args:
            address: Contract address
            chain: Chain identifier
            bytecode: Raw contract bytecode
            decompiler_result: Optional output from Rust decompiler
        """
        logger.info(f"Analyzing contract {address} on {chain}")
        
        # Initialize analysis result
        analysis = ContractAnalysis(
            address=address,
            chain=chain,
            bytecode_hash=hashlib.sha256(bytecode).hexdigest()
        )
        
        # Extract data from decompiler if available
        selectors = []
        external_calls = 0
        storage_writes = 0
        has_selfdestruct = False
        
        if decompiler_result:
            security = decompiler_result.get("security", {})
            selectors = security.get("function_selectors", [])
            external_calls = security.get("external_calls", 0)
            storage_writes = security.get("storage_writes", 0)
            has_selfdestruct = security.get("has_selfdestruct", False)
            
            analysis.function_selectors = selectors
            analysis.is_proxy = security.get("has_delegatecall", False)
        
        # Run all detectors
        all_vulns = []
        
        # 1. Honeypot detection
        all_vulns.extend(
            self.honeypot_detector.analyze(bytecode, selectors)
        )
        
        # 2. Reentrancy detection
        all_vulns.extend(
            self.reentrancy_detector.analyze(bytecode, external_calls, storage_writes)
        )
        
        # 3. Owner privilege detection
        all_vulns.extend(
            self.owner_detector.analyze(selectors, has_selfdestruct)
        )
        
        # 4. Check against whitelist
        if address.lower() in self.pattern_db.WHITELISTED:
            logger.info(f"Contract {address} is whitelisted")
            all_vulns = []  # Clear vulnerabilities for known safe contracts
        
        analysis.vulnerabilities = all_vulns
        
        # Calculate risk score
        analysis.risk_score = self._calculate_risk_score(all_vulns)
        analysis.risk_level = self._risk_level_from_score(analysis.risk_score)
        
        logger.info(f"Analysis complete: {len(all_vulns)} vulnerabilities, risk score: {analysis.risk_score}")
        
        return analysis
    
    def _calculate_risk_score(self, vulnerabilities: List[Vulnerability]) -> int:
        """Calculate overall risk score 0-100"""
        if not vulnerabilities:
            return 0
        
        score = 0
        weights = {
            RiskLevel.CRITICAL: 40,
            RiskLevel.HIGH: 25,
            RiskLevel.MEDIUM: 15,
            RiskLevel.LOW: 5,
            RiskLevel.SAFE: 0
        }
        
        for vuln in vulnerabilities:
            base_weight = weights.get(vuln.severity, 10)
            score += int(base_weight * vuln.confidence)
        
        return min(100, score)
    
    def _risk_level_from_score(self, score: int) -> RiskLevel:
        """Convert numeric score to risk level"""
        if score >= 70:
            return RiskLevel.CRITICAL
        elif score >= 50:
            return RiskLevel.HIGH
        elif score >= 30:
            return RiskLevel.MEDIUM
        elif score >= 10:
            return RiskLevel.LOW
        else:
            return RiskLevel.SAFE

# ═══════════════════════════════════════════════════════════════════════════════
#                              API INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class AnalyzerService:
    """
    HTTP service interface for the analyzer
    Designed to be called from the Go API server
    """
    
    def __init__(self):
        self.analyzer = VulnerabilityAnalyzer()
    
    async def analyze(self, request: Dict) -> Dict:
        """
        Process analysis request
        
        Expected request format:
        {
            "address": "0x...",
            "chain": "ethereum",
            "bytecode": "0x6060...",
            "decompiler_result": { ... }  # Optional
        }
        """
        address = request.get("address", "")
        chain = request.get("chain", "ethereum")
        bytecode_hex = request.get("bytecode", "")
        decompiler_result = request.get("decompiler_result")
        
        # Parse bytecode
        bytecode_clean = bytecode_hex.replace("0x", "")
        bytecode = bytes.fromhex(bytecode_clean) if bytecode_clean else b""
        
        # Run analysis
        result = await self.analyzer.analyze_contract(
            address=address,
            chain=chain,
            bytecode=bytecode,
            decompiler_result=decompiler_result
        )
        
        return result.to_dict()

# ═══════════════════════════════════════════════════════════════════════════════
#                                  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """Test the analyzer with sample bytecode"""
    print("""
 ██████╗ ███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗
██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║
███████╗ █████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║
╚════██║ ██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║
███████║ ███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
╚══════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝

        ML-based Vulnerability Analyzer v0.1.0
    """)
    
    # Sample test
    service = AnalyzerService()
    
    # Simulated request with decompiler output
    test_request = {
        "address": "0x1234567890123456789012345678901234567890",
        "chain": "ethereum",
        "bytecode": "0x6080604052",  # Minimal bytecode
        "decompiler_result": {
            "security": {
                "function_selectors": ["0x40c10f19", "0x8456cb59"],  # mint, pause
                "external_calls": 3,
                "storage_writes": 5,
                "has_selfdestruct": False,
                "has_delegatecall": True
            }
        }
    }
    
    result = await service.analyze(test_request)
    
    print("\n" + "═" * 70)
    print("                    ANALYSIS RESULTS")
    print("═" * 70 + "\n")
    
    print(json.dumps(result, indent=2))
    
    print("\n" + "═" * 70)
    print(f"Risk Score: {result['risk_score']}/100")
    print(f"Risk Level: {result['risk_level'].upper()}")
    print(f"Vulnerabilities Found: {len(result['vulnerabilities'])}")
    print("═" * 70)

if __name__ == "__main__":
    asyncio.run(main())
