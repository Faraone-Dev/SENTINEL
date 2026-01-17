"""
╔═══════════════════════════════════════════════════════════════════════════╗
║           SENTINEL SHIELD - PROXY SAFETY CHECKER                          ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Analyze Upgradeable Proxy Patterns for Security Vulnerabilities          ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path


class ProxyType(Enum):
    """Types of proxy patterns."""
    TRANSPARENT = "TransparentUpgradeableProxy"
    UUPS = "UUPSUpgradeable"
    BEACON = "BeaconProxy"
    MINIMAL = "EIP-1167 Minimal Proxy"
    DIAMOND = "EIP-2535 Diamond"
    METAMORPHIC = "Metamorphic Contract"
    UNKNOWN = "Unknown Proxy Type"


class UpgradeRisk(Enum):
    """Risk levels for upgrade vulnerabilities."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ProxyFinding:
    """A proxy-related security finding."""
    id: str
    title: str
    risk: UpgradeRisk
    description: str
    recommendation: str
    affected_code: str = ""
    line_number: int = 0
    

@dataclass
class StorageSlot:
    """Represents a storage slot."""
    slot: str  # Hex slot number
    name: str
    type: str
    contract: str
    line_number: int = 0


@dataclass 
class ProxyInfo:
    """Information about a detected proxy."""
    proxy_type: ProxyType
    implementation_slot: Optional[str]
    admin_slot: Optional[str]
    beacon_slot: Optional[str]
    has_initializer: bool
    has_reinitializer: bool
    upgrade_mechanism: str
    storage_layout: List[StorageSlot] = field(default_factory=list)


