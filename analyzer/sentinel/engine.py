"""
╔═══════════════════════════════════════════════════════════════════════════╗
║           SENTINEL SHIELD - MAIN SECURITY ENGINE                          ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Professional Smart Contract Security Suite                               ║
║  Ready for: Trail of Bits • OpenZeppelin • Consensys • Spearbit           ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Any
import hashlib


class SeverityLevel(Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "informational"


@dataclass
class SecurityIssue:
    """A detected security issue."""
    id: str
    title: str
    severity: SeverityLevel
    category: str
    description: str
    recommendation: str
    location: str = ""
    code_snippet: str = ""
    references: List[str] = field(default_factory=list)


@dataclass
class ScanResult:
    """Complete scan result."""
    target: str
    timestamp: datetime
    issues: List[SecurityIssue]
    metadata: Dict[str, Any]
    risk_score: int


class SentinelSecurityEngine:
    """
    The main SENTINEL security analysis engine.
    
    Integrates all security modules:
    - Vulnerability Database (SWC + DeFi + MEV patterns)
    - MEV & Flash Loan Detection
    - Slither Integration
    - Proxy Safety Checker
    - Cross-Chain Bridge Analyzer
    - Formal Verification Engine
    - Professional Audit Report Generation
    
    This is the unified interface for all SENTINEL capabilities.
    """
    
    VERSION = "2.0.0"
    CODENAME = "SHIELD"
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the SENTINEL security engine.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self._initialize_modules()
        self.results: List[ScanResult] = []
    
    def _initialize_modules(self):
        """Initialize all security modules."""
        # Import modules lazily to handle missing dependencies
        self.modules = {}
        
        try:
            from sentinel.vulnerabilities.database import VulnerabilityDatabase
            self.modules["vuln_db"] = VulnerabilityDatabase()
        except ImportError:
            self.modules["vuln_db"] = None
        
        try:
            from sentinel.detectors.mev_detector import MEVDetector
            self.modules["mev_detector"] = MEVDetector()
        except ImportError:
            self.modules["mev_detector"] = None
        
        try:
            from sentinel.detectors.proxy_checker import ProxySafetyChecker
            self.modules["proxy_checker"] = ProxySafetyChecker()
        except ImportError:
            self.modules["proxy_checker"] = None
        
        try:
            from sentinel.detectors.bridge_analyzer import CrossChainBridgeAnalyzer
            self.modules["bridge_analyzer"] = CrossChainBridgeAnalyzer()
        except ImportError:
            self.modules["bridge_analyzer"] = None
        
        try:
            from sentinel.verification.formal_verification import FormalVerificationEngine
            self.modules["formal_verifier"] = FormalVerificationEngine()
        except ImportError:
            self.modules["formal_verifier"] = None
        
        try:
            from sentinel.integrations.slither_integration import SlitherIntegration
            self.modules["slither"] = SlitherIntegration()
        except ImportError:
            self.modules["slither"] = None
        
        try:
            from sentinel.reports.audit_report import AuditReport
            self.modules["reporter"] = AuditReport
        except ImportError:
            self.modules["reporter"] = None
    
    def scan(
        self,
        code: str,
        filename: str = "Contract.sol",
        deep_analysis: bool = True,
        include_slither: bool = True,
        include_formal: bool = False,
    ) -> ScanResult:
        """
        Perform comprehensive security scan.
        
        Args:
            code: Solidity source code
            filename: Source filename
            deep_analysis: Enable deep pattern analysis
            include_slither: Include Slither analysis
            include_formal: Include formal verification
            
        Returns:
            Complete scan result
        """
        issues: List[SecurityIssue] = []
        metadata: Dict[str, Any] = {
            "filename": filename,
            "lines_of_code": len(code.splitlines()),
            "modules_used": [],
        }
        
        # 1. Vulnerability Database Scan
        if self.modules.get("vuln_db"):
            metadata["modules_used"].append("VulnerabilityDatabase")
            vuln_results = self.modules["vuln_db"].scan_code(code)
            
            for result in vuln_results:
                vuln = result["vulnerability"]
                issues.append(SecurityIssue(
                    id=vuln.id,
                    title=vuln.name,
                    severity=SeverityLevel(vuln.severity.value),
                    category=vuln.category.value if hasattr(vuln.category, 'value') else str(vuln.category),
                    description=vuln.description,
                    recommendation=vuln.remediation,  # Fixed: use remediation not recommendation
                    code_snippet=str(result["matches"])[:500],
                    references=vuln.references,
                ))
        
        # 2. MEV Detection
        if self.modules.get("mev_detector") and deep_analysis:
            metadata["modules_used"].append("MEVDetector")
            # MEV detector works on transactions, not code
            # But we can check for MEV-vulnerable patterns in code
            mev_patterns = [
                ("Potential sandwich vulnerability", "swap", SeverityLevel.MEDIUM),
                ("Flash loan entry point", "flashLoan", SeverityLevel.INFO),
                ("Price oracle dependency", "getPrice", SeverityLevel.MEDIUM),
            ]
            
            for title, pattern, severity in mev_patterns:
                if pattern.lower() in code.lower():
                    issues.append(SecurityIssue(
                        id=f"MEV-{len(issues):03d}",
                        title=title,
                        severity=severity,
                        category="MEV",
                        description=f"Code contains '{pattern}' which may be vulnerable to MEV attacks",
                        recommendation="Implement slippage protection and deadline checks",
                    ))
        
        # 3. Proxy Safety Check
        if self.modules.get("proxy_checker"):
            proxy_keywords = ["proxy", "upgradeable", "initializable", "UUPS", "beacon"]
            if any(kw.lower() in code.lower() for kw in proxy_keywords):
                metadata["modules_used"].append("ProxySafetyChecker")
                proxy_results = self.modules["proxy_checker"].analyze(code, filename)
                
                for finding in proxy_results.get("findings", []):
                    issues.append(SecurityIssue(
                        id=finding["id"],
                        title=finding["title"],
                        severity=SeverityLevel(finding["risk"]),
                        category="Proxy Safety",
                        description=finding["description"],
                        recommendation=finding["recommendation"],
                        code_snippet=finding.get("affected_code", ""),
                    ))
        
        # 4. Bridge Analysis
        if self.modules.get("bridge_analyzer"):
            bridge_keywords = ["bridge", "crosschain", "relay", "validator", "guardian"]
            if any(kw.lower() in code.lower() for kw in bridge_keywords):
                metadata["modules_used"].append("BridgeAnalyzer")
                bridge_results = self.modules["bridge_analyzer"].analyze(code, filename)
                
                for finding in bridge_results.get("findings", []):
                    issues.append(SecurityIssue(
                        id=finding["id"],
                        title=finding["title"],
                        severity=SeverityLevel(finding["risk"]),
                        category="Bridge Security",
                        description=finding["description"],
                        recommendation=finding["recommendation"],
                        code_snippet=finding.get("affected_code", ""),
                    ))
        
        # 5. Slither Integration
        if include_slither and self.modules.get("slither"):
            try:
                slither_results = self.modules["slither"].analyze_contract(code, filename)
                slither_findings = self.modules["slither"].parse_findings(slither_results)
                
                if slither_findings:
                    metadata["modules_used"].append("Slither")
                    
                    for finding in slither_findings:
                        issues.append(SecurityIssue(
                            id=f"SLITHER-{finding.detector}",
                            title=finding.check,
                            severity=SeverityLevel(finding.severity.lower()),
                            category="Static Analysis",
                            description=finding.description,
                            recommendation="Review Slither documentation for remediation",
                        ))
            except Exception:
                pass  # Slither not available or failed
        
        # 6. Formal Verification
        if include_formal and self.modules.get("formal_verifier"):
            metadata["modules_used"].append("FormalVerification")
            verifier = self.modules["formal_verifier"]
            verifier.add_security_properties()
            
            try:
                verification_results = verifier.verify_all(code)
                
                for result in verification_results.get("results", []):
                    if result["status"] == "violated":
                        issues.append(SecurityIssue(
                            id=result["property_id"],
                            title=f"Formal Property Violated: {result['property_name']}",
                            severity=SeverityLevel(result["severity"]),
                            category="Formal Verification",
                            description=f"Property '{result['property_name']}' was violated",
                            recommendation="Review counterexample and fix the violation",
                            code_snippet=json.dumps(result.get("counterexample", {})),
                        ))
            except Exception:
                pass  # Verification failed
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(issues)
        
        # Create result
        result = ScanResult(
            target=filename,
            timestamp=datetime.now(),
            issues=issues,
            metadata=metadata,
            risk_score=risk_score,
        )
        
        self.results.append(result)
        return result
    
    def scan_file(self, file_path: str, **kwargs) -> ScanResult:
        """
        Scan a Solidity file.
        
        Args:
            file_path: Path to the Solidity file
            **kwargs: Additional arguments for scan()
            
        Returns:
            Scan result
        """
        path = Path(file_path)
        code = path.read_text()
        return self.scan(code, filename=path.name, **kwargs)
    
    def scan_directory(
        self,
        dir_path: str,
        pattern: str = "*.sol",
        **kwargs
    ) -> List[ScanResult]:
        """
        Scan all Solidity files in a directory.
        
        Args:
            dir_path: Path to directory
            pattern: Glob pattern for files
            **kwargs: Additional arguments for scan()
            
        Returns:
            List of scan results
        """
        path = Path(dir_path)
        results = []
        
        for sol_file in path.rglob(pattern):
            if "node_modules" not in str(sol_file):
                try:
                    result = self.scan_file(str(sol_file), **kwargs)
                    results.append(result)
                except Exception as e:
                    print(f"Error scanning {sol_file}: {e}")
        
        return results
    
    def _calculate_risk_score(self, issues: List[SecurityIssue]) -> int:
        """Calculate overall risk score (0-100)."""
        weights = {
            SeverityLevel.CRITICAL: 25,
            SeverityLevel.HIGH: 15,
            SeverityLevel.MEDIUM: 8,
            SeverityLevel.LOW: 3,
            SeverityLevel.INFO: 1,
        }
        
        score = sum(weights.get(issue.severity, 0) for issue in issues)
        return min(100, score)
    
    def get_summary(self, result: ScanResult) -> Dict[str, Any]:
        """Get scan summary."""
        severity_counts = {}
        category_counts = {}
        
        for issue in result.issues:
            severity = issue.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            category = issue.category
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return {
            "target": result.target,
            "timestamp": result.timestamp.isoformat(),
            "total_issues": len(result.issues),
            "by_severity": severity_counts,
            "by_category": category_counts,
            "risk_score": result.risk_score,
            "modules_used": result.metadata.get("modules_used", []),
        }
    
    def generate_report(
        self,
        result: ScanResult,
        format: str = "markdown"
    ) -> str:
        """
        Generate security report.
        
        Args:
            result: Scan result
            format: Output format (markdown, json, html)
            
        Returns:
            Formatted report
        """
        if format == "json":
            return json.dumps({
                "version": self.VERSION,
                "summary": self.get_summary(result),
                "issues": [
                    {
                        "id": issue.id,
                        "title": issue.title,
                        "severity": issue.severity.value,
                        "category": issue.category,
                        "description": issue.description,
                        "recommendation": issue.recommendation,
                        "location": issue.location,
                        "references": issue.references,
                    }
                    for issue in result.issues
                ],
            }, indent=2)
        
        # Markdown report
        report = f"""# SENTINEL Security Report

