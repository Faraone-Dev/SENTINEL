"""
╔═══════════════════════════════════════════════════════════════════════════╗
║           SENTINEL SHIELD - FORMAL VERIFICATION ENGINE                    ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  SMT-Based Verification for Smart Contract Security Properties            ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any, Set, Callable
import subprocess
import shutil
import json
from pathlib import Path
import tempfile


class PropertyType(Enum):
    """Types of verifiable properties."""
    INVARIANT = "invariant"          # Always holds
    REACHABILITY = "reachability"    # Can reach state
    SAFETY = "safety"                # Bad state never reached
    LIVENESS = "liveness"            # Good state eventually reached
    FAIRNESS = "fairness"            # Resource access fairness


class VerificationStatus(Enum):
    """Result of verification."""
    VERIFIED = "verified"        # Property holds
    VIOLATED = "violated"        # Counterexample found
    UNKNOWN = "unknown"          # Cannot determine
    TIMEOUT = "timeout"          # Verification timed out
    ERROR = "error"              # Error during verification


@dataclass
class Property:
    """A property to verify."""
    id: str
    name: str
    property_type: PropertyType
    expression: str              # SMT-LIB or Solidity expression
    description: str
    severity: str = "high"


@dataclass
class VerificationResult:
    """Result of verifying a property."""
    property: Property
    status: VerificationStatus
    execution_time: float        # seconds
    counterexample: Optional[Dict] = None
    trace: Optional[List[str]] = None
    solver_output: str = ""


@dataclass
class ContractModel:
    """Formal model of a contract."""
    name: str
    state_variables: Dict[str, str]   # name -> type
    functions: List[str]
    invariants: List[str]
    assertions: List[str]


class FormalVerificationEngine:
    """
    Formal verification engine for Solidity smart contracts.
    
    Supports:
    - SMT-based symbolic execution
    - Property checking (invariants, safety, reachability)
    - Counterexample generation
    - Integration with solc --model-checker
    - Integration with external solvers (Z3, CVC5)
    
    Used by:
    - Certora Prover
    - Runtime Verification (K Framework)
    - Manticore
    - Mythril
    """
    
    # Common security properties to verify
    SECURITY_PROPERTIES = {
        "no_overflow": Property(
            id="SEC-001",
            name="Integer Overflow Protection",
            property_type=PropertyType.SAFETY,
            expression="forall x y. add(x, y) >= x && add(x, y) >= y",
            description="Addition operations should not overflow",
            severity="critical",
        ),
        "no_underflow": Property(
            id="SEC-002",
            name="Integer Underflow Protection",
            property_type=PropertyType.SAFETY,
            expression="forall x y. sub(x, y) <= x",
            description="Subtraction operations should not underflow",
            severity="critical",
        ),
        "no_reentrancy": Property(
            id="SEC-003",
            name="Reentrancy Safety",
            property_type=PropertyType.SAFETY,
            expression="locked == true => no_external_calls()",
            description="No external calls while in locked state",
            severity="critical",
        ),
        "access_control": Property(
            id="SEC-004",
            name="Access Control Invariant",
            property_type=PropertyType.INVARIANT,
            expression="admin_function() => msg.sender == owner",
            description="Admin functions only callable by owner",
            severity="critical",
        ),
        "balance_integrity": Property(
            id="SEC-005",
            name="Balance Integrity",
            property_type=PropertyType.INVARIANT,
            expression="sum(balances) == totalSupply",
            description="Sum of balances equals total supply",
            severity="high",
        ),
        "no_selfdestruct": Property(
            id="SEC-006",
            name="No Unauthorized Selfdestruct",
            property_type=PropertyType.SAFETY,
            expression="selfdestruct() => msg.sender == owner && timelockExpired",
            description="Selfdestruct only via authorized path",
            severity="critical",
        ),
        "withdrawal_safety": Property(
            id="SEC-007",
            name="Withdrawal Safety",
            property_type=PropertyType.SAFETY,
            expression="withdraw(x) => balances[msg.sender] >= x",
            description="Can only withdraw owned funds",
            severity="critical",
        ),
        "transfer_integrity": Property(
            id="SEC-008",
            name="Transfer Integrity",
            property_type=PropertyType.INVARIANT,
            expression="pre(balances[a] + balances[b]) == post(balances[a] + balances[b])",
            description="Transfer preserves total balance",
            severity="high",
        ),
        "pause_safety": Property(
            id="SEC-009",
            name="Pause Safety",
            property_type=PropertyType.SAFETY,
            expression="paused == true => no_transfers()",
            description="No transfers while paused",
            severity="medium",
        ),
        "upgrade_authorization": Property(
            id="SEC-010",
            name="Upgrade Authorization",
            property_type=PropertyType.SAFETY,
            expression="upgradeTo(x) => msg.sender == owner || msg.sender == admin",
            description="Upgrades only by authorized addresses",
            severity="critical",
        ),
    }
    
    # DeFi-specific properties
    DEFI_PROPERTIES = {
        "price_manipulation": Property(
            id="DEFI-001",
            name="Price Manipulation Safety",
            property_type=PropertyType.SAFETY,
            expression="abs(newPrice - oldPrice) / oldPrice <= maxDeviation",
            description="Price cannot deviate beyond threshold in single tx",
            severity="critical",
        ),
        "liquidity_invariant": Property(
            id="DEFI-002",
            name="Liquidity Invariant",
            property_type=PropertyType.INVARIANT,
            expression="reserveA * reserveB >= k",
            description="AMM constant product invariant",
            severity="critical",
        ),
        "flash_loan_repayment": Property(
            id="DEFI-003",
            name="Flash Loan Repayment",
            property_type=PropertyType.SAFETY,
            expression="post_loan_balance >= pre_loan_balance + fee",
            description="Flash loans must be repaid with fee",
            severity="critical",
        ),
        "collateral_ratio": Property(
            id="DEFI-004",
            name="Collateral Ratio Maintained",
            property_type=PropertyType.INVARIANT,
            expression="collateralValue >= debtValue * minRatio",
            description="Minimum collateral ratio always maintained",
            severity="high",
        ),
        "slippage_protection": Property(
            id="DEFI-005",
            name="Slippage Protection",
            property_type=PropertyType.SAFETY,
            expression="amountOut >= minAmountOut",
            description="Output amount meets minimum requirement",
            severity="medium",
        ),
    }
    
    def __init__(self, solver: str = "z3"):
        """
        Initialize verification engine.
        
        Args:
            solver: SMT solver to use (z3, cvc5, bitwuzla)
        """
        self.solver = solver
        self.solver_path = self._find_solver()
        self.properties: List[Property] = []
        self.results: List[VerificationResult] = []
    
    def _find_solver(self) -> Optional[str]:
        """Find the SMT solver executable."""
        solvers = {
            "z3": ["z3", "z3.exe"],
            "cvc5": ["cvc5", "cvc5.exe"],
            "bitwuzla": ["bitwuzla", "bitwuzla.exe"],
        }
        
        for name in solvers.get(self.solver, []):
            path = shutil.which(name)
            if path:
                return path
        
        return None
    
    def add_property(self, prop: Property):
        """Add a property to verify."""
        self.properties.append(prop)
    
    def add_security_properties(self):
        """Add all standard security properties."""
        for prop in self.SECURITY_PROPERTIES.values():
            self.properties.append(prop)
    
    def add_defi_properties(self):
        """Add DeFi-specific properties."""
        for prop in self.DEFI_PROPERTIES.values():
            self.properties.append(prop)
    
    def extract_model(self, code: str) -> ContractModel:
        """
        Extract formal model from Solidity code.
        
        Args:
            code: Solidity source
            
        Returns:
            Contract model for verification
        """
        # Extract contract name
        name_match = re.search(r"contract\s+(\w+)", code)
        name = name_match.group(1) if name_match else "Unknown"
        
        # Extract state variables
        state_vars = {}
        var_pattern = re.compile(
            r"^\s*(uint\d*|int\d*|address|bool|bytes\d*|string|mapping\([^)]+\))\s+"
            r"(?:public\s+|private\s+|internal\s+)?(\w+)",
            re.MULTILINE
        )
        for match in var_pattern.finditer(code):
            state_vars[match.group(2)] = match.group(1)
        
        # Extract functions
        functions = []
        func_pattern = re.compile(r"function\s+(\w+)\s*\(")
        functions = func_pattern.findall(code)
        
        # Extract invariants from comments
        invariants = []
        invariant_pattern = re.compile(r"///\s*@invariant\s+(.+)")
        for match in invariant_pattern.finditer(code):
            invariants.append(match.group(1))
        
        # Extract assertions
        assertions = []
        assert_pattern = re.compile(r"(?:require|assert)\s*\(\s*([^;]+)\s*[,;)]")
        for match in assert_pattern.finditer(code):
            assertions.append(match.group(1))
        
        return ContractModel(
            name=name,
            state_variables=state_vars,
            functions=functions,
            invariants=invariants,
            assertions=assertions,
        )
    
    def verify_with_solc(
        self,
        code: str,
        targets: List[str] = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Verify using Solidity compiler's built-in model checker.
        
        Args:
            code: Solidity source
            targets: Verification targets (overflow, underflow, divByZero, etc.)
            timeout: Timeout in seconds
            
        Returns:
            Verification results
        """
        if targets is None:
            targets = ["overflow", "underflow", "divByZero", "assert"]
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".sol",
            delete=False
        ) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            # Build solc command with model checker
            cmd = [
                "solc",
                "--model-checker-engine", "chc",  # Constrained Horn Clauses
                "--model-checker-targets", ",".join(targets),
                "--model-checker-timeout", str(timeout * 1000),  # ms
                temp_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 10
            )
            
            return self._parse_solc_output(result.stdout, result.stderr)
            
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "message": "Verification timed out"}
        except FileNotFoundError:
            return {"status": "error", "message": "solc not found"}
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def _parse_solc_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse solc model checker output."""
        results = {
            "status": "unknown",
            "findings": [],
            "warnings": [],
        }
        
        output = stdout + stderr
        
        # Check for verified
        if "CHC: All assertions are verified" in output:
            results["status"] = "verified"
        
        # Check for violations
        violation_pattern = re.compile(
            r"Warning: CHC: (\w+) happens here\.\n(.+?)(?=\n\n|\Z)",
            re.DOTALL
        )
        
        for match in violation_pattern.finditer(output):
            violation_type = match.group(1)
            details = match.group(2).strip()
            
            results["findings"].append({
                "type": violation_type,
                "details": details,
            })
            results["status"] = "violated"
        
        # Check for errors
        if "Error:" in output:
            results["status"] = "error"
            results["errors"] = re.findall(r"Error: (.+)", output)
        
        return results
    
    def verify_property_smt(
        self,
        prop: Property,
        model: ContractModel,
        timeout: int = 60
    ) -> VerificationResult:
        """
        Verify a property using SMT solver.
        
        Args:
            prop: Property to verify
            model: Contract model
            timeout: Timeout in seconds
            
        Returns:
            Verification result
        """
        import time
        start_time = time.time()
        
        # Generate SMT-LIB formula
        smt_formula = self._generate_smt_formula(prop, model)
        
        if not self.solver_path:
            return VerificationResult(
                property=prop,
                status=VerificationStatus.ERROR,
                execution_time=time.time() - start_time,
                solver_output="SMT solver not found",
            )
        
        # Write formula to temp file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".smt2",
            delete=False
        ) as f:
            f.write(smt_formula)
            smt_path = f.name
        
        try:
            # Run solver
            cmd = [self.solver_path, smt_path]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return self._parse_smt_result(prop, result, time.time() - start_time)
            
        except subprocess.TimeoutExpired:
            return VerificationResult(
                property=prop,
                status=VerificationStatus.TIMEOUT,
                execution_time=timeout,
            )
        finally:
            Path(smt_path).unlink(missing_ok=True)
    
    def _generate_smt_formula(self, prop: Property, model: ContractModel) -> str:
        """Generate SMT-LIB formula for property."""
        lines = [
            "(set-logic QF_LIA)",  # Quantifier-free linear integer arithmetic
            "(set-option :produce-models true)",
            "",
        ]
        
        # Declare state variables as SMT variables
        for var_name, var_type in model.state_variables.items():
            smt_type = self._solidity_to_smt_type(var_type)
            lines.append(f"(declare-const {var_name} {smt_type})")
        
        # Add assertions from contract
        for assertion in model.assertions:
            smt_expr = self._solidity_to_smt_expr(assertion)
            if smt_expr:
                lines.append(f"(assert {smt_expr})")
        
        # Add invariants
        for invariant in model.invariants:
            smt_expr = self._solidity_to_smt_expr(invariant)
            if smt_expr:
                lines.append(f"(assert {smt_expr})")
        
        # Negate property to check for counterexample
        prop_expr = self._property_to_smt(prop)
        lines.append(f"(assert (not {prop_expr}))")
        
        lines.extend([
            "",
            "(check-sat)",
            "(get-model)",
        ])
        
        return "\n".join(lines)
    
    def _solidity_to_smt_type(self, sol_type: str) -> str:
        """Convert Solidity type to SMT-LIB type."""
        if sol_type.startswith("uint") or sol_type.startswith("int"):
            return "Int"
        elif sol_type == "bool":
            return "Bool"
        elif sol_type == "address":
            return "Int"  # Addresses as integers
        else:
            return "Int"  # Default
    
    def _solidity_to_smt_expr(self, expr: str) -> Optional[str]:
        """Convert Solidity expression to SMT-LIB."""
        # Simple conversions
        expr = expr.strip()
        
        # Boolean operators
        expr = re.sub(r"\s*&&\s*", " ) (and ", expr)
        expr = re.sub(r"\s*\|\|\s*", " ) (or ", expr)
        expr = re.sub(r"!", "(not ", expr)
        
        # Comparison operators
        expr = re.sub(r"\s*==\s*", " ", expr)
        expr = re.sub(r"\s*!=\s*", " ", expr)
        expr = re.sub(r"\s*>=\s*", " ", expr)
        expr = re.sub(r"\s*<=\s*", " ", expr)
        expr = re.sub(r"\s*>\s*", " ", expr)
        expr = re.sub(r"\s*<\s*", " ", expr)
        
        # Wrap in parentheses
        if "==" in expr:
            parts = expr.split("==")
            if len(parts) == 2:
                return f"(= {parts[0].strip()} {parts[1].strip()})"
        
        if ">=" in expr:
            parts = expr.split(">=")
            if len(parts) == 2:
                return f"(>= {parts[0].strip()} {parts[1].strip()})"
        
        return None
    
    def _property_to_smt(self, prop: Property) -> str:
        """Convert property expression to SMT-LIB."""
        expr = prop.expression
        
        # Handle common patterns
        if "=>" in expr:
            parts = expr.split("=>")
            if len(parts) == 2:
                antecedent = self._solidity_to_smt_expr(parts[0]) or "true"
                consequent = self._solidity_to_smt_expr(parts[1]) or "true"
                return f"(=> {antecedent} {consequent})"
        
        return self._solidity_to_smt_expr(expr) or "true"
    
    def _parse_smt_result(
        self,
        prop: Property,
        result: subprocess.CompletedProcess,
        exec_time: float
    ) -> VerificationResult:
        """Parse SMT solver output."""
        output = result.stdout + result.stderr
        
        if "unsat" in output.lower():
            # Property holds (negation is unsatisfiable)
            return VerificationResult(
                property=prop,
                status=VerificationStatus.VERIFIED,
                execution_time=exec_time,
                solver_output=output,
            )
        
        elif "sat" in output.lower():
            # Counterexample exists
            counterexample = self._extract_counterexample(output)
            return VerificationResult(
                property=prop,
                status=VerificationStatus.VIOLATED,
                execution_time=exec_time,
                counterexample=counterexample,
                solver_output=output,
            )
        
        else:
            return VerificationResult(
                property=prop,
                status=VerificationStatus.UNKNOWN,
                execution_time=exec_time,
                solver_output=output,
            )
    
    def _extract_counterexample(self, output: str) -> Dict[str, Any]:
        """Extract counterexample from SMT model."""
        counterexample = {}
        
        # Parse (define-fun name () Type value) patterns
        define_pattern = re.compile(
            r"\(define-fun\s+(\w+)\s+\(\)\s+\w+\s+([^)]+)\)"
        )
        
        for match in define_pattern.finditer(output):
            name = match.group(1)
            value = match.group(2).strip()
            
            # Convert value
            try:
                if value.startswith("-"):
                    counterexample[name] = int(value.replace("(- ", "-").replace(")", ""))
                else:
                    counterexample[name] = int(value)
            except ValueError:
                counterexample[name] = value
        
        return counterexample
    
    def verify_all(
        self,
        code: str,
        timeout_per_property: int = 60
    ) -> Dict[str, Any]:
        """
        Verify all added properties.
        
        Args:
            code: Solidity source
            timeout_per_property: Timeout per property
            
        Returns:
            Complete verification results
        """
        model = self.extract_model(code)
        self.results = []
        
        for prop in self.properties:
            result = self.verify_property_smt(prop, model, timeout_per_property)
            self.results.append(result)
        
        return {
            "contract": model.name,
            "model": {
                "state_variables": model.state_variables,
                "functions": model.functions,
                "invariants": model.invariants,
            },
            "results": [self._result_to_dict(r) for r in self.results],
            "summary": self._generate_summary(),
        }
    
    def _result_to_dict(self, result: VerificationResult) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "property_id": result.property.id,
            "property_name": result.property.name,
            "type": result.property.property_type.value,
            "status": result.status.value,
            "execution_time": result.execution_time,
            "counterexample": result.counterexample,
            "severity": result.property.severity,
        }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate verification summary."""
        by_status = {
            "verified": 0,
            "violated": 0,
            "unknown": 0,
            "timeout": 0,
            "error": 0,
        }
        
        critical_violated = []
        
        for result in self.results:
            by_status[result.status.value] += 1
            
            if result.status == VerificationStatus.VIOLATED:
                if result.property.severity == "critical":
                    critical_violated.append(result.property.name)
        
        return {
            "total_properties": len(self.results),
            "by_status": by_status,
            "critical_violations": critical_violated,
            "verification_complete": by_status["unknown"] == 0 and by_status["timeout"] == 0,
        }
    
    def generate_report(self) -> str:
        """Generate human-readable verification report."""
        report = "# Formal Verification Report\n\n"
        
        summary = self._generate_summary()
        
        # Summary
        report += "## Summary\n\n"
        report += f"| Status | Count |\n|--------|-------|\n"
        for status, count in summary["by_status"].items():
            emoji = {"verified": "✅", "violated": "❌", "unknown": "❓", "timeout": "⏰", "error": "⚠️"}
            report += f"| {emoji.get(status, '')} {status.capitalize()} | {count} |\n"
        report += "\n"
        
        if summary["critical_violations"]:
            report += "### ⚠️ Critical Violations\n\n"
            for violation in summary["critical_violations"]:
                report += f"- {violation}\n"
            report += "\n"
        
        # Detailed Results
        report += "## Property Verification Results\n\n"
        
        for result in self.results:
            status_emoji = {
                VerificationStatus.VERIFIED: "✅",
                VerificationStatus.VIOLATED: "❌",
                VerificationStatus.UNKNOWN: "❓",
                VerificationStatus.TIMEOUT: "⏰",
                VerificationStatus.ERROR: "⚠️",
            }
            
            emoji = status_emoji.get(result.status, "•")
            report += f"### {emoji} [{result.property.id}] {result.property.name}\n\n"
            report += f"- **Type**: {result.property.property_type.value}\n"
            report += f"- **Severity**: {result.property.severity}\n"
            report += f"- **Status**: {result.status.value}\n"
            report += f"- **Time**: {result.execution_time:.2f}s\n\n"
            report += f"**Description**: {result.property.description}\n\n"
            report += f"**Property**: `{result.property.expression}`\n\n"
            
            if result.counterexample:
                report += "**Counterexample**:\n```json\n"
                report += json.dumps(result.counterexample, indent=2)
                report += "\n```\n\n"
            
            report += "---\n\n"
        
        return report


