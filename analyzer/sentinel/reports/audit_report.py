"""
╔═══════════════════════════════════════════════════════════════════════════╗
║           SENTINEL SHIELD - AUDIT REPORT GENERATOR                        ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Professional Security Audit Reports - Trail of Bits Style                ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any
import json
import hashlib
from pathlib import Path


class FindingSeverity(Enum):
    """Severity levels matching industry standards."""
    CRITICAL = ("Critical", "#DC2626", 10)
    HIGH = ("High", "#EA580C", 8)
    MEDIUM = ("Medium", "#CA8A04", 5)
    LOW = ("Low", "#16A34A", 2)
    INFORMATIONAL = ("Informational", "#6B7280", 0)
    
    def __init__(self, label: str, color: str, score: int):
        self.label = label
        self.color = color
        self.score = score


class FindingStatus(Enum):
    """Finding resolution status."""
    OPEN = "Open"
    ACKNOWLEDGED = "Acknowledged"
    RESOLVED = "Resolved"
    WONT_FIX = "Won't Fix"


class FindingCategory(Enum):
    """Categories of security findings."""
    ACCESS_CONTROL = "Access Control"
    ARITHMETIC = "Arithmetic"
    REENTRANCY = "Reentrancy"
    ORACLE = "Oracle Manipulation"
    FLASH_LOAN = "Flash Loan Attack"
    MEV = "MEV Vulnerability"
    LOGIC = "Business Logic"
    DATA_VALIDATION = "Data Validation"
    DENIAL_OF_SERVICE = "Denial of Service"
    GAS_OPTIMIZATION = "Gas Optimization"
    CODE_QUALITY = "Code Quality"
    CENTRALIZATION = "Centralization Risk"
    UPGRADE = "Upgrade Safety"


@dataclass
class CodeSnippet:
    """Code snippet with highlighting."""
    file_path: str
    start_line: int
    end_line: int
    code: str
    highlight_lines: List[int] = field(default_factory=list)
    language: str = "solidity"


@dataclass
class Finding:
    """Security finding in audit report."""
    id: str
    title: str
    severity: FindingSeverity
    category: FindingCategory
    description: str
    impact: str
    likelihood: str
    affected_code: List[CodeSnippet]
    recommendation: str
    references: List[str] = field(default_factory=list)
    status: FindingStatus = FindingStatus.OPEN
    developer_response: str = ""
    auditor_notes: str = ""
    cwe_id: Optional[str] = None
    swc_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity.label,
            "category": self.category.value,
            "description": self.description,
            "impact": self.impact,
            "likelihood": self.likelihood,
            "recommendation": self.recommendation,
            "references": self.references,
            "status": self.status.value,
            "cwe_id": self.cwe_id,
            "swc_id": self.swc_id,
        }


@dataclass
class AuditMetadata:
    """Metadata for the audit report."""
    project_name: str
    project_version: str
    audit_start_date: datetime
    audit_end_date: datetime
    auditors: List[str]
    repository_url: str
    commit_hash: str
    scope: List[str]
    methods: List[str] = field(default_factory=lambda: [
        "Manual Code Review",
        "Static Analysis (Slither, Mythril)",
        "Dynamic Analysis",
        "Formal Verification",
        "Fuzzing",
    ])
    total_sloc: int = 0
    test_coverage: float = 0.0


class AuditReport:
    """
    Professional security audit report generator.
    Produces reports in the style of Trail of Bits, OpenZeppelin, Consensys Diligence.
    """
    
    def __init__(self, metadata: AuditMetadata):
        self.metadata = metadata
        self.findings: List[Finding] = []
        self.executive_summary: str = ""
        self.scope_description: str = ""
        self.methodology: str = ""
        self.additional_notes: str = ""
    
    def add_finding(self, finding: Finding) -> None:
        """Add a security finding to the report."""
        self.findings.append(finding)
    
    def get_severity_counts(self) -> Dict[str, int]:
        """Get count of findings by severity."""
        counts = {sev.label: 0 for sev in FindingSeverity}
        for finding in self.findings:
            counts[finding.severity.label] += 1
        return counts
    
    def get_category_counts(self) -> Dict[str, int]:
        """Get count of findings by category."""
        counts = {cat.value: 0 for cat in FindingCategory}
        for finding in self.findings:
            counts[finding.category.value] += 1
        return {k: v for k, v in counts.items() if v > 0}
    
    def calculate_risk_score(self) -> float:
        """Calculate overall risk score (0-100)."""
        if not self.findings:
            return 0.0
        
        total_score = sum(f.severity.score for f in self.findings)
        max_possible = len(self.findings) * FindingSeverity.CRITICAL.score
        return min(100, (total_score / max_possible) * 100) if max_possible > 0 else 0
    
    def generate_executive_summary(self) -> str:
        """Generate executive summary based on findings."""
        counts = self.get_severity_counts()
        total = len(self.findings)
        risk_score = self.calculate_risk_score()
        
        # Determine overall assessment
        if counts["Critical"] > 0:
            assessment = "The audit identified critical vulnerabilities that must be addressed before deployment."
        elif counts["High"] > 0:
            assessment = "The audit identified high-severity issues that should be resolved before mainnet deployment."
        elif counts["Medium"] > 0:
            assessment = "The audit identified medium-severity issues that should be addressed."
        elif counts["Low"] > 0:
            assessment = "The audit identified minor issues. The codebase demonstrates good security practices."
        else:
            assessment = "No significant security issues were identified. The codebase follows security best practices."
        
        summary = f"""