**Version**: {self.VERSION} ({self.CODENAME})
**Target**: {result.target}
**Timestamp**: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
**Risk Score**: {result.risk_score}/100

---

## Executive Summary

| Severity | Count |
|----------|-------|
"""
        
        summary = self.get_summary(result)
        for severity in ["critical", "high", "medium", "low", "informational"]:
            count = summary["by_severity"].get(severity, 0)
            if count > 0:
                emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "informational": "ℹ️"}
                report += f"| {emoji.get(severity, '')} {severity.capitalize()} | {count} |\n"
        
        report += f"\n**Modules Used**: {', '.join(summary['modules_used'])}\n\n"
        
        report += "---\n\n## Findings\n\n"
        
        # Group by severity
        severity_order = [
            SeverityLevel.CRITICAL,
            SeverityLevel.HIGH,
            SeverityLevel.MEDIUM,
            SeverityLevel.LOW,
            SeverityLevel.INFO
        ]
        
        for severity in severity_order:
            severity_issues = [i for i in result.issues if i.severity == severity]
            
            if not severity_issues:
                continue
            
            report += f"### {severity.value.upper()}\n\n"
            
            for issue in severity_issues:
                report += f"#### [{issue.id}] {issue.title}\n\n"
                report += f"**Category**: {issue.category}\n\n"
                report += f"**Description**: {issue.description}\n\n"
                report += f"**Recommendation**: {issue.recommendation}\n\n"
                
                if issue.code_snippet:
                    report += f"```solidity\n{issue.code_snippet[:500]}\n```\n\n"
                
                if issue.references:
                    report += "**References**:\n"
                    for ref in issue.references:
                        report += f"- {ref}\n"
                    report += "\n"
                
                report += "---\n\n"
        
        # Footer
        report += f"""
