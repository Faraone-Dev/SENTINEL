"""
╔═══════════════════════════════════════════════════════════════════════════╗
║           SENTINEL SHIELD - SLITHER INTEGRATION                           ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Professional Static Analysis via Slither by Trail of Bits               ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import subprocess
import json
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Any
import tempfile
import os


class SlitherDetectorType(Enum):
    """Slither detector categories."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"
    OPTIMIZATION = "optimization"


@dataclass
class SlitherFinding:
    """A finding from Slither analysis."""
    detector: str
    check: str
    severity: str
    confidence: str
    description: str
    first_markdown_element: str
    elements: List[Dict] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SlitherFinding":
        """Create from Slither JSON output."""
        return cls(
            detector=data.get("check", "unknown"),
            check=data.get("check", "unknown"),
            severity=data.get("impact", "unknown"),
            confidence=data.get("confidence", "unknown"),
            description=data.get("description", ""),
            first_markdown_element=data.get("first_markdown_element", ""),
            elements=data.get("elements", []),
        )


class SlitherIntegration:
    """
    Integration with Slither - the Solidity static analyzer by Trail of Bits.
    
    Slither is the industry-standard static analysis tool used by:
    - Trail of Bits
    - OpenZeppelin
    - Consensys Diligence
    - Major DeFi protocols
    """
    
    # Detector categories and their descriptions
    DETECTORS = {
        # High severity
        "reentrancy-eth": ("Reentrancy vulnerabilities with ETH transfer", "high"),
        "reentrancy-no-eth": ("Reentrancy vulnerabilities without ETH", "medium"),
        "arbitrary-send-eth": ("Arbitrary ETH send", "high"),
        "controlled-delegatecall": ("Delegatecall to user-controlled address", "high"),
        "selfdestruct": ("Unprotected selfdestruct", "high"),
        "suicidal": ("Functions allowing self-destruct by anyone", "high"),
        "unprotected-upgrade": ("Unprotected upgradeable contract", "high"),
        
        # Medium severity
        "divide-before-multiply": ("Divide before multiply precision loss", "medium"),
        "incorrect-equality": ("Dangerous strict equality", "medium"),
        "locked-ether": ("Contracts that lock Ether", "medium"),
        "missing-zero-check": ("Missing zero-address validation", "medium"),
        "reentrancy-events": ("Reentrancy with event misorder", "medium"),
        "tx-origin": ("Dangerous usage of tx.origin", "medium"),
        "unchecked-transfer": ("Unchecked ERC20 transfer", "medium"),
        "uninitialized-local": ("Uninitialized local variables", "medium"),
        "unused-return": ("Unused return values", "medium"),
        
        # Low severity  
        "assembly": ("Assembly usage", "informational"),
        "boolean-equal": ("Boolean equality comparison", "low"),
        "calls-loop": ("External calls in loop", "low"),
        "costly-loop": ("Costly loop operations", "low"),
        "dead-code": ("Unused code", "informational"),
        "low-level-calls": ("Low level calls", "informational"),
        "naming-convention": ("Naming convention violations", "informational"),
        "pragma": ("Different pragma versions", "informational"),
        "redundant-statements": ("Redundant statements", "informational"),
        "solc-version": ("Incorrect Solidity version", "informational"),
        "timestamp": ("Block timestamp manipulation", "low"),
        "too-many-digits": ("Too many digits", "informational"),
        "unimplemented-functions": ("Unimplemented functions", "informational"),
        "unused-state": ("Unused state variables", "informational"),
        "variable-scope": ("Variable scope issues", "low"),
    }
    
    def __init__(self, slither_path: str = "slither"):
        """
        Initialize Slither integration.
        
        Args:
            slither_path: Path to slither executable
        """
        self.slither_path = slither_path
        self._verify_installation()
    
    def _verify_installation(self) -> bool:
        """Verify Slither is installed and accessible."""
        if shutil.which(self.slither_path):
            return True
        
        # Try common installation paths
        common_paths = [
            os.path.expanduser("~/.local/bin/slither"),
            "/usr/local/bin/slither",
            "/usr/bin/slither",
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                self.slither_path = path
                return True
        
        return False
    
    @staticmethod
    def install() -> bool:
        """Install Slither via pip."""
        try:
            subprocess.run(
                ["pip", "install", "slither-analyzer"],
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    def analyze(
        self,
        target: str,
        detectors: Optional[List[str]] = None,
        exclude_detectors: Optional[List[str]] = None,
        exclude_dependencies: bool = True,
        exclude_optimization: bool = False,
        compile_args: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run Slither analysis on target.
        
        Args:
            target: Path to contract file, directory, or project
            detectors: Specific detectors to run (None = all)
            exclude_detectors: Detectors to exclude
            exclude_dependencies: Exclude node_modules/dependencies
            exclude_optimization: Exclude optimization detectors
            compile_args: Additional compilation arguments
            
        Returns:
            Analysis results dictionary
        """
        cmd = [self.slither_path, target, "--json", "-"]
        
        if detectors:
            cmd.extend(["--detect", ",".join(detectors)])
        
        if exclude_detectors:
            cmd.extend(["--exclude", ",".join(exclude_detectors)])
        
        if exclude_dependencies:
            cmd.append("--exclude-dependencies")
        
        if exclude_optimization:
            cmd.extend(["--exclude", "optimization"])
        
        if compile_args:
            cmd.extend(compile_args)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Slither outputs JSON to stdout
            if result.stdout:
                return json.loads(result.stdout)
            
            # Check stderr for errors
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr,
                    "findings": []
                }
            
            return {"success": True, "findings": []}
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Analysis timed out after 5 minutes",
                "findings": []
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Failed to parse Slither output: {e}",
                "findings": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "findings": []
            }
    
    def analyze_contract(self, contract_code: str, filename: str = "Contract.sol") -> Dict[str, Any]:
        """
        Analyze a contract from source code string.
        
        Args:
            contract_code: Solidity source code
            filename: Virtual filename for the contract
            
        Returns:
            Analysis results
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            contract_path = Path(tmpdir) / filename
            contract_path.write_text(contract_code)
            return self.analyze(str(contract_path))
    
    def parse_findings(self, results: Dict[str, Any]) -> List[SlitherFinding]:
        """Parse Slither output into Finding objects."""
        findings = []
        
        for detector_result in results.get("results", {}).get("detectors", []):
            finding = SlitherFinding.from_dict(detector_result)
            findings.append(finding)
        
        return findings
    
    def get_severity_summary(self, findings: List[SlitherFinding]) -> Dict[str, int]:
        """Get summary of findings by severity."""
        summary = {"high": 0, "medium": 0, "low": 0, "informational": 0, "optimization": 0}
        
        for finding in findings:
            severity = finding.severity.lower()
            if severity in summary:
                summary[severity] += 1
        
        return summary
    
    def generate_report(self, findings: List[SlitherFinding]) -> str:
        """Generate human-readable report from findings."""
        if not findings:
            return "✅ No issues detected by Slither!"
        
        report = "# Slither Analysis Report\n\n"
        
        # Summary
        summary = self.get_severity_summary(findings)
        report += "## Summary\n\n"
        report += f"| Severity | Count |\n|----------|-------|\n"
        for severity, count in summary.items():
            if count > 0:
                report += f"| {severity.capitalize()} | {count} |\n"
        report += "\n"
        
        # Group by severity
        severity_order = ["high", "medium", "low", "informational", "optimization"]
        
        for severity in severity_order:
            severity_findings = [f for f in findings if f.severity.lower() == severity]
            if not severity_findings:
                continue
            
            report += f"## {severity.capitalize()} Severity\n\n"
            
            for finding in severity_findings:
                report += f"### {finding.detector}\n\n"
                report += f"**Confidence**: {finding.confidence}\n\n"
                report += f"{finding.description}\n\n"
                
                if finding.first_markdown_element:
                    report += f"**Location**: `{finding.first_markdown_element}`\n\n"
                
                report += "---\n\n"
        
        return report
    
    def quick_scan(self, target: str) -> Dict[str, Any]:
        """
        Run a quick security scan with most important detectors.
        
        Args:
            target: Path to analyze
            
        Returns:
            Scan results
        """
        critical_detectors = [
            "reentrancy-eth",
            "reentrancy-no-eth",
            "arbitrary-send-eth",
            "controlled-delegatecall",
            "selfdestruct",
            "suicidal",
            "unprotected-upgrade",
            "tx-origin",
            "unchecked-transfer",
        ]
        
        return self.analyze(target, detectors=critical_detectors)
    
    def full_audit_scan(self, target: str) -> Dict[str, Any]:
        """
        Run comprehensive audit scan with all detectors.
        
        Args:
            target: Path to analyze
            
        Returns:
            Complete scan results
        """
        return self.analyze(
            target,
            exclude_dependencies=True,
            exclude_optimization=False
        )


class SlitherPrinter:
    """
    Run Slither printers for contract analysis.
    Printers provide information about the contract structure.
    """
    
    PRINTERS = {
        "contract-summary": "Print a summary of the contracts",
        "function-summary": "Print a summary of the functions",
        "inheritance": "Print the inheritance graph",
        "inheritance-graph": "Output inheritance graph in DOT format",
        "call-graph": "Output the call graph in DOT format",
        "cfg": "Output the control flow graph of each function",
        "vars-and-auth": "Print state variables and authorization",
        "data-dependency": "Print data dependency of the variables",
        "modifiers": "Print modifiers for each function",
        "require": "Print require statements per function",
        "human-summary": "Print human-readable summary",
    }
    
    def __init__(self, slither_path: str = "slither"):
        self.slither_path = slither_path
    
    def run_printer(self, target: str, printer: str) -> str:
        """
        Run a Slither printer on target.
        
        Args:
            target: Path to analyze
            printer: Printer name from PRINTERS
            
        Returns:
            Printer output
        """
        if printer not in self.PRINTERS:
            raise ValueError(f"Unknown printer: {printer}. Available: {list(self.PRINTERS.keys())}")
        
        cmd = [self.slither_path, target, "--print", printer]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return result.stdout or result.stderr
        except Exception as e:
            return f"Error running printer: {e}"
    
    def get_contract_summary(self, target: str) -> str:
        """Get contract summary."""
        return self.run_printer(target, "contract-summary")
    
    def get_inheritance_graph(self, target: str) -> str:
        """Get inheritance graph in DOT format."""
        return self.run_printer(target, "inheritance-graph")
    
    def get_call_graph(self, target: str) -> str:
        """Get call graph in DOT format."""
        return self.run_printer(target, "call-graph")


class CombinedAnalyzer:
    """
    Combines Slither with SENTINEL's custom analysis.
    """
    
    def __init__(self):
        self.slither = SlitherIntegration()
    
    def full_analysis(self, target: str) -> Dict[str, Any]:
        """
        Run combined Slither + SENTINEL analysis.
        
        Args:
            target: Path to analyze
            
        Returns:
            Combined results from all tools
        """
        results = {
            "slither": None,
            "sentinel": None,
            "combined_findings": [],
            "risk_score": 0,
        }
        
        # Run Slither
        slither_results = self.slither.full_audit_scan(target)
        slither_findings = self.slither.parse_findings(slither_results)
        results["slither"] = {
            "findings": [f.__dict__ for f in slither_findings],
            "summary": self.slither.get_severity_summary(slither_findings)
        }
        
        # Run SENTINEL custom patterns
        from sentinel.vulnerabilities.database import VulnerabilityDatabase
        vuln_db = VulnerabilityDatabase()
        
        # Read contract code
        contract_path = Path(target)
        if contract_path.is_file():
            code = contract_path.read_text()
            sentinel_findings = vuln_db.scan_code(code)
            results["sentinel"] = {
                "findings": [
                    {
                        "id": f["vulnerability"].id,
                        "name": f["vulnerability"].name,
                        "severity": f["vulnerability"].severity.value,
                        "matches": f["matches"],
                        "likely_false_positive": f["likely_false_positive"]
                    }
                    for f in sentinel_findings
                ]
            }
        
        # Calculate combined risk score
        slither_score = (
            results["slither"]["summary"]["high"] * 10 +
            results["slither"]["summary"]["medium"] * 5 +
            results["slither"]["summary"]["low"] * 2
        )
        
        results["risk_score"] = min(100, slither_score)
        
        return results


if __name__ == "__main__":
    print("SENTINEL Slither Integration")
    print("=" * 50)
    
    slither = SlitherIntegration()
    
    if not slither._verify_installation():
        print("⚠️  Slither not found. Install with: pip install slither-analyzer")
    else:
        print("✅ Slither is installed and ready")
        print(f"   Path: {slither.slither_path}")
    
    print(f"\n📋 Available Detectors: {len(SlitherIntegration.DETECTORS)}")
    print(f"📊 Available Printers: {len(SlitherPrinter.PRINTERS)}")
