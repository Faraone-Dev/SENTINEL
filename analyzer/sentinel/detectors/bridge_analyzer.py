"""
╔═══════════════════════════════════════════════════════════════════════════╗
║           SENTINEL SHIELD - CROSS-CHAIN BRIDGE ANALYZER                   ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Detect Bridge Vulnerabilities: Ronin, Wormhole, Nomad Pattern Analysis   ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any, Set
from datetime import datetime


class BridgeType(Enum):
    """Types of cross-chain bridges."""
    LOCK_MINT = "Lock-and-Mint"
    BURN_MINT = "Burn-and-Mint"
    LIQUIDITY_POOL = "Liquidity Pool"
    HASH_TIME_LOCK = "Hash Time-Locked Contract (HTLC)"
    OPTIMISTIC = "Optimistic Bridge"
    ZK_ROLLUP = "ZK-Rollup Bridge"
    SIDECHAIN = "Sidechain Bridge"
    UNKNOWN = "Unknown Bridge Type"


class BridgeRisk(Enum):
    """Risk levels for bridge vulnerabilities."""
    CRITICAL = "critical"  # Can lead to total fund loss
    HIGH = "high"          # Can lead to significant fund loss
    MEDIUM = "medium"      # Can lead to temporary issues
    LOW = "low"            # Minor issues
    INFO = "info"          # Informational


@dataclass
class BridgeFinding:
    """A bridge-related security finding."""
    id: str
    title: str
    risk: BridgeRisk
    description: str
    recommendation: str
    attack_vector: str
    historical_exploit: Optional[str] = None
    affected_code: str = ""
    estimated_impact: str = ""


@dataclass
class BridgeComponent:
    """A detected bridge component."""
    name: str
    component_type: str  # validator, relayer, oracle, vault, router
    functions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)


class CrossChainBridgeAnalyzer:
    """
    Analyzes cross-chain bridge implementations for vulnerabilities.
    
    Based on analysis of major bridge exploits:
    - Ronin Bridge: $625M (validator key compromise)
    - Wormhole: $320M (signature verification bypass)
    - Nomad: $190M (merkle root validation bypass)
    - Harmony Horizon: $100M (multi-sig compromise)
    - Multichain: $130M (admin key compromise)
    - Poly Network: $611M (access control bypass)
    """
    
    # Historical exploits database
    HISTORICAL_EXPLOITS = {
        "ronin": {
            "name": "Ronin Bridge Hack",
            "date": "March 2022",
            "loss": "$625M",
            "cause": "Validator key compromise (5/9 multisig)",
            "pattern": "Centralized validator set with insufficient key security",
        },
        "wormhole": {
            "name": "Wormhole Hack",
            "date": "February 2022",
            "loss": "$320M",
            "cause": "Signature verification bypass",
            "pattern": "Missing guardian set verification in VAA validation",
        },
        "nomad": {
            "name": "Nomad Bridge Hack",
            "date": "August 2022",
            "loss": "$190M",
            "cause": "Invalid merkle root accepted as valid",
            "pattern": "Initialization bug allowing zero bytes32 as valid root",
        },
        "harmony": {
            "name": "Harmony Horizon Hack",
            "date": "June 2022",
            "loss": "$100M",
            "cause": "Multi-sig key compromise (2/5)",
            "pattern": "Low threshold multi-sig with poor key management",
        },
        "polynetwork": {
            "name": "Poly Network Hack",
            "date": "August 2021",
            "loss": "$611M",
            "cause": "Access control bypass via cross-chain message",
            "pattern": "Keeper role could be changed via cross-chain call",
        },
        "multichain": {
            "name": "Multichain Exploit",
            "date": "July 2023",
            "loss": "$130M",
            "cause": "Admin/MPC key compromise",
            "pattern": "Centralized key management for bridge assets",
        },
    }
    
    # Vulnerability patterns
    VULNERABILITY_PATTERNS = {
        # Signature/Verification Issues
        "missing_sig_verify": {
            "pattern": re.compile(
                r"function\s+\w*(relay|execute|claim|process)\w*\s*\([^)]*\)[^{]*\{(?![^}]*(?:verify|ecrecover|ECDSA))",
                re.IGNORECASE | re.DOTALL
            ),
            "risk": BridgeRisk.CRITICAL,
            "title": "Missing Signature Verification",
            "description": "Bridge message processing without signature verification",
            "attack_vector": "Attacker can forge cross-chain messages",
            "historical": "wormhole",
        },
        
        # Merkle Proof Issues
        "weak_merkle": {
            "pattern": re.compile(
                r"(merkleRoot|root)\s*==\s*(bytes32\(0\)|0x0{64})",
                re.IGNORECASE
            ),
            "risk": BridgeRisk.CRITICAL,
            "title": "Weak Merkle Root Validation",
            "description": "Merkle root validation accepts zero/empty values",
            "attack_vector": "Attacker can submit transactions with zero proof",
            "historical": "nomad",
        },
        
        # Multi-sig Issues
        "low_threshold": {
            "pattern": re.compile(
                r"threshold\s*[=<]\s*[12]\s*(?:;|\)|,)",
                re.IGNORECASE
            ),
            "risk": BridgeRisk.HIGH,
            "title": "Low Multi-Sig Threshold",
            "description": "Multi-sig threshold is too low (1-2 signers)",
            "attack_vector": "Compromising 1-2 keys gives full control",
            "historical": "harmony",
        },
        
        # Access Control Issues
        "unprotected_admin": {
            "pattern": re.compile(
                r"function\s+(set\w*|update\w*|change\w*)\s*\([^)]*\)\s+(?:external|public)(?![^{]*(?:onlyOwner|onlyAdmin|require\s*\(\s*msg\.sender))",
                re.IGNORECASE
            ),
            "risk": BridgeRisk.CRITICAL,
            "title": "Unprotected Admin Functions",
            "description": "Administrative functions lack access control",
            "attack_vector": "Anyone can modify bridge configuration",
            "historical": "polynetwork",
        },
        
        # Replay Attack Vulnerabilities
        "missing_nonce": {
            "pattern": re.compile(
                r"function\s+\w*(relay|claim|execute)\w*\s*\([^)]*\)(?![^{]*(?:nonce|used\[|processed\[|claimed\[))",
                re.IGNORECASE | re.DOTALL
            ),
            "risk": BridgeRisk.HIGH,
            "title": "Missing Replay Protection",
            "description": "No nonce or transaction tracking for replay prevention",
            "attack_vector": "Same message can be replayed multiple times",
        },
        
        # Oracle Manipulation
        "centralized_oracle": {
            "pattern": re.compile(
                r"(?:oracle|reporter|relayer)\s*=\s*(?:msg\.sender|_\w+|address)",
                re.IGNORECASE
            ),
            "risk": BridgeRisk.MEDIUM,
            "title": "Centralized Oracle/Relayer",
            "description": "Bridge relies on single oracle or relayer",
            "attack_vector": "Oracle compromise leads to false messages",
        },
        
        # Insufficient Validation
        "missing_chain_id": {
            "pattern": re.compile(
                r"function\s+\w*process\w*\s*\([^)]*\)(?![^{]*chainId)",
                re.IGNORECASE | re.DOTALL
            ),
            "risk": BridgeRisk.HIGH,
            "title": "Missing Chain ID Validation",
            "description": "Cross-chain message doesn't validate source/dest chain",
            "attack_vector": "Message from wrong chain could be processed",
        },
        
        # Reentrancy in Bridge
        "bridge_reentrancy": {
            "pattern": re.compile(
                r"(\.call\{value:|\.transfer\(|\.send\().*\n(?:.*\n){0,5}.*(?:balances?\[|amount)",
                re.IGNORECASE
            ),
            "risk": BridgeRisk.HIGH,
            "title": "Potential Bridge Reentrancy",
            "description": "ETH/token transfer before state update in bridge",
            "attack_vector": "Reentrant call can drain bridge funds",
        },
        
        # Initialization Issues
        "uninitialized_bridge": {
            "pattern": re.compile(
                r"(?:validator|guardian|keeper)s?\s*\.\s*length\s*==\s*0",
                re.IGNORECASE
            ),
            "risk": BridgeRisk.CRITICAL,
            "title": "Bridge Operating Without Validators",
            "description": "Bridge can operate with empty validator set",
            "attack_vector": "Attacker can add themselves as sole validator",
        },
        
        # Wrapped Token Issues
        "uncapped_mint": {
            "pattern": re.compile(
                r"function\s+mint\s*\([^)]*\)\s+(?:external|public)(?![^{]*(?:require|assert|revert))",
                re.IGNORECASE
            ),
            "risk": BridgeRisk.CRITICAL,
            "title": "Uncapped Token Minting",
            "description": "Bridge can mint wrapped tokens without limit",
            "attack_vector": "Infinite mint attack on wrapped asset",
        },
    }
    
    # Bridge component patterns
    COMPONENT_PATTERNS = {
        "vault": re.compile(r"(vault|treasury|escrow|lock)", re.IGNORECASE),
        "validator": re.compile(r"(validator|guardian|keeper|signer)", re.IGNORECASE),
        "relayer": re.compile(r"(relayer|messenger|executor|bridge)", re.IGNORECASE),
        "oracle": re.compile(r"(oracle|priceF|datafeed)", re.IGNORECASE),
        "router": re.compile(r"(router|gateway|portal)", re.IGNORECASE),
        "token": re.compile(r"(wrapped|bridged|synth)", re.IGNORECASE),
    }
    
    def __init__(self):
        self.findings: List[BridgeFinding] = []
        self.components: List[BridgeComponent] = []
        self.bridge_type: BridgeType = BridgeType.UNKNOWN
    
    def analyze(self, code: str, filename: str = "Bridge.sol") -> Dict[str, Any]:
        """
        Analyze bridge contract for vulnerabilities.
        
        Args:
            code: Solidity source code
            filename: Source filename
            
        Returns:
            Analysis results
        """
        self.findings = []
        self.components = []
        
        # Detect bridge type
        self.bridge_type = self._detect_bridge_type(code)
        
        # Detect components
        self._detect_components(code)
        
        # Run vulnerability checks
        self._check_all_patterns(code)
        self._check_validator_security(code)
        self._check_message_handling(code)
        self._check_token_security(code)
        self._check_timelock(code)
        self._check_emergency_controls(code)
        
        return {
            "filename": filename,
            "bridge_type": self.bridge_type.value,
            "components": [self._component_to_dict(c) for c in self.components],
            "findings": [self._finding_to_dict(f) for f in self.findings],
            "summary": self._generate_summary(),
            "risk_score": self._calculate_risk_score(),
            "recommendations": self._generate_recommendations(),
        }
    
    def _detect_bridge_type(self, code: str) -> BridgeType:
        """Detect the type of bridge implementation."""
        patterns = {
            BridgeType.LOCK_MINT: [r"lock.*mint", r"deposit.*wrap", r"lock\s*\(.*\).*mint\s*\("],
            BridgeType.BURN_MINT: [r"burn.*mint", r"burn\s*\(.*\).*mint\s*\("],
            BridgeType.LIQUIDITY_POOL: [r"addLiquidity", r"removeLiquidity", r"swap.*pool"],
            BridgeType.HASH_TIME_LOCK: [r"hashlock", r"timelock", r"HTLC", r"secretHash"],
            BridgeType.OPTIMISTIC: [r"fraud.*proof", r"challenge.*period", r"dispute"],
            BridgeType.ZK_ROLLUP: [r"zkProof", r"verifyProof", r"snark", r"plonk"],
        }
        
        for bridge_type, type_patterns in patterns.items():
            for pattern in type_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    return bridge_type
        
        return BridgeType.UNKNOWN
    
    def _detect_components(self, code: str):
        """Detect bridge components."""
        # Extract contract names
        contract_pattern = re.compile(r"contract\s+(\w+)")
        contracts = contract_pattern.findall(code)
        
        for contract in contracts:
            for comp_type, pattern in self.COMPONENT_PATTERNS.items():
                if pattern.search(contract):
                    # Find functions in this contract
                    func_pattern = re.compile(
                        rf"contract\s+{contract}[^{{]*\{{([^}}]+)\}}",
                        re.DOTALL
                    )
                    match = func_pattern.search(code)
                    functions = []
                    if match:
                        func_defs = re.findall(r"function\s+(\w+)", match.group(1))
                        functions = func_defs
                    
                    self.components.append(BridgeComponent(
                        name=contract,
                        component_type=comp_type,
                        functions=functions,
                    ))
                    break
    
    def _check_all_patterns(self, code: str):
        """Check all vulnerability patterns."""
        for vuln_id, vuln_info in self.VULNERABILITY_PATTERNS.items():
            matches = vuln_info["pattern"].findall(code)
            if matches:
                historical = None
                if "historical" in vuln_info:
                    historical = self.HISTORICAL_EXPLOITS.get(vuln_info["historical"])
                
                self.findings.append(BridgeFinding(
                    id=f"BRIDGE-{len(self.findings)+1:03d}",
                    title=vuln_info["title"],
                    risk=vuln_info["risk"],
                    description=vuln_info["description"],
                    recommendation=self._get_recommendation(vuln_id),
                    attack_vector=vuln_info["attack_vector"],
                    historical_exploit=historical["name"] if historical else None,
                    affected_code=str(matches[0])[:200] if matches else "",
                ))
    
    def _check_validator_security(self, code: str):
        """Check validator/guardian security."""
        # Check for hardcoded validators
        if re.search(r"validators?\s*=\s*\[.*0x[a-fA-F0-9]{40}", code):
            self.findings.append(BridgeFinding(
                id=f"BRIDGE-{len(self.findings)+1:03d}",
                title="Hardcoded Validator Addresses",
                risk=BridgeRisk.MEDIUM,
                description="Validator addresses are hardcoded in contract",
                recommendation="Implement upgradeable validator set with proper governance",
                attack_vector="Validator rotation requires contract upgrade",
            ))
        
        # Check validator rotation
        if not re.search(r"(addValidator|removeValidator|updateValidator)", code, re.IGNORECASE):
            self.findings.append(BridgeFinding(
                id=f"BRIDGE-{len(self.findings)+1:03d}",
                title="No Validator Rotation Mechanism",
                risk=BridgeRisk.MEDIUM,
                description="No mechanism to add/remove validators",
                recommendation="Implement secure validator rotation with timelock",
                attack_vector="Compromised validator cannot be removed",
            ))
        
        # Check validator count
        threshold_match = re.search(r"(?:threshold|required|minValidators)\s*=\s*(\d+)", code)
        total_match = re.search(r"(?:totalValidators|validatorCount|numValidators)\s*=\s*(\d+)", code)
        
        if threshold_match and total_match:
            threshold = int(threshold_match.group(1))
            total = int(total_match.group(1))
            
            if threshold < total * 2 // 3:
                self.findings.append(BridgeFinding(
                    id=f"BRIDGE-{len(self.findings)+1:03d}",
                    title="Insufficient Validator Threshold",
                    risk=BridgeRisk.HIGH,
                    description=f"Threshold {threshold}/{total} is below 2/3 Byzantine tolerance",
                    recommendation="Set threshold to at least 2/3 of validators",
                    attack_vector="Attacker needs to compromise fewer validators",
                    historical_exploit="Ronin Bridge Hack",
                ))
    
    def _check_message_handling(self, code: str):
        """Check cross-chain message security."""
        # Check message expiry
        if not re.search(r"(expiry|deadline|timeout|validUntil)", code, re.IGNORECASE):
            self.findings.append(BridgeFinding(
                id=f"BRIDGE-{len(self.findings)+1:03d}",
                title="Missing Message Expiry",
                risk=BridgeRisk.MEDIUM,
                description="Cross-chain messages have no expiration time",
                recommendation="Add message expiry/deadline for time-bounded validity",
                attack_vector="Old messages can be replayed indefinitely",
            ))
        
        # Check for double-spending prevention
        if not re.search(r"(processed|claimed|executed|used)\s*\[", code, re.IGNORECASE):
            self.findings.append(BridgeFinding(
                id=f"BRIDGE-{len(self.findings)+1:03d}",
                title="Missing Transaction Tracking",
                risk=BridgeRisk.CRITICAL,
                description="No mapping to track processed transactions",
                recommendation="Track processed transaction hashes/nonces in mapping",
                attack_vector="Same transaction can be claimed multiple times",
            ))
    
    def _check_token_security(self, code: str):
        """Check wrapped token security."""
        # Check for supply tracking
        if re.search(r"function\s+mint", code, re.IGNORECASE):
            if not re.search(r"(totalLocked|lockedSupply|backingAmount)", code, re.IGNORECASE):
                self.findings.append(BridgeFinding(
                    id=f"BRIDGE-{len(self.findings)+1:03d}",
                    title="No Backing Asset Tracking",
                    risk=BridgeRisk.HIGH,
                    description="Minted tokens don't track locked collateral",
                    recommendation="Track locked assets and ensure 1:1 backing",
                    attack_vector="Can mint unbacked tokens",
                ))
        
        # Check for burn verification
        if re.search(r"burn", code, re.IGNORECASE):
            if not re.search(r"burn.*require", code, re.IGNORECASE):
                self.findings.append(BridgeFinding(
                    id=f"BRIDGE-{len(self.findings)+1:03d}",
                    title="Unvalidated Token Burn",
                    risk=BridgeRisk.MEDIUM,
                    description="Token burn lacks sufficient validation",
                    recommendation="Verify burn amount, sender, and emit proper events",
                    attack_vector="Invalid burns could unlock incorrect amounts",
                ))
    
    def _check_timelock(self, code: str):
        """Check for timelock on critical operations."""
        critical_ops = ["upgrade", "setValidator", "setThreshold", "pause", "withdraw"]
        
        for op in critical_ops:
            if re.search(rf"function\s+{op}", code, re.IGNORECASE):
                if not re.search(r"(timelock|delay|queue.*execute)", code, re.IGNORECASE):
                    self.findings.append(BridgeFinding(
                        id=f"BRIDGE-{len(self.findings)+1:03d}",
                        title="Critical Operations Without Timelock",
                        risk=BridgeRisk.MEDIUM,
                        description=f"Function `{op}` has no timelock delay",
                        recommendation="Add timelock for critical admin operations",
                        attack_vector="Compromised admin can make instant changes",
                    ))
                    break
    
    def _check_emergency_controls(self, code: str):
        """Check emergency control mechanisms."""
        # Check for pause mechanism
        if not re.search(r"(pause|unpause|Pausable)", code, re.IGNORECASE):
            self.findings.append(BridgeFinding(
                id=f"BRIDGE-{len(self.findings)+1:03d}",
                title="Missing Emergency Pause",
                risk=BridgeRisk.MEDIUM,
                description="Bridge has no emergency pause mechanism",
                recommendation="Implement Pausable pattern for emergency stops",
                attack_vector="Cannot stop ongoing attack",
            ))
        
        # Check for emergency withdrawal
        if not re.search(r"(emergencyWithdraw|rescueFunds|recoverToken)", code, re.IGNORECASE):
            self.findings.append(BridgeFinding(
                id=f"BRIDGE-{len(self.findings)+1:03d}",
                title="Missing Fund Recovery Mechanism",
                risk=BridgeRisk.LOW,
                description="No emergency fund recovery function",
                recommendation="Add timelocked emergency withdrawal (with proper access control)",
                attack_vector="Stuck funds cannot be recovered",
            ))
    
    def _get_recommendation(self, vuln_id: str) -> str:
        """Get recommendation for vulnerability type."""
        recommendations = {
            "missing_sig_verify": "Implement robust signature verification using ECDSA.recover or similar",
            "weak_merkle": "Validate merkle root is non-zero and properly initialized",
            "low_threshold": "Increase threshold to at least 2/3 of total signers",
            "unprotected_admin": "Add onlyOwner/onlyAdmin modifier to administrative functions",
            "missing_nonce": "Track processed messages with nonce or transaction hash mapping",
            "centralized_oracle": "Use decentralized oracle network or multi-oracle setup",
            "missing_chain_id": "Validate source and destination chain IDs in message",
            "bridge_reentrancy": "Follow checks-effects-interactions pattern or use ReentrancyGuard",
            "uninitialized_bridge": "Require minimum validator count before processing",
            "uncapped_mint": "Implement minting limits and validation",
        }
        return recommendations.get(vuln_id, "Review and fix the identified vulnerability")
    
    def _component_to_dict(self, component: BridgeComponent) -> Dict[str, Any]:
        """Convert component to dictionary."""
        return {
            "name": component.name,
            "type": component.component_type,
            "functions": component.functions,
            "risks": component.risks,
        }
    
    def _finding_to_dict(self, finding: BridgeFinding) -> Dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            "id": finding.id,
            "title": finding.title,
            "risk": finding.risk.value,
            "description": finding.description,
            "recommendation": finding.recommendation,
            "attack_vector": finding.attack_vector,
            "historical_exploit": finding.historical_exploit,
            "affected_code": finding.affected_code,
            "estimated_impact": finding.estimated_impact,
        }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate analysis summary."""
        risk_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        
        for finding in self.findings:
            risk_counts[finding.risk.value] += 1
        
        return {
            "total_findings": len(self.findings),
            "by_risk": risk_counts,
            "bridge_type_detected": self.bridge_type != BridgeType.UNKNOWN,
            "components_detected": len(self.components),
        }
    
    def _calculate_risk_score(self) -> int:
        """Calculate overall risk score (0-100)."""
        weights = {
            BridgeRisk.CRITICAL: 30,
            BridgeRisk.HIGH: 18,
            BridgeRisk.MEDIUM: 8,
            BridgeRisk.LOW: 3,
            BridgeRisk.INFO: 1,
        }
        
        score = sum(weights.get(f.risk, 0) for f in self.findings)
        return min(100, score)
    
    def _generate_recommendations(self) -> List[str]:
        """Generate overall security recommendations."""
        recs = []
        
        if self.bridge_type == BridgeType.UNKNOWN:
            recs.append("Clarify bridge architecture and document cross-chain flow")
        
        if any(f.historical_exploit for f in self.findings):
            recs.append("Review historical bridge exploits and implement lessons learned")
        
        summary = self._generate_summary()
        if summary["by_risk"]["critical"] > 0:
            recs.append("URGENT: Address critical vulnerabilities before deployment")
        
        recs.extend([
            "Implement defense-in-depth with multiple validation layers",
            "Use battle-tested libraries (OpenZeppelin, LayerZero, Axelar)",
            "Get professional security audit from firms like Trail of Bits or OpenZeppelin",
            "Set up monitoring and alerting for unusual bridge activity",
            "Implement progressive rate limiting for large transfers",
        ])
        
        return recs
    
    def generate_report(self) -> str:
        """Generate human-readable report."""
        report = "# Cross-Chain Bridge Security Analysis\n\n"
        
        # Bridge Info
        report += "## Bridge Information\n\n"
        report += f"- **Type**: {self.bridge_type.value}\n"
        report += f"- **Components Detected**: {len(self.components)}\n\n"
        
        if self.components:
            report += "### Components\n\n"
            for comp in self.components:
                report += f"- **{comp.name}** ({comp.component_type})\n"
            report += "\n"
        
        # Historical Context
        report += "## Historical Bridge Exploits Reference\n\n"
        report += "| Bridge | Loss | Year | Cause |\n"
        report += "|--------|------|------|-------|\n"
        for exploit in self.HISTORICAL_EXPLOITS.values():
            report += f"| {exploit['name']} | {exploit['loss']} | {exploit['date']} | {exploit['cause'][:50]}... |\n"
        report += "\n"
        
        # Summary
        summary = self._generate_summary()
        report += "## Vulnerability Summary\n\n"
        report += f"| Risk Level | Count |\n|------------|-------|\n"
        for risk, count in summary["by_risk"].items():
            if count > 0:
                report += f"| {risk.capitalize()} | {count} |\n"
        report += f"\n**Risk Score**: {self._calculate_risk_score()}/100\n\n"
        
        # Findings
        if self.findings:
            report += "## Detailed Findings\n\n"
            
            for finding in sorted(self.findings, key=lambda x: list(BridgeRisk).index(x.risk)):
                emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "ℹ️"}
                report += f"### {emoji.get(finding.risk.value, '•')} [{finding.id}] {finding.title}\n\n"
                report += f"**Risk**: {finding.risk.value.upper()}\n\n"
                report += f"**Description**: {finding.description}\n\n"
                report += f"**Attack Vector**: {finding.attack_vector}\n\n"
                
                if finding.historical_exploit:
                    report += f"**Similar to**: {finding.historical_exploit}\n\n"
                
                report += f"**Recommendation**: {finding.recommendation}\n\n"
                
                if finding.affected_code:
                    report += f"```solidity\n{finding.affected_code}\n```\n\n"
                
                report += "---\n\n"
        else:
            report += "## ✅ No Critical Issues Detected\n\n"
        
        # Recommendations
        report += "## Security Recommendations\n\n"
        for i, rec in enumerate(self._generate_recommendations(), 1):
            report += f"{i}. {rec}\n"
        
        return report