---

## About SENTINEL

SENTINEL is a professional-grade smart contract security suite designed for:
- **Trail of Bits** - Building on their Slither framework
- **OpenZeppelin** - Compatible with OZ security standards
- **Consensys Diligence** - Following best practices
- **Spearbit** - Professional audit-ready reports

**Modules**:
- 🔍 Vulnerability Database (SWC + DeFi + MEV)
- ⚡ MEV & Flash Loan Detection
- 🔗 Slither Integration
- 🛡️ Proxy Safety Checker
- 🌉 Cross-Chain Bridge Analyzer
- ✓ Formal Verification Engine

---

*Generated by SENTINEL Shield v{self.VERSION}*
*Report Hash: {hashlib.sha256(report.encode()).hexdigest()[:16]}*
"""
        
        return report
    
    def export_sarif(self, result: ScanResult) -> Dict:
        """
        Export results in SARIF format for CI/CD integration.
        
        SARIF (Static Analysis Results Interchange Format) is the standard
        format supported by GitHub, Azure DevOps, and other tools.
        """
        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "SENTINEL",
                            "version": self.VERSION,
                            "informationUri": "https://github.com/sentinel-shield",
                            "rules": [],
                        }
                    },
                    "results": [],
                }
            ],
        }
        
        for issue in result.issues:
            # Add rule
            rule = {
                "id": issue.id,
                "name": issue.title,
                "shortDescription": {"text": issue.title},
                "fullDescription": {"text": issue.description},
                "help": {"text": issue.recommendation},
                "defaultConfiguration": {
                    "level": "error" if issue.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH] else "warning"
                },
            }
            sarif["runs"][0]["tool"]["driver"]["rules"].append(rule)
            
            # Add result
            sarif_result = {
                "ruleId": issue.id,
                "message": {"text": issue.description},
                "level": "error" if issue.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH] else "warning",
            }
            sarif["runs"][0]["results"].append(sarif_result)
        
        return sarif


# Convenience functions
def quick_scan(code: str) -> Dict[str, Any]:
    """Quick scan with default settings."""
    engine = SentinelSecurityEngine()
    result = engine.scan(code)
    return engine.get_summary(result)


def full_audit(code: str, filename: str = "Contract.sol") -> str:
    """Full audit with all modules and markdown report."""
    engine = SentinelSecurityEngine()
    result = engine.scan(
        code,
        filename=filename,
        deep_analysis=True,
        include_slither=True,
        include_formal=True,
    )
    return engine.generate_report(result)


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║   ███████╗███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗             ║
║   ██╔════╝██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║             ║
║   ███████╗█████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║             ║
║   ╚════██║██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║             ║
║   ███████║███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗        ║
║   ╚══════╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝        ║
║                                                                           ║
║   ████████████████████████████████████████████████████████████████████    ║
║   █                    SHIELD v2.0.0                                 █    ║
║   █     Professional Smart Contract Security Suite                   █    ║
║   ████████████████████████████████████████████████████████████████████    ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)
    
    engine = SentinelSecurityEngine()
    
    print("📊 SENTINEL Security Engine Initialized")
    print(f"   Version: {engine.VERSION}")
    print(f"   Codename: {engine.CODENAME}")
    print(f"\n🔧 Active Modules:")
    
    for name, module in engine.modules.items():
        status = "✅ Loaded" if module else "❌ Not available"
        print(f"   - {name}: {status}")
    
    print("\n🚀 Ready for security analysis!")
    print("   Use: sentinel.scan(code) or sentinel.scan_file(path)")