class ProxySafetyChecker:
    """
    Analyzes upgradeable proxy patterns for security issues.
    
    Checks for:
    - Storage collision vulnerabilities
    - Uninitialized proxy/implementation
    - Missing upgrade authorization
    - Function selector clashing
    - Delegatecall vulnerabilities
    - Missing initializer protection
    - Storage gaps
    """
    
    # Standard EIP-1967 storage slots
    STANDARD_SLOTS = {
        "implementation": "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc",
        "admin": "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103",
        "beacon": "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50",
        "rollback": "0x4910fdfa16fed3260ed0e7147f7cc6da11a60208b5b9406d12a635614ffd9143",
    }
    
    # Storage gap patterns
    STORAGE_GAP_PATTERN = re.compile(
        r"uint256\[\s*(\d+)\s*\]\s+(?:private|internal)?\s*__gap",
        re.IGNORECASE
    )
    
    # Proxy detection patterns
    PROXY_PATTERNS = {
        ProxyType.TRANSPARENT: [
            r"TransparentUpgradeableProxy",
            r"import.*TransparentUpgradeableProxy",
            r"_IMPLEMENTATION_SLOT",
            r"_ADMIN_SLOT",
        ],
        ProxyType.UUPS: [
            r"UUPSUpgradeable",
            r"_authorizeUpgrade",
            r"proxiableUUID",
            r"import.*UUPSUpgradeable",
        ],
        ProxyType.BEACON: [
            r"BeaconProxy",
            r"IBeacon",
            r"_BEACON_SLOT",
            r"import.*BeaconProxy",
        ],
        ProxyType.MINIMAL: [
            r"clone\s*\(",
            r"0x3d602d80600a3d3981f3363d3d373d3d3d363d73",
            r"EIP-1167",
            r"LibClone",
        ],
        ProxyType.DIAMOND: [
            r"DiamondCut",
            r"IDiamondCut",
            r"facetAddress",
            r"LibDiamond",
            r"DiamondLoupe",
        ],
        ProxyType.METAMORPHIC: [
            r"CREATE2",
            r"selfdestruct",
            r"0x5860208158601c335a63",  # Metamorphic bytecode
        ],
    }
    
    # Initializer patterns
    INITIALIZER_PATTERNS = {
        "oz_initializer": re.compile(r"initializer\s+modifier"),
        "oz_initializer_func": re.compile(r"function\s+\w+\s*\([^)]*\)[^{]*\binitializer\b"),
        "oz_reinitializer": re.compile(r"reinitializer\s*\(\s*\d+\s*\)"),
        "custom_init": re.compile(r"function\s+init(?:ialize)?\s*\("),
        "constructor_disable": re.compile(r"_disableInitializers\s*\(\s*\)"),
    }
    
    # Dangerous patterns
    DANGEROUS_PATTERNS = {
        "unprotected_upgrade": re.compile(
            r"function\s+upgrade\w*\s*\([^)]*\)\s+(?:external|public)(?![^{]*onlyOwner|[^{]*onlyRole|[^{]*require)",
            re.IGNORECASE
        ),
        "delegatecall_to_user": re.compile(
            r"\.delegatecall\s*\(\s*(?:msg\.data|_data|data|abi\.encode)",
        ),
        "selfdestruct": re.compile(r"selfdestruct\s*\("),
        "missing_auth_upgrade": re.compile(
            r"function\s+_authorizeUpgrade\s*\([^)]*\)\s+internal\s+(?:virtual\s+)?override\s*\{\s*\}",
        ),
        "storage_in_proxy": re.compile(
            r"contract\s+\w*Proxy\w*[^{]*\{[^}]*(?:uint256|address|bool|mapping|bytes)\s+(?:public|private|internal)",
            re.DOTALL
        ),
    }
    
    def __init__(self):
        self.findings: List[ProxyFinding] = []
        self.proxy_info: Optional[ProxyInfo] = None
    
    def analyze(self, code: str, filename: str = "Contract.sol") -> Dict[str, Any]:
        """
        Analyze contract code for proxy-related vulnerabilities.
        
        Args:
            code: Solidity source code
            filename: Source filename for reporting
            
        Returns:
            Analysis results
        """
        self.findings = []
        
        # Detect proxy type
        self.proxy_info = self._detect_proxy_type(code)
        
        # Run all checks
        self._check_initializer_protection(code)
        self._check_storage_collision(code)
        self._check_upgrade_authorization(code)
        self._check_function_clashing(code)
        self._check_storage_gaps(code)
        self._check_dangerous_patterns(code)
        self._check_constructor_usage(code)
        self._check_immutable_variables(code)
        self._check_selfdestruct(code)
        
        # Compile results
        return {
            "filename": filename,
            "proxy_type": self.proxy_info.proxy_type.value if self.proxy_info else "none",
            "proxy_info": self._proxy_info_to_dict(),
            "findings": [self._finding_to_dict(f) for f in self.findings],
            "summary": self._generate_summary(),
            "risk_score": self._calculate_risk_score(),
        }
    
    def _detect_proxy_type(self, code: str) -> ProxyInfo:
        """Detect the proxy pattern used."""
        detected_type = ProxyType.UNKNOWN
        
        for proxy_type, patterns in self.PROXY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, code):
                    detected_type = proxy_type
                    break
            if detected_type != ProxyType.UNKNOWN:
                break
        
        # Extract slots
        impl_slot = self._find_slot(code, "implementation")
        admin_slot = self._find_slot(code, "admin")
        beacon_slot = self._find_slot(code, "beacon")
        
        # Check initializers
        has_init = bool(self.INITIALIZER_PATTERNS["oz_initializer_func"].search(code))
        has_reinit = bool(self.INITIALIZER_PATTERNS["oz_reinitializer"].search(code))
        
        # Determine upgrade mechanism
        if detected_type == ProxyType.UUPS:
            upgrade_mech = "UUPS (implementation-side)"
        elif detected_type == ProxyType.TRANSPARENT:
            upgrade_mech = "Transparent (admin-side)"
        elif detected_type == ProxyType.BEACON:
            upgrade_mech = "Beacon (beacon contract)"
        elif detected_type == ProxyType.DIAMOND:
            upgrade_mech = "Diamond (facet cuts)"
        else:
            upgrade_mech = "Unknown"
        
        return ProxyInfo(
            proxy_type=detected_type,
            implementation_slot=impl_slot,
            admin_slot=admin_slot,
            beacon_slot=beacon_slot,
            has_initializer=has_init,
            has_reinitializer=has_reinit,
            upgrade_mechanism=upgrade_mech,
        )
    
    def _find_slot(self, code: str, slot_type: str) -> Optional[str]:
        """Find a storage slot in the code."""
        standard = self.STANDARD_SLOTS.get(slot_type)
        if standard and standard in code:
            return standard
        
        # Look for custom slot definitions
        slot_pattern = re.compile(
            rf"bytes32.*{slot_type}.*=.*0x([a-fA-F0-9]{{64}})",
            re.IGNORECASE
        )
        match = slot_pattern.search(code)
        if match:
            return f"0x{match.group(1)}"
        
        return None
    
    def _check_initializer_protection(self, code: str):
        """Check for proper initializer protection."""
        # Check for constructor that disables initializers
        has_disable = bool(self.INITIALIZER_PATTERNS["constructor_disable"].search(code))
        
        # Check for initializer modifier
        has_init_modifier = bool(self.INITIALIZER_PATTERNS["oz_initializer"].search(code))
        init_funcs = self.INITIALIZER_PATTERNS["custom_init"].findall(code)
        
        if init_funcs and not has_init_modifier:
            self.findings.append(ProxyFinding(
                id="PROXY-001",
                title="Initializer Missing Protection",
                risk=UpgradeRisk.CRITICAL,
                description="Initialize function found without `initializer` modifier. "
                           "This can allow re-initialization attacks.",
                recommendation="Add OpenZeppelin's `initializer` modifier to prevent re-initialization.",
                affected_code=init_funcs[0] if init_funcs else "",
            ))
        
        if not has_disable and self.proxy_info and self.proxy_info.proxy_type in [
            ProxyType.UUPS, ProxyType.TRANSPARENT
        ]:
            self.findings.append(ProxyFinding(
                id="PROXY-002",
                title="Missing _disableInitializers in Constructor",
                risk=UpgradeRisk.HIGH,
                description="Implementation contract should call _disableInitializers() in constructor "
                           "to prevent initialization of the implementation contract itself.",
                recommendation="Add `constructor() { _disableInitializers(); }` to implementation.",
            ))
    
    def _check_storage_collision(self, code: str):
        """Check for potential storage collision issues."""
        # Count state variables
        state_var_pattern = re.compile(
            r"^\s*(uint\d*|int\d*|address|bool|bytes\d*|string|mapping)[^;]*;",
            re.MULTILINE
        )
        state_vars = state_var_pattern.findall(code)
        
        # Check for inheritance without gaps
        inheritance_pattern = re.compile(r"contract\s+\w+\s+is\s+([\w\s,]+)\s*\{")
        inheritance_match = inheritance_pattern.search(code)
        
        if inheritance_match:
            parents = [p.strip() for p in inheritance_match.group(1).split(",")]
            if len(parents) > 1 and not self.STORAGE_GAP_PATTERN.search(code):
                self.findings.append(ProxyFinding(
                    id="PROXY-003",
                    title="Missing Storage Gap in Upgradeable Contract",
                    risk=UpgradeRisk.MEDIUM,
                    description=f"Contract inherits from {len(parents)} contracts but no storage gap found. "
                               "Adding state variables to parent contracts in future upgrades will cause storage collision.",
                    recommendation="Add `uint256[50] private __gap;` at the end of each upgradeable base contract.",
                ))
        
        # Check for slot collision with EIP-1967
        for slot_name, slot_value in self.STANDARD_SLOTS.items():
            if slot_value in code:
                # Verify it's using the correct calculation
                if f'keccak256("eip1967.proxy.{slot_name}")' not in code.lower():
                    # Custom slot - verify it's derived correctly
                    pass
    
    def _check_upgrade_authorization(self, code: str):
        """Check upgrade authorization controls."""
        # Check for unprotected upgrade
        if self.DANGEROUS_PATTERNS["unprotected_upgrade"].search(code):
            self.findings.append(ProxyFinding(
                id="PROXY-004",
                title="Unprotected Upgrade Function",
                risk=UpgradeRisk.CRITICAL,
                description="Upgrade function lacks access control. Anyone can upgrade the implementation.",
                recommendation="Add `onlyOwner`, `onlyRole`, or similar access control to upgrade functions.",
            ))
        
        # Check for empty _authorizeUpgrade
        if self.DANGEROUS_PATTERNS["missing_auth_upgrade"].search(code):
            self.findings.append(ProxyFinding(
                id="PROXY-005",
                title="Empty _authorizeUpgrade Function",
                risk=UpgradeRisk.CRITICAL,
                description="The _authorizeUpgrade function is empty, allowing anyone to upgrade.",
                recommendation="Implement proper access control in _authorizeUpgrade.",
            ))
        
        # Check for missing Ownable/AccessControl
        if self.proxy_info and self.proxy_info.proxy_type == ProxyType.UUPS:
            if not re.search(r"(OwnableUpgradeable|AccessControlUpgradeable|onlyOwner|onlyRole)", code):
                self.findings.append(ProxyFinding(
                    id="PROXY-006",
                    title="UUPS Without Access Control",
                    risk=UpgradeRisk.HIGH,
                    description="UUPS proxy implementation without standard access control pattern.",
                    recommendation="Inherit from OwnableUpgradeable or AccessControlUpgradeable.",
                ))
    
    def _check_function_clashing(self, code: str):
        """Check for function selector clashing."""
        # Extract function signatures
        func_pattern = re.compile(r"function\s+(\w+)\s*\(([^)]*)\)")
        functions = func_pattern.findall(code)
        
        # Calculate selectors
        from hashlib import sha3_256
        try:
            from Crypto.Hash import keccak
            
            def get_selector(name: str, params: str) -> str:
                sig = f"{name}({params})"
                k = keccak.new(digest_bits=256)
                k.update(sig.encode())
                return k.hexdigest()[:8]
        except ImportError:
            # Fallback without selector calculation
            return
        
        selectors: Dict[str, str] = {}
        for name, params in functions:
            # Normalize params
            param_types = ",".join([p.split()[0] for p in params.split(",") if p.strip()])
            selector = get_selector(name, param_types)
            
            if selector in selectors:
                self.findings.append(ProxyFinding(
                    id="PROXY-007",
                    title="Function Selector Collision",
                    risk=UpgradeRisk.HIGH,
                    description=f"Functions `{selectors[selector]}` and `{name}` have the same selector.",
                    recommendation="Rename one of the functions to avoid selector collision.",
                ))
            else:
                selectors[selector] = name
    
    def _check_storage_gaps(self, code: str):
        """Check storage gap implementation."""
        gaps = self.STORAGE_GAP_PATTERN.findall(code)
        
        if gaps:
            for gap_size in gaps:
                if int(gap_size) < 50:
                    self.findings.append(ProxyFinding(
                        id="PROXY-008",
                        title="Insufficient Storage Gap Size",
                        risk=UpgradeRisk.LOW,
                        description=f"Storage gap of {gap_size} slots found. "
                                   "Standard practice is 50 slots for future-proofing.",
                        recommendation="Consider using `uint256[50] private __gap;` for more flexibility.",
                    ))
    
    def _check_dangerous_patterns(self, code: str):
        """Check for dangerous patterns in proxy context."""
        # Delegatecall to user input
        if self.DANGEROUS_PATTERNS["delegatecall_to_user"].search(code):
            self.findings.append(ProxyFinding(
                id="PROXY-009",
                title="Delegatecall with User Input",
                risk=UpgradeRisk.CRITICAL,
                description="Delegatecall with user-controlled data detected. "
                           "This can lead to arbitrary code execution in proxy context.",
                recommendation="Avoid delegatecall with user input or implement strict validation.",
            ))
        
        # Storage declared in proxy
        if self.DANGEROUS_PATTERNS["storage_in_proxy"].search(code):
            self.findings.append(ProxyFinding(
                id="PROXY-010",
                title="State Variables in Proxy Contract",
                risk=UpgradeRisk.HIGH,
                description="State variables declared directly in proxy contract. "
                           "This can cause storage collision with implementation.",
                recommendation="Use EIP-1967 slots for proxy-specific storage.",
            ))
    
    def _check_constructor_usage(self, code: str):
        """Check for constructor in upgradeable contract."""
        constructor_pattern = re.compile(r"constructor\s*\([^)]*\)\s*\{[^}]+\}")
        initializable_pattern = re.compile(r"Initializable|initializer")
        
        has_constructor = bool(constructor_pattern.search(code))
        is_initializable = bool(initializable_pattern.search(code))
        
        if has_constructor and is_initializable:
            # Check if constructor does anything besides _disableInitializers
            constructor_match = constructor_pattern.search(code)
            if constructor_match:
                constructor_body = constructor_match.group(0)
                if "_disableInitializers" not in constructor_body:
                    self.findings.append(ProxyFinding(
                        id="PROXY-011",
                        title="Constructor with Logic in Upgradeable Contract",
                        risk=UpgradeRisk.HIGH,
                        description="Constructor contains logic in an upgradeable contract. "
                                   "Constructor logic won't run for proxy deployments.",
                        recommendation="Move constructor logic to initializer function.",
                        affected_code=constructor_body[:200],
                    ))
    
    def _check_immutable_variables(self, code: str):
        """Check for immutable variables in upgradeable context."""
        immutable_pattern = re.compile(r"(\w+)\s+(?:public\s+)?immutable\s+(\w+)")
        immutables = immutable_pattern.findall(code)
        
        if immutables and self.proxy_info and self.proxy_info.proxy_type in [
            ProxyType.UUPS, ProxyType.TRANSPARENT, ProxyType.BEACON
        ]:
            self.findings.append(ProxyFinding(
                id="PROXY-012",
                title="Immutable Variables in Upgradeable Contract",
                risk=UpgradeRisk.INFO,
                description=f"Found {len(immutables)} immutable variable(s) in upgradeable contract. "
                           "Immutable values are stored in bytecode and may differ between implementations.",
                recommendation="Ensure immutable values are consistent across upgrades or use storage.",
            ))
    
    def _check_selfdestruct(self, code: str):
        """Check for selfdestruct in upgradeable context."""
        if self.DANGEROUS_PATTERNS["selfdestruct"].search(code):
            self.findings.append(ProxyFinding(
                id="PROXY-013",
                title="Selfdestruct in Upgradeable Contract",
                risk=UpgradeRisk.CRITICAL,
                description="Selfdestruct found in upgradeable contract. "
                           "This can permanently brick the proxy by destroying implementation.",
                recommendation="Remove selfdestruct from implementation contracts.",
            ))
    
    def _proxy_info_to_dict(self) -> Dict[str, Any]:
        """Convert proxy info to dictionary."""
        if not self.proxy_info:
            return {}
        
        return {
            "proxy_type": self.proxy_info.proxy_type.value,
            "implementation_slot": self.proxy_info.implementation_slot,
            "admin_slot": self.proxy_info.admin_slot,
            "beacon_slot": self.proxy_info.beacon_slot,
            "has_initializer": self.proxy_info.has_initializer,
            "has_reinitializer": self.proxy_info.has_reinitializer,
            "upgrade_mechanism": self.proxy_info.upgrade_mechanism,
        }
    
    def _finding_to_dict(self, finding: ProxyFinding) -> Dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            "id": finding.id,
            "title": finding.title,
            "risk": finding.risk.value,
            "description": finding.description,
            "recommendation": finding.recommendation,
            "affected_code": finding.affected_code,
            "line_number": finding.line_number,
        }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate analysis summary."""
        risk_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        
        for finding in self.findings:
            risk_counts[finding.risk.value] += 1
        
        return {
            "total_findings": len(self.findings),
            "by_risk": risk_counts,
            "proxy_detected": self.proxy_info.proxy_type != ProxyType.UNKNOWN if self.proxy_info else False,
        }
    
    def _calculate_risk_score(self) -> int:
        """Calculate overall risk score (0-100)."""
        weights = {
            UpgradeRisk.CRITICAL: 25,
            UpgradeRisk.HIGH: 15,
            UpgradeRisk.MEDIUM: 8,
            UpgradeRisk.LOW: 3,
            UpgradeRisk.INFO: 1,
        }
        
        score = sum(weights.get(f.risk, 0) for f in self.findings)
        return min(100, score)
    
    def generate_report(self) -> str:
        """Generate human-readable report."""
        if not self.findings:
            return "✅ No proxy-related vulnerabilities detected!"
        
        report = "# Proxy Safety Analysis Report\n\n"
        
        # Proxy info
        if self.proxy_info:
            report += "## Proxy Information\n\n"
            report += f"- **Type**: {self.proxy_info.proxy_type.value}\n"
            report += f"- **Upgrade Mechanism**: {self.proxy_info.upgrade_mechanism}\n"
            report += f"- **Has Initializer**: {'Yes' if self.proxy_info.has_initializer else 'No'}\n"
            report += f"- **Has Reinitializer**: {'Yes' if self.proxy_info.has_reinitializer else 'No'}\n\n"
        
        # Summary
        summary = self._generate_summary()
        report += "## Summary\n\n"
        report += f"| Risk Level | Count |\n|------------|-------|\n"
        for risk, count in summary["by_risk"].items():
            if count > 0:
                report += f"| {risk.capitalize()} | {count} |\n"
        report += f"\n**Risk Score**: {self._calculate_risk_score()}/100\n\n"
        
        # Findings
        report += "## Findings\n\n"
        
        for finding in sorted(self.findings, key=lambda x: list(UpgradeRisk).index(x.risk)):
            emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "ℹ️"}
            report += f"### {emoji.get(finding.risk.value, '•')} [{finding.id}] {finding.title}\n\n"
            report += f"**Risk**: {finding.risk.value.upper()}\n\n"
            report += f"**Description**: {finding.description}\n\n"
            report += f"**Recommendation**: {finding.recommendation}\n\n"
            
            if finding.affected_code:
                report += f"```solidity\n{finding.affected_code}\n```\n\n"
            
            report += "---\n\n"
        
        return report


# Example vulnerable contracts for testing
VULNERABLE_UUPS_EXAMPLE = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";

contract VulnerableUUPS is UUPSUpgradeable {
    uint256 public value;
    
    // VULN: No _disableInitializers in constructor
    
    function initialize(uint256 _value) external {
        // VULN: Missing initializer modifier
        value = _value;
    }
    
    function _authorizeUpgrade(address newImplementation) internal override {
        // VULN: Empty authorization - anyone can upgrade!
    }
    
    function destroy() external {
        // VULN: Selfdestruct in upgradeable contract
        selfdestruct(payable(msg.sender));
    }
}
"""

if __name__ == "__main__":
    print("SENTINEL Proxy Safety Checker")
    print("=" * 50)
    
    checker = ProxySafetyChecker()
    results = checker.analyze(VULNERABLE_UUPS_EXAMPLE)
    
    print(f"\n📋 Proxy Type: {results['proxy_type']}")
    print(f"🔍 Findings: {results['summary']['total_findings']}")
    print(f"⚠️  Risk Score: {results['risk_score']}/100")
    
    print("\n" + checker.generate_report())