## Executive Summary

SENTINEL Security conducted a security audit of **{self.metadata.project_name}** 
from {self.metadata.audit_start_date.strftime('%B %d, %Y')} to 
{self.metadata.audit_end_date.strftime('%B %d, %Y')}.

### Overview

The audit reviewed {len(self.metadata.scope)} contracts totaling approximately 
{self.metadata.total_sloc:,} lines of Solidity code. The test coverage at the 
time of audit was {self.metadata.test_coverage:.1f}%.

### Risk Assessment

| Severity | Count |
|----------|-------|
| Critical | {counts['Critical']} |
| High | {counts['High']} |
| Medium | {counts['Medium']} |
| Low | {counts['Low']} |
| Informational | {counts['Informational']} |
| **Total** | **{total}** |

**Overall Risk Score: {risk_score:.1f}/100**

### Assessment

{assessment}

### Key Findings

"""
        # Add key findings summary
        critical_high = [f for f in self.findings if f.severity in [FindingSeverity.CRITICAL, FindingSeverity.HIGH]]
        if critical_high:
            for finding in critical_high[:5]:
                summary += f"- **[{finding.severity.label}]** {finding.title}\n"
        else:
            summary += "No critical or high severity findings.\n"
        
        return summary
    
    def generate_methodology_section(self) -> str:
        """Generate methodology section."""
        return f"""
## Methodology

### Audit Approach

The security assessment employed multiple techniques to ensure comprehensive coverage:

1. **Manual Code Review**: Line-by-line analysis of all in-scope contracts, focusing on 
   business logic, access control, and known vulnerability patterns.

2. **Static Analysis**: Automated scanning using industry-standard tools:
   - Slither for Solidity-specific vulnerabilities
   - Mythril for symbolic execution
   - Semgrep for custom pattern matching

3. **Dynamic Analysis**: Runtime testing including:
   - Fuzzing with Echidna/Foundry
   - Property-based testing
   - Invariant testing

4. **Formal Verification**: Mathematical proofs for critical invariants where applicable.

5. **Architecture Review**: Assessment of overall design patterns, upgrade mechanisms,
   and integration risks.

### Scope

The following contracts were in scope for this audit:

| Contract | SLOC | Complexity |
|----------|------|------------|
""" + "\n".join([f"| `{contract}` | - | - |" for contract in self.metadata.scope]) + """

### Limitations

- The audit was conducted at a specific point in time ({self.metadata.commit_hash[:8]})
- Off-chain components and external integrations were not in scope
- Economic attacks requiring significant capital were not simulated
- The audit does not guarantee absence of vulnerabilities
"""
    
    def generate_findings_section(self) -> str:
        """Generate detailed findings section."""
        section = "\n## Findings\n\n"
        
        # Sort by severity
        sorted_findings = sorted(
            self.findings,
            key=lambda f: f.severity.score,
            reverse=True
        )
        
        for finding in sorted_findings:
            section += self._format_finding(finding)
        
        return section
    
    def _format_finding(self, finding: Finding) -> str:
        """Format a single finding for the report."""
        severity_badge = f"[{finding.severity.label.upper()}]"
        
        output = f"""
### {finding.id}: {finding.title}

**Severity**: {severity_badge}  
**Category**: {finding.category.value}  
**Status**: {finding.status.value}
"""
        
        if finding.swc_id:
            output += f"**SWC ID**: {finding.swc_id}  \n"
        if finding.cwe_id:
            output += f"**CWE ID**: {finding.cwe_id}  \n"
        
        output += f"""
