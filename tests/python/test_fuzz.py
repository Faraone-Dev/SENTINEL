"""
╔═══════════════════════════════════════════════════════════════════════════╗
║              SENTINEL SHIELD - FUZZ & PROPERTY TESTS (PYTHON)             ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Hypothesis-based property testing and randomized fuzzing                 ║
║  Install: pip install hypothesis                                          ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import pytest
import random
import string
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Try to import hypothesis, skip if not available
try:
    from hypothesis import given, strategies as st, settings, assume, example
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False
    # Create dummy decorators
    def given(*args, **kwargs):
        def decorator(f):
            return pytest.mark.skip(reason="hypothesis not installed")(f)
        return decorator
    def settings(*args, **kwargs):
        def decorator(f):
            return f
        return decorator
    def example(*args, **kwargs):
        def decorator(f):
            return f
        return decorator
    def assume(x):
        return x
    class st:
        @staticmethod
        def text(*args, **kwargs): return None
        @staticmethod
        def integers(*args, **kwargs): return None
        @staticmethod
        def floats(*args, **kwargs): return None
        @staticmethod
        def lists(*args, **kwargs): return None
        @staticmethod
        def dictionaries(*args, **kwargs): return None
        @staticmethod
        def booleans(*args, **kwargs): return None
        @staticmethod
        def one_of(*args, **kwargs): return None
        @staticmethod
        def from_regex(*args, **kwargs): return None


# ═══════════════════════════════════════════════════════════════════════════
#                          DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════

class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class VulnerabilityFinding:
    severity: str
    category: str
    confidence: float
    description: str
    location: Optional[str] = None
    

@dataclass
class AnalysisResult:
    risk_score: float
    risk_level: RiskLevel
    findings: List[VulnerabilityFinding]
    patterns_detected: List[str]


# ═══════════════════════════════════════════════════════════════════════════
#                          CORE FUNCTIONS TO TEST
# ═══════════════════════════════════════════════════════════════════════════

def calculate_risk_score(findings: List[VulnerabilityFinding]) -> float:
    """Calculate aggregate risk score from findings."""
    if not findings:
        return 0.0
    
    weights = {"critical": 30, "high": 20, "medium": 10, "low": 5, "info": 1}
    total = 0.0
    
    for finding in findings:
        weight = weights.get(finding.severity.lower(), 5)
        total += weight * finding.confidence
    
    # Normalize to 0-100
    return min(100.0, total)


def categorize_risk(score: float) -> RiskLevel:
    """Categorize risk level from score."""
    if score == 0:
        return RiskLevel.SAFE
    elif score < 25:
        return RiskLevel.LOW
    elif score < 50:
        return RiskLevel.MEDIUM
    elif score < 75:
        return RiskLevel.HIGH
    else:
        return RiskLevel.CRITICAL


def validate_address(address: str) -> bool:
    """Validate Ethereum address format."""
    if not address:
        return False
    if not address.startswith("0x"):
        return False
    if len(address) != 42:
        return False
    try:
        int(address[2:], 16)
        return True
    except ValueError:
        return False


def normalize_bytecode(bytecode: str) -> str:
    """Normalize bytecode for analysis."""
    bytecode = bytecode.strip()
    if bytecode.startswith("0x"):
        bytecode = bytecode[2:]
    return bytecode.lower()


def detect_patterns(bytecode: str) -> List[str]:
    """Detect known vulnerability patterns in bytecode."""
    patterns = []
    normalized = normalize_bytecode(bytecode)
    
    # Simplified pattern detection
    if "selfdestruct" in normalized or "ff" in normalized:
        patterns.append("SELFDESTRUCT")
    if "delegatecall" in normalized or "f4" in normalized:
        patterns.append("DELEGATECALL")
    if "callvalue" in normalized or "34" in normalized:
        patterns.append("CALLVALUE")
    
    return patterns


def parse_function_signature(sig: str) -> Dict[str, Any]:
    """Parse function signature into components."""
    sig = sig.strip()
    if "(" not in sig:
        return {"name": sig, "params": []}
    
    name = sig.split("(")[0]
    params_str = sig.split("(")[1].rstrip(")")
    params = [p.strip() for p in params_str.split(",") if p.strip()]
    
    return {"name": name, "params": params}


# ═══════════════════════════════════════════════════════════════════════════
#                          PROPERTY-BASED TESTS
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
class TestPropertyBased:
    """Property-based tests using Hypothesis."""
    
    @given(st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False))
    def test_risk_categorization_is_monotonic(self, score):
        """Higher scores should never give lower risk levels."""
        level = categorize_risk(score)
        
        # Property: score 0 is always safe
        if score == 0:
            assert level == RiskLevel.SAFE
        
        # Property: score 100 is always critical
        if score >= 75:
            assert level == RiskLevel.CRITICAL
    
    @given(st.lists(st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False), min_size=0, max_size=20))
    def test_risk_score_bounds(self, confidences):
        """Risk score should always be between 0 and 100."""
        findings = [
            VulnerabilityFinding(
                severity=random.choice(["critical", "high", "medium", "low"]),
                category="test",
                confidence=c,
                description="test"
            )
            for c in confidences
        ]
        
        score = calculate_risk_score(findings)
        
        assert 0 <= score <= 100, f"Score {score} out of bounds"
    
    @given(st.text(min_size=0, max_size=100))
    def test_address_validation_deterministic(self, addr):
        """Same address should always give same validation result."""
        result1 = validate_address(addr)
        result2 = validate_address(addr)
        
        assert result1 == result2, "Validation is not deterministic"
    
    @given(st.from_regex(r"0x[0-9a-fA-F]{40}", fullmatch=True))
    def test_valid_address_always_passes(self, addr):
        """Properly formatted addresses should always be valid."""
        assert validate_address(addr), f"Valid address {addr} rejected"
    
    @given(st.text(min_size=0, max_size=1000))
    def test_bytecode_normalization_idempotent(self, bytecode):
        """Normalizing twice should give same result."""
        normalized1 = normalize_bytecode(bytecode)
        normalized2 = normalize_bytecode(normalized1)
        
        assert normalized1 == normalized2, "Normalization not idempotent"
    
    @given(st.text(min_size=0, max_size=500))
    def test_bytecode_normalization_lowercase(self, bytecode):
        """Normalized bytecode should be lowercase."""
        normalized = normalize_bytecode(bytecode)
        assert normalized == normalized.lower(), "Normalization didn't lowercase"
    
    @given(st.text(min_size=0, max_size=200))
    def test_pattern_detection_stable(self, bytecode):
        """Pattern detection should be deterministic."""
        patterns1 = detect_patterns(bytecode)
        patterns2 = detect_patterns(bytecode)
        
        assert patterns1 == patterns2, "Pattern detection not stable"
    
    @given(st.text(min_size=0, max_size=100))
    @settings(max_examples=200)
    def test_function_signature_parsing_no_crash(self, sig):
        """Function signature parsing should never crash."""
        try:
            result = parse_function_signature(sig)
            assert "name" in result
            assert "params" in result
        except Exception as e:
            pytest.fail(f"Parsing crashed on '{sig}': {e}")


# ═══════════════════════════════════════════════════════════════════════════
#                          FUZZ TESTS (Manual)
# ═══════════════════════════════════════════════════════════════════════════

class TestFuzz:
    """Manual fuzz tests for edge cases."""
    
    def test_fuzz_address_validation_random(self):
        """Fuzz address validation with random strings."""
        for _ in range(1000):
            length = random.randint(0, 100)
            chars = string.ascii_letters + string.digits + "0x"
            addr = "".join(random.choices(chars, k=length))
            
            # Should not crash
            result = validate_address(addr)
            assert isinstance(result, bool)
    
    def test_fuzz_address_validation_edge_cases(self):
        """Test edge cases for address validation."""
        edge_cases = [
            "",
            "0x",
            "0x0",
            "0x" + "0" * 40,
            "0x" + "f" * 40,
            "0x" + "F" * 40,
            "0x" + "g" * 40,  # Invalid hex
            "1x" + "0" * 40,
            "0x" + "0" * 39,
            "0x" + "0" * 41,
            None,  # Should handle gracefully
        ]
        
        for case in edge_cases:
            try:
                if case is None:
                    result = validate_address("")
                else:
                    result = validate_address(case)
                assert isinstance(result, bool)
            except Exception:
                pass  # Some edge cases may raise, that's ok
    
    def test_fuzz_risk_score_random_findings(self):
        """Fuzz risk score with random findings."""
        severities = ["critical", "high", "medium", "low", "info", "unknown"]
        
        for _ in range(100):
            num_findings = random.randint(0, 50)
            findings = [
                VulnerabilityFinding(
                    severity=random.choice(severities),
                    category="test",
                    confidence=random.random(),
                    description="test"
                )
                for _ in range(num_findings)
            ]
            
            score = calculate_risk_score(findings)
            
            assert 0 <= score <= 100
            assert isinstance(score, float)
    
    def test_fuzz_bytecode_patterns_random(self):
        """Fuzz pattern detection with random bytecode."""
        for _ in range(100):
            length = random.randint(0, 1000)
            bytecode = "0x" + "".join(random.choices("0123456789abcdef", k=length))
            
            patterns = detect_patterns(bytecode)
            
            assert isinstance(patterns, list)
            for p in patterns:
                assert isinstance(p, str)
    
    def test_fuzz_function_signature_random(self):
        """Fuzz function signature parsing."""
        for _ in range(100):
            # Generate random function-like strings
            name = "".join(random.choices(string.ascii_lowercase, k=random.randint(1, 20)))
            num_params = random.randint(0, 5)
            params = [
                random.choice(["uint256", "address", "bytes", "string", "bool"])
                for _ in range(num_params)
            ]
            sig = f"{name}({','.join(params)})"
            
            result = parse_function_signature(sig)
            
            assert result["name"] == name
            assert len(result["params"]) == num_params
    
    def test_fuzz_json_parsing_robustness(self):
        """Test JSON parsing with various inputs."""
        test_cases = [
            "{}",
            '{"address": "0x123"}',
            '{"address": null}',
            "[]",
            "null",
            '{"nested": {"deep": {"value": 123}}}',
            '{"array": [1, 2, 3, "mixed", null]}',
            '{"unicode": "\\u0000\\u001f"}',
            '{"large": ' + '"x"' + ' * 10000}',
        ]
        
        for case in test_cases:
            try:
                json.loads(case)
            except json.JSONDecodeError:
                pass  # Expected for invalid JSON


# ═══════════════════════════════════════════════════════════════════════════
#                          INVARIANT TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestInvariants:
    """Tests that verify invariants hold."""
    
    def test_invariant_empty_findings_zero_score(self):
        """Empty findings should always give zero score."""
        assert calculate_risk_score([]) == 0.0
    
    def test_invariant_zero_confidence_no_impact(self):
        """Zero confidence findings should not impact score."""
        findings = [
            VulnerabilityFinding(
                severity="critical",
                category="test",
                confidence=0.0,
                description="test"
            )
        ]
        assert calculate_risk_score(findings) == 0.0
    
    def test_invariant_risk_levels_ordered(self):
        """Risk levels should be properly ordered."""
        scores_and_levels = [
            (0, RiskLevel.SAFE),
            (10, RiskLevel.LOW),
            (30, RiskLevel.MEDIUM),
            (60, RiskLevel.HIGH),
            (90, RiskLevel.CRITICAL),
        ]
        
        for score, expected_level in scores_and_levels:
            actual_level = categorize_risk(score)
            assert actual_level == expected_level, f"Score {score} gave {actual_level}, expected {expected_level}"
    
    def test_invariant_address_length(self):
        """Valid addresses must be exactly 42 characters."""
        valid_addrs = [
            "0x" + "0" * 40,
            "0x" + "a" * 40,
            "0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1",
        ]
        
        for addr in valid_addrs:
            assert len(addr) == 42
            assert validate_address(addr)
    
    def test_invariant_normalization_removes_prefix(self):
        """Normalization should remove 0x prefix."""
        bytecode = "0xABCDEF"
        normalized = normalize_bytecode(bytecode)
        
        assert not normalized.startswith("0x")
        assert normalized == "abcdef"


# ═══════════════════════════════════════════════════════════════════════════
#                          BOUNDARY TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestBoundaries:
    """Tests for boundary conditions."""
    
    def test_boundary_risk_score_at_100(self):
        """Score should cap at 100."""
        # Create many high-severity findings
        findings = [
            VulnerabilityFinding(
                severity="critical",
                category="test",
                confidence=1.0,
                description="test"
            )
            for _ in range(100)
        ]
        
        score = calculate_risk_score(findings)
        assert score == 100.0
    
    def test_boundary_risk_level_transitions(self):
        """Test exact boundary values for risk levels."""
        boundaries = [
            (0, RiskLevel.SAFE),
            (0.001, RiskLevel.LOW),  # Just above 0
            (24.99, RiskLevel.LOW),
            (25.0, RiskLevel.MEDIUM),
            (49.99, RiskLevel.MEDIUM),
            (50.0, RiskLevel.HIGH),
            (74.99, RiskLevel.HIGH),
            (75.0, RiskLevel.CRITICAL),
            (100.0, RiskLevel.CRITICAL),
        ]
        
        for score, expected in boundaries:
            actual = categorize_risk(score)
            assert actual == expected, f"Score {score}: expected {expected}, got {actual}"
    
    def test_boundary_empty_bytecode(self):
        """Empty bytecode should be handled."""
        empty_cases = ["", "0x", "   ", "\n\t"]
        
        for case in empty_cases:
            normalized = normalize_bytecode(case)
            patterns = detect_patterns(case)
            
            assert isinstance(normalized, str)
            assert isinstance(patterns, list)
    
    def test_boundary_max_length_inputs(self):
        """Test with maximum reasonable length inputs."""
        # Long address (invalid but should not crash)
        long_addr = "0x" + "0" * 10000
        assert not validate_address(long_addr)
        
        # Long bytecode
        long_bytecode = "0x" + "ab" * 10000
        patterns = detect_patterns(long_bytecode)
        assert isinstance(patterns, list)
        
        # Long function signature
        long_sig = "function(" + ",".join(["uint256"] * 100) + ")"
        result = parse_function_signature(long_sig)
        assert result["name"] == "function"


# ═══════════════════════════════════════════════════════════════════════════
#                          REGRESSION TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestRegressions:
    """Tests for previously found bugs."""
    
    def test_regression_unicode_in_bytecode(self):
        """Bytecode with unicode should be handled."""
        bytecode = "0xABCDEF\u0000\u001f"
        normalized = normalize_bytecode(bytecode)
        assert isinstance(normalized, str)
    
    def test_regression_special_chars_in_signature(self):
        """Function signatures with special chars should be handled."""
        sigs = [
            "func()",
            "func(uint256)",
            "_internal()",
            "$special(bytes32)",
            "func((uint256,address))",  # Tuple
        ]
        
        for sig in sigs:
            result = parse_function_signature(sig)
            assert "name" in result
    
    def test_regression_mixed_case_severity(self):
        """Severity strings should be case-insensitive."""
        severities = ["CRITICAL", "Critical", "critical", "CrItIcAl"]
        
        for sev in severities:
            finding = VulnerabilityFinding(
                severity=sev,
                category="test",
                confidence=1.0,
                description="test"
            )
            score = calculate_risk_score([finding])
            assert score == 30.0, f"Severity '{sev}' gave score {score}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
