"""
SENTINEL SHIELD - Professional Smart Contract Security Suite
=============================================================

Ready for: Trail of Bits • OpenZeppelin • Consensys • Spearbit

Modules:
- vulnerabilities/ - SWC + DeFi + MEV vulnerability database
- detectors/ - MEV, Proxy, Bridge security detectors  
- integrations/ - Slither, Mythril, Manticore integration
- verification/ - SMT-based formal verification
- reports/ - Professional audit report generation
"""

__version__ = "2.0.0"
__codename__ = "SHIELD"
__author__ = "SENTINEL Team"

from sentinel.engine import (
    SentinelSecurityEngine,
    SecurityIssue,
    ScanResult,
    SeverityLevel,
    quick_scan,
    full_audit,
)

__all__ = [
    "SentinelSecurityEngine",
    "SecurityIssue", 
    "ScanResult",
    "SeverityLevel",
    "quick_scan",
    "full_audit",
]
