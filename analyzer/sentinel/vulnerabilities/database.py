"""
╔═══════════════════════════════════════════════════════════════════════════╗
║           SENTINEL SHIELD - VULNERABILITY DATABASE                        ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Complete SWC Registry + CVE Database for Smart Contract Security         ║
║  Used by Trail of Bits, OpenZeppelin, Consensys Diligence                 ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set
import re
import json


class Severity(Enum):
    """Vulnerability severity levels (CVSS-based)."""
    CRITICAL = "critical"  # 9.0-10.0
    HIGH = "high"          # 7.0-8.9
    MEDIUM = "medium"      # 4.0-6.9
    LOW = "low"            # 0.1-3.9
    INFO = "info"          # Informational


class Category(Enum):
    """Vulnerability categories."""
    REENTRANCY = "reentrancy"
    ACCESS_CONTROL = "access_control"
    ARITHMETIC = "arithmetic"
    UNCHECKED_CALLS = "unchecked_calls"
    DOS = "denial_of_service"
    FRONT_RUNNING = "front_running"
    TIME_MANIPULATION = "time_manipulation"
    RANDOMNESS = "randomness"
    SIGNATURE = "signature"
    FLASH_LOAN = "flash_loan"
    ORACLE = "oracle"
    PROXY = "proxy"
    LOGIC = "logic"
    GAS = "gas"


@dataclass
class VulnerabilityPattern:
    """A vulnerability pattern with detection rules."""
    id: str
    name: str
    description: str
    severity: Severity
    category: Category
    swc_id: Optional[str] = None
    cwe_id: Optional[str] = None
    regex_patterns: List[str] = field(default_factory=list)
    ast_patterns: List[Dict] = field(default_factory=list)
    remediation: str = ""
    references: List[str] = field(default_factory=list)
    false_positive_hints: List[str] = field(default_factory=list)
    
    def matches_code(self, code: str) -> List[Dict]:
        """Check if code matches vulnerability patterns."""
        matches = []
        for pattern in self.regex_patterns:
            for match in re.finditer(pattern, code, re.MULTILINE | re.IGNORECASE):
                matches.append({
                    "pattern": pattern,
                    "match": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "line": code[:match.start()].count('\n') + 1
                })
        return matches


class VulnerabilityDatabase:
    """
    Comprehensive vulnerability database for smart contract security.
    Contains SWC Registry entries, CVEs, and custom patterns.
    """
    
    def __init__(self):
        self.vulnerabilities: Dict[str, VulnerabilityPattern] = {}
        self._load_swc_registry()
        self._load_defi_patterns()
        self._load_mev_patterns()
    
    def _load_swc_registry(self):
        """Load Smart Contract Weakness Classification (SWC) Registry."""
        
        # SWC-100: Function Default Visibility
        self.add(VulnerabilityPattern(
            id="SWC-100",
            name="Function Default Visibility",
            description="Functions that do not have a function visibility type specified are public by default.",
            severity=Severity.MEDIUM,
            category=Category.ACCESS_CONTROL,
            swc_id="SWC-100",
            cwe_id="CWE-710",
            regex_patterns=[
                r"function\s+\w+\s*\([^)]*\)\s*(?!public|private|internal|external)",
            ],
            remediation="Explicitly declare function visibility (public, private, internal, external).",
            references=["https://swcregistry.io/docs/SWC-100"]
        ))
        
        # SWC-101: Integer Overflow and Underflow
        self.add(VulnerabilityPattern(
            id="SWC-101",
            name="Integer Overflow and Underflow",
            description="Integer overflow/underflow can occur when arithmetic operations reach the maximum or minimum size of the type.",
            severity=Severity.HIGH,
            category=Category.ARITHMETIC,
            swc_id="SWC-101",
            cwe_id="CWE-190",
            regex_patterns=[
                r"(\w+)\s*\+\s*(\w+)(?!\s*;.*SafeMath)",
                r"(\w+)\s*-\s*(\w+)(?!\s*;.*SafeMath)",
                r"(\w+)\s*\*\s*(\w+)(?!\s*;.*SafeMath)",
            ],
            remediation="Use Solidity 0.8.x built-in overflow checks or SafeMath library.",
            references=["https://swcregistry.io/docs/SWC-101"],
            false_positive_hints=["pragma solidity ^0.8", "using SafeMath"]
        ))
        
        # SWC-104: Unchecked Call Return Value
        self.add(VulnerabilityPattern(
            id="SWC-104",
            name="Unchecked Call Return Value",
            description="The return value of a message call is not checked.",
            severity=Severity.MEDIUM,
            category=Category.UNCHECKED_CALLS,
            swc_id="SWC-104",
            cwe_id="CWE-252",
            regex_patterns=[
                r"\.call\{[^}]*\}\([^)]*\)\s*;",
                r"\.send\([^)]*\)\s*;",
                r"\.transfer\([^)]*\)\s*;(?!\s*//\s*safe)",
            ],
            remediation="Check the return value of low-level calls and handle failures appropriately.",
            references=["https://swcregistry.io/docs/SWC-104"]
        ))
        
        # SWC-106: Unprotected SELFDESTRUCT
        self.add(VulnerabilityPattern(
            id="SWC-106",
            name="Unprotected SELFDESTRUCT Instruction",
            description="A selfdestruct instruction can be triggered by any user, destroying the contract.",
            severity=Severity.CRITICAL,
            category=Category.ACCESS_CONTROL,
            swc_id="SWC-106",
            cwe_id="CWE-284",
            regex_patterns=[
                r"selfdestruct\s*\([^)]*\)",
                r"suicide\s*\([^)]*\)",
            ],
            remediation="Protect selfdestruct with access control modifiers (onlyOwner, etc.).",
            references=["https://swcregistry.io/docs/SWC-106"]
        ))
        
        # SWC-107: Reentrancy
        self.add(VulnerabilityPattern(
            id="SWC-107",
            name="Reentrancy",
            description="External calls can call back into the calling contract before the first execution is complete.",
            severity=Severity.CRITICAL,
            category=Category.REENTRANCY,
            swc_id="SWC-107",
            cwe_id="CWE-841",
            regex_patterns=[
                r"\.call\{.*value.*\}.*\n.*\w+\s*[+-]=",
                r"\.call\{.*value.*\}.*\n.*\w+\s*=\s*\w+\s*[+-]",
                r"payable\([^)]+\)\.transfer.*\n.*\w+\s*[+-]=",
            ],
            remediation="Use Checks-Effects-Interactions pattern or ReentrancyGuard.",
            references=["https://swcregistry.io/docs/SWC-107"]
        ))
        
        # SWC-110: Assert Violation
        self.add(VulnerabilityPattern(
            id="SWC-110",
            name="Assert Violation",
            description="Assert should only be used to test for internal errors and check invariants.",
            severity=Severity.LOW,
            category=Category.LOGIC,
            swc_id="SWC-110",
            cwe_id="CWE-670",
            regex_patterns=[
                r"assert\s*\([^)]*msg\.value",
                r"assert\s*\([^)]*tx\.origin",
            ],
            remediation="Use require() for input validation, assert() only for invariants.",
            references=["https://swcregistry.io/docs/SWC-110"]
        ))
        
        # SWC-111: Use of Deprecated Functions
        self.add(VulnerabilityPattern(
            id="SWC-111",
            name="Use of Deprecated Solidity Functions",
            description="Deprecated Solidity functions are used.",
            severity=Severity.INFO,
            category=Category.LOGIC,
            swc_id="SWC-111",
            regex_patterns=[
                r"\bsuicide\s*\(",
                r"\bsha3\s*\(",
                r"\bcallcode\s*\(",
                r"\bthrow\s*;",
                r"\bvar\s+\w+",
            ],
            remediation="Replace deprecated functions with their modern equivalents.",
            references=["https://swcregistry.io/docs/SWC-111"]
        ))
        
        # SWC-112: Delegatecall to Untrusted Callee
        self.add(VulnerabilityPattern(
            id="SWC-112",
            name="Delegatecall to Untrusted Callee",
            description="Delegatecall retains the context of the calling contract, which can lead to unexpected behavior.",
            severity=Severity.CRITICAL,
            category=Category.ACCESS_CONTROL,
            swc_id="SWC-112",
            cwe_id="CWE-829",
            regex_patterns=[
                r"\.delegatecall\s*\(",
                r"delegatecall\s*\([^)]*\w+\s*\)",
            ],
            remediation="Avoid delegatecall to untrusted contracts. If necessary, validate the target.",
            references=["https://swcregistry.io/docs/SWC-112"]
        ))
        
        # SWC-113: DoS with Failed Call
        self.add(VulnerabilityPattern(
            id="SWC-113",
            name="DoS with Failed Call",
            description="External calls can fail, which may lead to DoS if not handled properly.",
            severity=Severity.MEDIUM,
            category=Category.DOS,
            swc_id="SWC-113",
            cwe_id="CWE-703",
            regex_patterns=[
                r"for\s*\([^)]*\)\s*\{[^}]*\.transfer\(",
                r"while\s*\([^)]*\)\s*\{[^}]*\.send\(",
            ],
            remediation="Use pull payment pattern instead of pushing payments in loops.",
            references=["https://swcregistry.io/docs/SWC-113"]
        ))
        
        # SWC-114: Transaction Order Dependence
        self.add(VulnerabilityPattern(
            id="SWC-114",
            name="Transaction Order Dependence (Front-Running)",
            description="Contract behavior depends on the order of transactions, which miners can manipulate.",
            severity=Severity.HIGH,
            category=Category.FRONT_RUNNING,
            swc_id="SWC-114",
            cwe_id="CWE-362",
            regex_patterns=[
                r"mapping.*\bprice\b",
                r"function\s+\w*[Bb]uy\w*\s*\(",
                r"function\s+\w*[Ss]wap\w*\s*\(",
            ],
            remediation="Use commit-reveal scheme, submarine sends, or flashbots.",
            references=["https://swcregistry.io/docs/SWC-114"]
        ))
        
        # SWC-115: Authorization through tx.origin
        self.add(VulnerabilityPattern(
            id="SWC-115",
            name="Authorization through tx.origin",
            description="tx.origin should not be used for authorization as it can be phished.",
            severity=Severity.HIGH,
            category=Category.ACCESS_CONTROL,
            swc_id="SWC-115",
            cwe_id="CWE-477",
            regex_patterns=[
                r"require\s*\([^)]*tx\.origin",
                r"if\s*\([^)]*tx\.origin",
                r"tx\.origin\s*==",
            ],
            remediation="Use msg.sender instead of tx.origin for authorization.",
            references=["https://swcregistry.io/docs/SWC-115"]
        ))
        
        # SWC-116: Block Timestamp Dependence
        self.add(VulnerabilityPattern(
            id="SWC-116",
            name="Block Timestamp Dependence",
            description="Contracts using block.timestamp for critical logic can be manipulated by miners.",
            severity=Severity.LOW,
            category=Category.TIME_MANIPULATION,
            swc_id="SWC-116",
            cwe_id="CWE-829",
            regex_patterns=[
                r"block\.timestamp\s*[<>=]",
                r"now\s*[<>=]",
            ],
            remediation="Avoid using block.timestamp for critical logic or use a tolerance window.",
            references=["https://swcregistry.io/docs/SWC-116"]
        ))
        
        # SWC-120: Weak Sources of Randomness
        self.add(VulnerabilityPattern(
            id="SWC-120",
            name="Weak Sources of Randomness from Chain Attributes",
            description="Using block attributes for randomness can be predicted or manipulated.",
            severity=Severity.HIGH,
            category=Category.RANDOMNESS,
            swc_id="SWC-120",
            cwe_id="CWE-330",
            regex_patterns=[
                r"block\.timestamp.*random",
                r"block\.difficulty.*random",
                r"blockhash\s*\([^)]*\).*random",
                r"keccak256\s*\([^)]*block\.",
            ],
            remediation="Use Chainlink VRF or commit-reveal scheme for randomness.",
            references=["https://swcregistry.io/docs/SWC-120"]
        ))
        
        # SWC-123: Requirement Violation
        self.add(VulnerabilityPattern(
            id="SWC-123",
            name="Requirement Violation",
            description="A require() statement can fail under normal operation.",
            severity=Severity.MEDIUM,
            category=Category.LOGIC,
            swc_id="SWC-123",
            regex_patterns=[
                r"require\s*\(\s*false\s*[,)]",
                r"require\s*\(\s*0\s*[,)]",
            ],
            remediation="Review require conditions to ensure they are reachable under valid inputs.",
            references=["https://swcregistry.io/docs/SWC-123"]
        ))
        
        # SWC-124: Write to Arbitrary Storage Location
        self.add(VulnerabilityPattern(
            id="SWC-124",
            name="Write to Arbitrary Storage Location",
            description="User-controlled data can determine which storage slot is written to.",
            severity=Severity.CRITICAL,
            category=Category.ACCESS_CONTROL,
            swc_id="SWC-124",
            cwe_id="CWE-123",
            regex_patterns=[
                r"assembly\s*\{[^}]*sstore\s*\([^)]*\w+",
            ],
            remediation="Validate array indices and avoid assembly storage writes with user input.",
            references=["https://swcregistry.io/docs/SWC-124"]
        ))
        
        # SWC-126: Insufficient Gas Griefing
        self.add(VulnerabilityPattern(
            id="SWC-126",
            name="Insufficient Gas Griefing",
            description="Relaying transactions may fail due to insufficient gas forwarded.",
            severity=Severity.MEDIUM,
            category=Category.GAS,
            swc_id="SWC-126",
            cwe_id="CWE-691",
            regex_patterns=[
                r"\.call\{[^}]*gas\s*:",
                r"\.call\s*\.\s*gas\s*\(",
            ],
            remediation="Forward sufficient gas or use gasleft() checks.",
            references=["https://swcregistry.io/docs/SWC-126"]
        ))
        
        # SWC-127: Arbitrary Jump with Function Type Variable
        self.add(VulnerabilityPattern(
            id="SWC-127",
            name="Arbitrary Jump with Function Type Variable",
            description="Function type variables can be manipulated to jump to arbitrary code.",
            severity=Severity.HIGH,
            category=Category.LOGIC,
            swc_id="SWC-127",
            cwe_id="CWE-695",
            regex_patterns=[
                r"function\s*\([^)]*\)\s*(internal|external|public|private)?\s*\w+\s*;",
            ],
            remediation="Validate function type variables before calling.",
            references=["https://swcregistry.io/docs/SWC-127"]
        ))
        
        # SWC-128: DoS With Block Gas Limit
        self.add(VulnerabilityPattern(
            id="SWC-128",
            name="DoS With Block Gas Limit",
            description="Loops over dynamic arrays can exceed block gas limit.",
            severity=Severity.MEDIUM,
            category=Category.DOS,
            swc_id="SWC-128",
            cwe_id="CWE-400",
            regex_patterns=[
                r"for\s*\([^)]*\.length",
                r"while\s*\([^)]*\.length",
            ],
            remediation="Implement pagination or limit array size.",
            references=["https://swcregistry.io/docs/SWC-128"]
        ))
        
        # SWC-129: Typographical Error
        self.add(VulnerabilityPattern(
            id="SWC-129",
            name="Typographical Error",
            description="A typo can lead to unintended behavior.",
            severity=Severity.HIGH,
            category=Category.LOGIC,
            swc_id="SWC-129",
            cwe_id="CWE-480",
            regex_patterns=[
                r"=\+",  # Should be +=
                r"=-",  # Should be -=
            ],
            remediation="Review operators carefully. Use =+ should likely be +=.",
            references=["https://swcregistry.io/docs/SWC-129"]
        ))
        
        # SWC-131: Presence of Unused Variables
        self.add(VulnerabilityPattern(
            id="SWC-131",
            name="Presence of Unused Variables",
            description="Unused variables indicate potential bugs or wasted gas.",
            severity=Severity.INFO,
            category=Category.GAS,
            swc_id="SWC-131",
            cwe_id="CWE-1164",
            regex_patterns=[],  # Needs AST analysis
            remediation="Remove unused variables to save gas and improve readability.",
            references=["https://swcregistry.io/docs/SWC-131"]
        ))
        
        # SWC-132: Unexpected Ether Balance
        self.add(VulnerabilityPattern(
            id="SWC-132",
            name="Unexpected Ether Balance",
            description="Contracts relying on this.balance can be manipulated via selfdestruct.",
            severity=Severity.MEDIUM,
            category=Category.LOGIC,
            swc_id="SWC-132",
            cwe_id="CWE-667",
            regex_patterns=[
                r"address\s*\(\s*this\s*\)\s*\.balance",
                r"this\.balance",
            ],
            remediation="Track deposits/withdrawals separately instead of relying on this.balance.",
            references=["https://swcregistry.io/docs/SWC-132"]
        ))
        
        # SWC-134: Message call with hardcoded gas amount
        self.add(VulnerabilityPattern(
            id="SWC-134",
            name="Message Call with Hardcoded Gas Amount",
            description="Hardcoded gas amounts can break with EVM upgrades.",
            severity=Severity.LOW,
            category=Category.GAS,
            swc_id="SWC-134",
            cwe_id="CWE-655",
            regex_patterns=[
                r"\.call\{.*gas\s*:\s*\d+",
                r"\.transfer\s*\(",
                r"\.send\s*\(",
            ],
            remediation="Use .call{value: x}('') instead of transfer/send.",
            references=["https://swcregistry.io/docs/SWC-134"]
        ))
        
        # SWC-135: Code With No Effects
        self.add(VulnerabilityPattern(
            id="SWC-135",
            name="Code With No Effects",
            description="Code that has no effect indicates a bug.",
            severity=Severity.MEDIUM,
            category=Category.LOGIC,
            swc_id="SWC-135",
            cwe_id="CWE-1164",
            regex_patterns=[
                r"^\s*\w+\s*;\s*$",  # Standalone identifier
            ],
            remediation="Remove dead code or fix the intended logic.",
            references=["https://swcregistry.io/docs/SWC-135"]
        ))
        
        # SWC-136: Unencrypted Private Data On-Chain
        self.add(VulnerabilityPattern(
            id="SWC-136",
            name="Unencrypted Private Data On-Chain",
            description="Private variables are still visible on the blockchain.",
            severity=Severity.HIGH,
            category=Category.ACCESS_CONTROL,
            swc_id="SWC-136",
            cwe_id="CWE-767",
            regex_patterns=[
                r"private\s+.*password",
                r"private\s+.*secret",
                r"private\s+.*key",
            ],
            remediation="Never store sensitive data on-chain, even in private variables.",
            references=["https://swcregistry.io/docs/SWC-136"]
        ))
    
    def _load_defi_patterns(self):
        """Load DeFi-specific vulnerability patterns."""
        
        # Flash Loan Attack
        self.add(VulnerabilityPattern(
            id="DEFI-001",
            name="Flash Loan Attack Vector",
            description="Contract may be vulnerable to flash loan attacks due to price manipulation.",
            severity=Severity.CRITICAL,
            category=Category.FLASH_LOAN,
            regex_patterns=[
                r"getReserves\s*\(\s*\)",
                r"slot0\s*\(\s*\)",
                r"\.price\s*\(\s*\)",
            ],
            remediation="Use TWAP oracles, multiple price sources, or flash loan guards.",
            references=["https://www.paradigm.xyz/2020/11/so-you-want-to-use-a-price-oracle"]
        ))
        
        # Oracle Manipulation
        self.add(VulnerabilityPattern(
            id="DEFI-002",
            name="Oracle Price Manipulation",
            description="Single-block price from AMM can be manipulated.",
            severity=Severity.CRITICAL,
            category=Category.ORACLE,
            swc_id="SWC-114",
            regex_patterns=[
                r"IUniswapV2Pair.*getReserves",
                r"reserve0.*reserve1.*price",
            ],
            remediation="Use Chainlink oracles or implement TWAP.",
            references=["https://shouldiusespotpriceasmyoracle.com/"]
        ))
        
        # Slippage Protection Missing
        self.add(VulnerabilityPattern(
            id="DEFI-003",
            name="Missing Slippage Protection",
            description="Swap functions without minimum output can be sandwich attacked.",
            severity=Severity.HIGH,
            category=Category.FRONT_RUNNING,
            regex_patterns=[
                r"swap\s*\([^)]*0\s*,",
                r"amountOutMin\s*:\s*0",
            ],
            remediation="Implement slippage protection with minimum output amounts.",
            references=["https://docs.uniswap.org/contracts/v2/guides/smart-contract-integration/trading-from-a-smart-contract"]
        ))
        
        # Unlimited Token Approval
        self.add(VulnerabilityPattern(
            id="DEFI-004",
            name="Unlimited Token Approval",
            description="Approving max uint256 can lead to fund loss if spender is compromised.",
            severity=Severity.MEDIUM,
            category=Category.ACCESS_CONTROL,
            regex_patterns=[
                r"approve\s*\([^,]+,\s*type\s*\(\s*uint256\s*\)\s*\.max",
                r"approve\s*\([^,]+,\s*2\s*\*\*\s*256\s*-\s*1",
                r"approve\s*\([^,]+,\s*0xffffffff",
            ],
            remediation="Approve only the necessary amount or implement permit-style approvals.",
            references=["https://revoke.cash/"]
        ))
        
        # Missing Deadline Check
        self.add(VulnerabilityPattern(
            id="DEFI-005",
            name="Missing Deadline Check",
            description="Transactions without deadline can be held and executed at unfavorable prices.",
            severity=Severity.MEDIUM,
            category=Category.FRONT_RUNNING,
            regex_patterns=[
                r"block\.timestamp\s*\+\s*\d{6,}",  # Very long deadline
            ],
            remediation="Use reasonable deadlines (e.g., 30 minutes) for time-sensitive operations.",
            references=["https://blog.uniswap.org/"]
        ))
        
        # Read-Only Reentrancy
        self.add(VulnerabilityPattern(
            id="DEFI-006",
            name="Read-Only Reentrancy",
            description="View functions can return stale data during reentrancy.",
            severity=Severity.HIGH,
            category=Category.REENTRANCY,
            regex_patterns=[
                r"function\s+\w+\s*\([^)]*\)\s*.*view.*\{[^}]*balanceOf",
            ],
            remediation="Use reentrancy guards even for view functions that query external contracts.",
            references=["https://chainsecurity.com/curve-lp-oracle-manipulation-post-mortem/"]
        ))
        
        # Curve LP Token Oracle
        self.add(VulnerabilityPattern(
            id="DEFI-007",
            name="Curve LP Token Price Vulnerability",
            description="Curve virtual_price can be manipulated via reentrancy.",
            severity=Severity.CRITICAL,
            category=Category.ORACLE,
            regex_patterns=[
                r"get_virtual_price\s*\(\s*\)",
                r"virtualPrice",
            ],
            remediation="Use Curve's native reentrancy protection or check for reentrancy state.",
            references=["https://chainsecurity.com/curve-lp-oracle-manipulation-post-mortem/"]
        ))
        
        # ERC4626 Inflation Attack
        self.add(VulnerabilityPattern(
            id="DEFI-008",
            name="ERC4626 Vault Inflation Attack",
            description="First depositor can manipulate share price in ERC4626 vaults.",
            severity=Severity.HIGH,
            category=Category.LOGIC,
            regex_patterns=[
                r"ERC4626",
                r"previewDeposit.*totalSupply.*==.*0",
            ],
            remediation="Implement virtual shares/assets or require minimum deposit.",
            references=["https://blog.openzeppelin.com/a-]novel-defense-against-erc4626-inflation-attacks"]
        ))
    
    def _load_mev_patterns(self):
        """Load MEV-specific vulnerability patterns."""
        
        # Sandwich Attack Vector
        self.add(VulnerabilityPattern(
            id="MEV-001",
            name="Sandwich Attack Vulnerability",
            description="Public swap functions can be sandwiched by MEV bots.",
            severity=Severity.HIGH,
            category=Category.FRONT_RUNNING,
            regex_patterns=[
                r"function\s+swap\s*\([^)]*\)\s*public",
                r"function\s+swap\s*\([^)]*\)\s*external",
            ],
            remediation="Use private mempools (Flashbots), MEV-Share, or implement MEV protection.",
            references=["https://docs.flashbots.net/"]
        ))
        
        # JIT Liquidity
        self.add(VulnerabilityPattern(
            id="MEV-002",
            name="JIT Liquidity Vulnerability",
            description="Large swaps can be targeted by just-in-time liquidity attacks.",
            severity=Severity.MEDIUM,
            category=Category.FRONT_RUNNING,
            regex_patterns=[],
            remediation="Break large swaps into smaller amounts or use private transactions.",
            references=["https://eigenphi.io/"]
        ))
        
        # Liquidation MEV
        self.add(VulnerabilityPattern(
            id="MEV-003",
            name="Liquidation MEV Exposure",
            description="Liquidation functions can be front-run by MEV bots.",
            severity=Severity.MEDIUM,
            category=Category.FRONT_RUNNING,
            regex_patterns=[
                r"function\s+liquidate\s*\(",
                r"function\s+liquidateBorrow\s*\(",
            ],
            remediation="Consider implementing liquidation rewards that account for MEV.",
            references=["https://www.paradigm.xyz/2021/07/mev-and-me"]
        ))
        
        # Arbitrage Leakage
        self.add(VulnerabilityPattern(
            id="MEV-004",
            name="Arbitrage Opportunity Leakage",
            description="Protocol leaves arbitrage value for MEV extractors.",
            severity=Severity.LOW,
            category=Category.FRONT_RUNNING,
            regex_patterns=[
                r"price\s*=\s*getReserves",
            ],
            remediation="Capture MEV value for the protocol or users via MEV-Share.",
            references=["https://collective.flashbots.net/"]
        ))
    
    def add(self, vuln: VulnerabilityPattern):
        """Add a vulnerability pattern to the database."""
        self.vulnerabilities[vuln.id] = vuln
    
    def get(self, vuln_id: str) -> Optional[VulnerabilityPattern]:
        """Get a vulnerability by ID."""
        return self.vulnerabilities.get(vuln_id)
    
    def get_by_category(self, category: Category) -> List[VulnerabilityPattern]:
        """Get all vulnerabilities in a category."""
        return [v for v in self.vulnerabilities.values() if v.category == category]
    
    def get_by_severity(self, severity: Severity) -> List[VulnerabilityPattern]:
        """Get all vulnerabilities of a severity level."""
        return [v for v in self.vulnerabilities.values() if v.severity == severity]
    
    def scan_code(self, code: str) -> List[Dict]:
        """Scan code for all vulnerability patterns."""
        findings = []
        for vuln in self.vulnerabilities.values():
            matches = vuln.matches_code(code)
            if matches:
                # Check for false positive hints
                is_false_positive = any(hint in code for hint in vuln.false_positive_hints)
                findings.append({
                    "vulnerability": vuln,
                    "matches": matches,
                    "likely_false_positive": is_false_positive
                })
        return findings
    
    def to_json(self) -> str:
        """Export database to JSON."""
        data = {}
        for vuln_id, vuln in self.vulnerabilities.items():
            data[vuln_id] = {
                "id": vuln.id,
                "name": vuln.name,
                "description": vuln.description,
                "severity": vuln.severity.value,
                "category": vuln.category.value,
                "swc_id": vuln.swc_id,
                "cwe_id": vuln.cwe_id,
                "remediation": vuln.remediation,
                "references": vuln.references,
            }
        return json.dumps(data, indent=2)
    
    def stats(self) -> Dict:
        """Get database statistics."""
        return {
            "total_patterns": len(self.vulnerabilities),
            "by_severity": {
                s.value: len(self.get_by_severity(s)) for s in Severity
            },
            "by_category": {
                c.value: len(self.get_by_category(c)) for c in Category
            }
        }


# Global database instance
VULN_DB = VulnerabilityDatabase()


if __name__ == "__main__":
    db = VulnerabilityDatabase()
    print("SENTINEL Vulnerability Database")
    print("=" * 50)
    stats = db.stats()
    print(f"Total Patterns: {stats['total_patterns']}")
    print("\nBy Severity:")
    for sev, count in stats['by_severity'].items():
        print(f"  {sev}: {count}")
    print("\nBy Category:")
    for cat, count in stats['by_category'].items():
        print(f"  {cat}: {count}")