# Example vulnerable bridge for testing
VULNERABLE_BRIDGE_EXAMPLE = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnerableBridge {
    mapping(address => uint256) public balances;
    address public validator;  // Single validator - centralized!
    uint256 public threshold = 1;  // Low threshold
    
    // VULN: No signature verification
    function relay(address to, uint256 amount, bytes memory message) external {
        // Missing signature check!
        balances[to] += amount;
    }
    
    // VULN: No replay protection
    function claim(bytes32 txHash, address to, uint256 amount) external {
        // No check if already claimed!
        payable(to).transfer(amount);
    }
    
    // VULN: Unprotected admin function
    function setValidator(address _validator) external {
        validator = _validator;
    }
    
    // VULN: Uncapped minting
    function mint(address to, uint256 amount) public {
        balances[to] += amount;
    }
}
"""

if __name__ == "__main__":
    print("SENTINEL Cross-Chain Bridge Analyzer")
    print("=" * 50)
    
    analyzer = CrossChainBridgeAnalyzer()
    results = analyzer.analyze(VULNERABLE_BRIDGE_EXAMPLE)
    
    print(f"\n🌉 Bridge Type: {results['bridge_type']}")
    print(f"🔍 Findings: {results['summary']['total_findings']}")
    print(f"⚠️  Risk Score: {results['risk_score']}/100")
    
    print("\n" + analyzer.generate_report())