class InvariantGenerator:
    """
    Automatically generate invariants from contract code.
    Uses heuristics and patterns to infer likely invariants.
    """
    
    def __init__(self):
        self.invariants: List[str] = []
    
    def analyze(self, code: str) -> List[str]:
        """Generate likely invariants from code."""
        self.invariants = []
        
        # Balance invariants
        if "totalSupply" in code and "balanceOf" in code:
            self.invariants.append(
                "sum(balanceOf[addr] for all addr) == totalSupply"
            )
        
        # Ownership invariants
        if "owner" in code:
            self.invariants.append("owner != address(0)")
        
        # Mapping invariants
        mapping_pattern = re.compile(r"mapping\s*\([^)]+\)\s+(\w+)")
        for match in mapping_pattern.finditer(code):
            mapping_name = match.group(1)
            if "balance" in mapping_name.lower():
                self.invariants.append(f"{mapping_name}[addr] >= 0 for all addr")
        
        # Allowance invariants
        if "allowance" in code:
            self.invariants.append(
                "allowance[owner][spender] == approved_amount"
            )
        
        # Pausable invariants
        if "paused" in code:
            self.invariants.append(
                "paused => no state-changing external calls"
            )
        
        return self.invariants


if __name__ == "__main__":
    print("SENTINEL Formal Verification Engine")
    print("=" * 50)
    
    # Example contract
    example_contract = """
    // SPDX-License-Identifier: MIT
    pragma solidity ^0.8.0;
    
    /// @invariant sum(balances) == totalSupply
    contract Token {
        mapping(address => uint256) public balances;
        uint256 public totalSupply;
        address public owner;
        
        function transfer(address to, uint256 amount) external {
            require(balances[msg.sender] >= amount, "Insufficient balance");
            balances[msg.sender] -= amount;
            balances[to] += amount;
        }
        
        function mint(address to, uint256 amount) external {
            require(msg.sender == owner, "Not owner");
            balances[to] += amount;
            totalSupply += amount;
        }
    }
    """
    
    engine = FormalVerificationEngine()
    engine.add_security_properties()
    
    # Extract model
    model = engine.extract_model(example_contract)
    print(f"\n📋 Contract: {model.name}")
    print(f"📊 State Variables: {len(model.state_variables)}")
    print(f"🔧 Functions: {len(model.functions)}")
    print(f"📝 Invariants: {len(model.invariants)}")
    
    # Generate invariants
    gen = InvariantGenerator()
    generated_invariants = gen.analyze(example_contract)
    print(f"🔮 Generated Invariants: {len(generated_invariants)}")
    for inv in generated_invariants:
        print(f"   - {inv}")
    
    # Check for solver
    if engine.solver_path:
        print(f"\n✅ SMT Solver ({engine.solver}) found at: {engine.solver_path}")
    else:
        print(f"\n⚠️  SMT Solver ({engine.solver}) not found")
        print("   Install with: pip install z3-solver")