#### Description

{finding.description}

#### Impact

{finding.impact}

#### Likelihood

{finding.likelihood}

"""
        
        # Add code snippets
        if finding.affected_code:
            output += "#### Affected Code\n\n"
            for snippet in finding.affected_code:
                output += f"**{snippet.file_path}** (lines {snippet.start_line}-{snippet.end_line}):\n\n"
                output += f"```{snippet.language}\n{snippet.code}\n```\n\n"
        
        output += f"""#### Recommendation

{finding.recommendation}

"""
        
        if finding.references:
            output += "#### References\n\n"
            for ref in finding.references:
                output += f"- {ref}\n"
            output += "\n"
        
        if finding.developer_response:
            output += f"""#### Developer Response

{finding.developer_response}

"""
        
        output += "---\n"
        return output
    
    def generate_appendix(self) -> str:
        """Generate appendix with additional information."""
        return f"""
## Appendix

### A. Severity Classification

| Severity | Description |
|----------|-------------|
| Critical | Exploitation likely, major impact (fund loss, contract takeover) |
| High | Exploitation possible, significant impact |
| Medium | Exploitation requires specific conditions, moderate impact |
| Low | Unlikely exploitation, minor impact |
| Informational | Best practices, code quality improvements |

### B. Finding Categories

| Category | Description |
|----------|-------------|
| Access Control | Unauthorized access to privileged functions |
| Arithmetic | Integer overflow/underflow, precision loss |
| Reentrancy | State manipulation via recursive calls |
| Oracle Manipulation | Price feed attacks, stale data |
| Flash Loan Attack | Single-transaction economic exploits |
| MEV Vulnerability | Front-running, sandwich attacks |
| Logic | Flawed business logic implementation |

### C. Audit Team

| Auditor | Role |
|---------|------|
""" + "\n".join([f"| {auditor} | Security Researcher |" for auditor in self.metadata.auditors]) + """

### D. Tools Used

- **Static Analysis**: Slither, Mythril, Semgrep
- **Fuzzing**: Foundry, Echidna
- **Formal Verification**: Certora, Halmos
- **Custom**: SENTINEL Security Suite

### E. Disclaimer

This audit report is provided "as is" with no warranties. The audit was 
conducted at a specific point in time and does not guarantee the security 
of the code after modifications. SENTINEL Security is not responsible for 
any security breaches or losses that may occur after the audit.

---

**Report Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Report Hash**: {self._generate_report_hash()}
"""
    
    def _generate_report_hash(self) -> str:
        """Generate hash of report for integrity verification."""
        content = json.dumps({
            "metadata": {
                "project": self.metadata.project_name,
                "commit": self.metadata.commit_hash,
                "date": self.metadata.audit_end_date.isoformat(),
            },
            "findings": [f.to_dict() for f in self.findings]
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def generate_markdown(self) -> str:
        """Generate complete audit report in Markdown format."""
        report = f"""# Security Audit Report

## {self.metadata.project_name}

**Version**: {self.metadata.project_version}  
**Audit Period**: {self.metadata.audit_start_date.strftime('%B %d, %Y')} - {self.metadata.audit_end_date.strftime('%B %d, %Y')}  
**Repository**: {self.metadata.repository_url}  
**Commit**: `{self.metadata.commit_hash}`

---

{self.generate_executive_summary()}

{self.generate_methodology_section()}

{self.generate_findings_section()}

