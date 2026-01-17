"""
═══════════════════════════════════════════════════════════════════════════════
 SENTINEL SHIELD - pytest configuration and shared fixtures
 Author: SENTINEL Team
═══════════════════════════════════════════════════════════════════════════════
"""

import pytest
import asyncio
from typing import Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_erc20_bytecode() -> bytes:
    """Standard ERC20 contract bytecode prefix"""
    return bytes.fromhex(
        "6080604052600436106100af5760003560e01c80633950935111610067578063395093511461026857806370a082311461028"
    )


@pytest.fixture
def sample_honeypot_bytecode() -> bytes:
    """Bytecode containing honeypot patterns"""
    return bytes.fromhex(
        "32"  # ORIGIN - common honeypot check
        + "54" * 20  # Excessive SLOAD
        + "60640455"  # PUSH1 100 DIV SSTORE - fee manipulation
    )


@pytest.fixture
def sample_proxy_bytecode() -> bytes:
    """Proxy contract bytecode with DELEGATECALL"""
    return bytes.fromhex(
        "6080604052366100135761001f61004c565b005b6100375b61003361002856"
    )


@pytest.fixture
def uniswap_router_address() -> str:
    """Uniswap V2 Router address (whitelisted)"""
    return "0x7a250d5630b4cf539739df2c5dacb4c659f2488d"


@pytest.fixture
def common_selectors() -> dict:
    """Common function selectors"""
    return {
        "transfer": "0xa9059cbb",
        "approve": "0x095ea7b3",
        "transferFrom": "0x23b872dd",
        "mint": "0x40c10f19",
        "pause": "0x8456cb59",
        "renounceOwnership": "0x715018a6",
        "setFeePercent": "0x7deb6025",
    }


@pytest.fixture
def mock_decompiler_result() -> dict:
    """Mock response from Rust decompiler"""
    return {
        "bytecode_hash": "0xabc123def456",
        "bytecode_size": 1024,
        "instruction_count": 256,
        "security": {
            "function_selectors": ["0xa9059cbb", "0x095ea7b3", "0x23b872dd"],
            "external_calls": 2,
            "storage_writes": 5,
            "dangerous_opcodes": [],
            "has_selfdestruct": False,
            "has_delegatecall": False,
            "has_create": False,
            "complexity_score": 45,
            "risk_indicators": []
        }
    }


@pytest.fixture
def malicious_decompiler_result() -> dict:
    """Decompiler result for a malicious contract"""
    return {
        "bytecode_hash": "0xbadbadbad",
        "bytecode_size": 2048,
        "instruction_count": 512,
        "security": {
            "function_selectors": [
                "0x40c10f19",  # mint
                "0x8456cb59",  # pause
                "0x7deb6025",  # setFeePercent
            ],
            "external_calls": 15,
            "storage_writes": 25,
            "dangerous_opcodes": ["SELFDESTRUCT", "DELEGATECALL", "ORIGIN"],
            "has_selfdestruct": True,
            "has_delegatecall": True,
            "has_create": True,
            "complexity_score": 95,
            "risk_indicators": [
                "Excessive external calls",
                "Contains SELFDESTRUCT",
                "ORIGIN used (honeypot indicator)",
            ]
        }
    }


# ═══════════════════════════════════════════════════════════════════════════════
#                              PYTEST MARKERS
# ═══════════════════════════════════════════════════════════════════════════════

def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "asyncio: marks tests as async tests"
    )