{self.generate_appendix()}
"""
        return report
    
    def generate_json(self) -> str:
        """Generate machine-readable JSON report."""
        report_data = {
            "metadata": {
                "project_name": self.metadata.project_name,
                "project_version": self.metadata.project_version,
                "audit_start_date": self.metadata.audit_start_date.isoformat(),
                "audit_end_date": self.metadata.audit_end_date.isoformat(),
                "auditors": self.metadata.auditors,
                "repository_url": self.metadata.repository_url,
                "commit_hash": self.metadata.commit_hash,
                "scope": self.metadata.scope,
                "total_sloc": self.metadata.total_sloc,
                "test_coverage": self.metadata.test_coverage,
            },
            "summary": {
                "total_findings": len(self.findings),
                "severity_counts": self.get_severity_counts(),
                "category_counts": self.get_category_counts(),
                "risk_score": self.calculate_risk_score(),
            },
            "findings": [f.to_dict() for f in self.findings],
            "report_hash": self._generate_report_hash(),
            "generated_at": datetime.now().isoformat(),
        }
        return json.dumps(report_data, indent=2)
    
    def save_report(self, output_dir: str, formats: List[str] = None) -> Dict[str, str]:
        """Save report in specified formats."""
        if formats is None:
            formats = ["md", "json"]
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        project_slug = self.metadata.project_name.lower().replace(" ", "-")
        date_str = self.metadata.audit_end_date.strftime("%Y%m%d")
        
        if "md" in formats:
            md_path = output_path / f"{project_slug}-audit-{date_str}.md"
            md_path.write_text(self.generate_markdown())
            saved_files["markdown"] = str(md_path)
        
        if "json" in formats:
            json_path = output_path / f"{project_slug}-audit-{date_str}.json"
            json_path.write_text(self.generate_json())
            saved_files["json"] = str(json_path)
        
        return saved_files


class QuickAuditReportGenerator:
    """Quick report generator from scan results."""
    
    @staticmethod
    def from_scan_results(
        project_name: str,
        scan_results: List[Dict],
        repository_url: str = "",
        commit_hash: str = ""
    ) -> AuditReport:
        """Generate audit report from vulnerability scan results."""
        metadata = AuditMetadata(
            project_name=project_name,
            project_version="1.0.0",
            audit_start_date=datetime.now(),
            audit_end_date=datetime.now(),
            auditors=["SENTINEL Automated Scanner"],
            repository_url=repository_url,
            commit_hash=commit_hash or "N/A",
            scope=list(set(r.get("file", "Unknown") for r in scan_results)),
        )
        
        report = AuditReport(metadata)
        
        # Convert scan results to findings
        for i, result in enumerate(scan_results, 1):
            severity_map = {
                "critical": FindingSeverity.CRITICAL,
                "high": FindingSeverity.HIGH,
                "medium": FindingSeverity.MEDIUM,
                "low": FindingSeverity.LOW,
                "info": FindingSeverity.INFORMATIONAL,
            }
            
            category_map = {
                "reentrancy": FindingCategory.REENTRANCY,
                "access_control": FindingCategory.ACCESS_CONTROL,
                "arithmetic": FindingCategory.ARITHMETIC,
                "oracle": FindingCategory.ORACLE,
                "flash_loan": FindingCategory.FLASH_LOAN,
            }
            
            finding = Finding(
                id=f"SEN-{i:03d}",
                title=result.get("name", "Unknown Vulnerability"),
                severity=severity_map.get(result.get("severity", "").lower(), FindingSeverity.INFORMATIONAL),
                category=category_map.get(result.get("category", "").lower(), FindingCategory.CODE_QUALITY),
                description=result.get("description", "No description available."),
                impact=result.get("impact", "Potential security risk."),
                likelihood=result.get("likelihood", "Unknown"),
                affected_code=[],
                recommendation=result.get("remediation", "Review and fix the identified issue."),
                swc_id=result.get("swc_id"),
                cwe_id=result.get("cwe_id"),
            )
            
            report.add_finding(finding)
        
        return report


if __name__ == "__main__":
    # Example usage
    metadata = AuditMetadata(
        project_name="Example Protocol",
        project_version="1.0.0",
        audit_start_date=datetime(2024, 1, 1),
        audit_end_date=datetime(2024, 1, 15),
        auditors=["Alice", "Bob"],
        repository_url="https://github.com/example/protocol",
        commit_hash="abc123def456",
        scope=["Token.sol", "Vault.sol", "Oracle.sol"],
        total_sloc=2500,
        test_coverage=85.5,
    )
    
    report = AuditReport(metadata)
    
    # Add example finding
    report.add_finding(Finding(
        id="SEN-001",
        title="Reentrancy in Withdraw Function",
        severity=FindingSeverity.CRITICAL,
        category=FindingCategory.REENTRANCY,
        description="The withdraw function makes an external call before updating state.",
        impact="An attacker can drain all funds from the contract.",
        likelihood="High - easily exploitable with a malicious contract.",
        affected_code=[CodeSnippet(
            file_path="Vault.sol",
            start_line=45,
            end_line=52,
            code="function withdraw() external {\n    payable(msg.sender).transfer(balances[msg.sender]);\n    balances[msg.sender] = 0;\n}"
        )],
        recommendation="Follow checks-effects-interactions pattern or use ReentrancyGuard.",
        swc_id="SWC-107",
        cwe_id="CWE-841",
    ))
    
    print(report.generate_markdown())
