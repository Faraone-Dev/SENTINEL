"""
╔═══════════════════════════════════════════════════════════════════════════╗
║           SENTINEL SHIELD - MEV & FLASH LOAN DETECTOR                     ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Advanced Detection for MEV Attacks, Flash Loans, and Sandwich Attacks    ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set, Tuple
from decimal import Decimal
import re
import json


class MEVType(Enum):
    """Types of MEV attacks."""
    SANDWICH = "sandwich"
    FRONTRUN = "frontrun"
    BACKRUN = "backrun"
    JIT_LIQUIDITY = "jit_liquidity"
    ARBITRAGE = "arbitrage"
    LIQUIDATION = "liquidation"
    NFT_SNIPE = "nft_snipe"
    TIME_BANDIT = "time_bandit"


class FlashLoanProvider(Enum):
    """Flash loan providers."""
    AAVE_V2 = "aave_v2"
    AAVE_V3 = "aave_v3"
    DYDX = "dydx"
    UNISWAP_V2 = "uniswap_v2"
    UNISWAP_V3 = "uniswap_v3"
    BALANCER = "balancer"
    MAKER = "maker"
    EULER = "euler"


@dataclass
class MEVAttack:
    """Represents a detected MEV attack."""
    type: MEVType
    severity: str
    description: str
    attacker: Optional[str] = None
    victim: Optional[str] = None
    profit_usd: Optional[Decimal] = None
    transactions: List[str] = field(default_factory=list)
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    recommendations: List[str] = field(default_factory=list)


@dataclass 
class FlashLoanUsage:
    """Represents a flash loan usage."""
    provider: FlashLoanProvider
    amount: int
    token: str
    fee: int
    is_attack: bool
    attack_type: Optional[str] = None
    affected_protocols: List[str] = field(default_factory=list)


class MEVDetector:
    """
    Detects MEV attacks and flash loan usage in transactions.
    Used for real-time protection and post-mortem analysis.
    """
    
    # Known MEV bot addresses
    MEV_BOTS = {
        "0x00000000000fde22a70e7b18c6f9f5f1de22a70e": "Flashbots Builder",
        "0x98c3d3183c4b8a650614ad179a1a98be0a8d6b8e": "BloXroute",
        "0xa57bd00134b2850b2a1c55860c9e9ea100fdd6cf": "MEV Bot",
        "0x5aa3393e361c2eb342408559309b3e873cd77ef3": "Sandwich Bot",
    }
    
    # Flash loan function signatures
    FLASH_LOAN_SIGS = {
        "0xab9c4b5d": ("AAVE V2", "flashLoan"),
        "0xe0232b42": ("AAVE V3", "flashLoan"),
        "0x5cffe9de": ("Balancer", "flashLoan"),
        "0xd9d98ce4": ("dYdX", "operate"),
        "0x022c0d9f": ("Uniswap V2", "swap"),  # Can be used for flash swaps
    }
    
    # DEX router addresses
    DEX_ROUTERS = {
        "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap V2",
        "0xe592427a0aece92de3edee1f18e0157c05861564": "Uniswap V3",
        "0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f": "SushiSwap",
        "0x1111111254fb6c44bac0bed2854e76f90643097d": "1inch",
        "0xdef1c0ded9bec7f1a1670819833240f027b25eff": "0x",
    }
    
    def __init__(self):
        self.detected_attacks: List[MEVAttack] = []
        self.flash_loans: List[FlashLoanUsage] = []
    
    def detect_sandwich_attack(
        self,
        frontrun_tx: Dict,
        victim_tx: Dict, 
        backrun_tx: Dict
    ) -> Optional[MEVAttack]:
        """
        Detect sandwich attack from three transactions.
        
        A sandwich attack consists of:
        1. Frontrun: Buy tokens to raise price
        2. Victim: User's trade at worse price
        3. Backrun: Sell tokens at higher price
        """
        # Check if transactions are in sequence
        if not (frontrun_tx.get("index", 0) < victim_tx.get("index", 0) < backrun_tx.get("index", 0)):
            return None
        
        # Check if frontrun and backrun are from same address
        if frontrun_tx.get("from") != backrun_tx.get("from"):
            return None
        
        # Check if victim is trading on same pair
        frontrun_data = frontrun_tx.get("input", "")
        victim_data = victim_tx.get("input", "")
        backrun_data = backrun_tx.get("input", "")
        
        # Detect swap functions
        swap_sigs = ["0x38ed1739", "0x7ff36ab5", "0x18cbafe5", "0xfb3bdb41"]
        
        is_frontrun_swap = any(frontrun_data.startswith(sig) for sig in swap_sigs)
        is_victim_swap = any(victim_data.startswith(sig) for sig in swap_sigs)
        is_backrun_swap = any(backrun_data.startswith(sig) for sig in swap_sigs)
        
        if not (is_frontrun_swap and is_victim_swap and is_backrun_swap):
            return None
        
        # Calculate attacker profit
        frontrun_gas = frontrun_tx.get("gasUsed", 0) * frontrun_tx.get("gasPrice", 0)
        backrun_gas = backrun_tx.get("gasUsed", 0) * backrun_tx.get("gasPrice", 0)
        
        attack = MEVAttack(
            type=MEVType.SANDWICH,
            severity="high",
            description="Sandwich attack detected: victim trade was front-run and back-run",
            attacker=frontrun_tx.get("from"),
            victim=victim_tx.get("from"),
            transactions=[
                frontrun_tx.get("hash", ""),
                victim_tx.get("hash", ""),
                backrun_tx.get("hash", "")
            ],
            block_number=victim_tx.get("blockNumber"),
            gas_used=frontrun_gas + backrun_gas,
            recommendations=[
                "Use private transaction pools (Flashbots Protect, MEV Blocker)",
                "Set tight slippage tolerance",
                "Use DEX aggregators with MEV protection",
                "Consider breaking large trades into smaller amounts"
            ]
        )
        
        self.detected_attacks.append(attack)
        return attack
    
    def detect_frontrun(self, pending_tx: Dict, confirmed_tx: Dict) -> Optional[MEVAttack]:
        """
        Detect frontrunning by comparing pending vs confirmed transactions.
        """
        # Check if confirmed tx was inserted before pending tx
        if confirmed_tx.get("index", 0) < pending_tx.get("index", 0):
            # Check if same function call
            if confirmed_tx.get("input", "")[:10] == pending_tx.get("input", "")[:10]:
                # Check if different sender
                if confirmed_tx.get("from") != pending_tx.get("from"):
                    attack = MEVAttack(
                        type=MEVType.FRONTRUN,
                        severity="high",
                        description="Transaction was front-run by MEV bot",
                        attacker=confirmed_tx.get("from"),
                        victim=pending_tx.get("from"),
                        transactions=[
                            confirmed_tx.get("hash", ""),
                            pending_tx.get("hash", "")
                        ],
                        block_number=confirmed_tx.get("blockNumber"),
                        recommendations=[
                            "Use private mempools",
                            "Implement commit-reveal schemes",
                            "Use Flashbots Protect for transaction submission"
                        ]
                    )
                    self.detected_attacks.append(attack)
                    return attack
        return None
    
    def detect_flash_loan(self, tx: Dict) -> Optional[FlashLoanUsage]:
        """
        Detect flash loan usage in a transaction.
        """
        input_data = tx.get("input", "")
        
        # Check for flash loan signatures
        for sig, (provider, func) in self.FLASH_LOAN_SIGS.items():
            if input_data.startswith(sig):
                # Analyze internal traces if available
                traces = tx.get("traces", [])
                
                # Look for signs of attack
                is_attack = self._analyze_flash_loan_traces(traces)
                
                flash_loan = FlashLoanUsage(
                    provider=FlashLoanProvider[provider.replace(" ", "_").upper()],
                    amount=self._extract_amount(input_data),
                    token=self._extract_token(input_data),
                    fee=self._calculate_fee(provider, self._extract_amount(input_data)),
                    is_attack=is_attack,
                    attack_type="oracle_manipulation" if is_attack else None,
                    affected_protocols=self._find_affected_protocols(traces)
                )
                
                self.flash_loans.append(flash_loan)
                return flash_loan
        
        return None
    
    def detect_jit_liquidity(
        self,
        add_liq_tx: Dict,
        swap_tx: Dict,
        remove_liq_tx: Dict
    ) -> Optional[MEVAttack]:
        """
        Detect Just-In-Time (JIT) liquidity attack.
        
        JIT Liquidity:
        1. Add liquidity just before large swap
        2. Capture swap fees
        3. Remove liquidity immediately after
        """
        # Check sequence
        if not (add_liq_tx.get("index", 0) < swap_tx.get("index", 0) < remove_liq_tx.get("index", 0)):
            return None
        
        # Check same block
        if not (add_liq_tx.get("blockNumber") == swap_tx.get("blockNumber") == remove_liq_tx.get("blockNumber")):
            return None
        
        # Check same attacker
        if add_liq_tx.get("from") != remove_liq_tx.get("from"):
            return None
        
        attack = MEVAttack(
            type=MEVType.JIT_LIQUIDITY,
            severity="medium",
            description="JIT Liquidity attack: liquidity was added just before swap and removed after",
            attacker=add_liq_tx.get("from"),
            victim=swap_tx.get("from"),
            transactions=[
                add_liq_tx.get("hash", ""),
                swap_tx.get("hash", ""),
                remove_liq_tx.get("hash", "")
            ],
            block_number=swap_tx.get("blockNumber"),
            recommendations=[
                "This is a form of MEV extraction that may not be preventable",
                "Consider using protocols with JIT protection",
                "Use private transaction submission"
            ]
        )
        
        self.detected_attacks.append(attack)
        return attack
    
    def analyze_block_for_mev(self, block: Dict) -> List[MEVAttack]:
        """
        Analyze an entire block for MEV extraction.
        """
        attacks = []
        transactions = block.get("transactions", [])
        
        # Sort by index
        transactions.sort(key=lambda x: x.get("index", 0))
        
        # Look for sandwich patterns
        for i in range(len(transactions) - 2):
            sandwich = self.detect_sandwich_attack(
                transactions[i],
                transactions[i + 1],
                transactions[i + 2]
            )
            if sandwich:
                attacks.append(sandwich)
        
        # Look for flash loans
        for tx in transactions:
            flash_loan = self.detect_flash_loan(tx)
            if flash_loan and flash_loan.is_attack:
                attacks.append(MEVAttack(
                    type=MEVType.ARBITRAGE,
                    severity="critical" if flash_loan.is_attack else "info",
                    description=f"Flash loan attack via {flash_loan.provider.value}",
                    transactions=[tx.get("hash", "")],
                    block_number=block.get("number"),
                    recommendations=[
                        "Use TWAP oracles instead of spot prices",
                        "Implement flash loan guards",
                        "Add minimum time between price updates"
                    ]
                ))
        
        return attacks
    
    def _analyze_flash_loan_traces(self, traces: List[Dict]) -> bool:
        """Analyze traces to determine if flash loan was used for attack."""
        # Look for suspicious patterns
        swap_count = 0
        oracle_calls = 0
        
        for trace in traces:
            input_data = trace.get("input", "")
            
            # Count swaps
            if any(sig in input_data for sig in ["0x38ed1739", "0x022c0d9f"]):
                swap_count += 1
            
            # Count oracle calls
            if any(sig in input_data for sig in ["0xfeaf968c", "0x50d25bcd"]):  # latestRoundData, latestAnswer
                oracle_calls += 1
        
        # Attack likely if multiple swaps + oracle interaction
        return swap_count >= 2 and oracle_calls >= 1
    
    def _extract_amount(self, input_data: str) -> int:
        """Extract loan amount from calldata."""
        if len(input_data) >= 138:
            try:
                return int(input_data[74:138], 16)
            except ValueError:
                return 0
        return 0
    
    def _extract_token(self, input_data: str) -> str:
        """Extract token address from calldata."""
        if len(input_data) >= 74:
            return "0x" + input_data[34:74]
        return ""
    
    def _calculate_fee(self, provider: str, amount: int) -> int:
        """Calculate flash loan fee based on provider."""
        fee_rates = {
            "AAVE V2": 9,      # 0.09%
            "AAVE V3": 5,      # 0.05%
            "Balancer": 0,     # 0%
            "dYdX": 0,         # 0%
            "Uniswap V2": 30,  # 0.3%
        }
        rate = fee_rates.get(provider, 0)
        return (amount * rate) // 10000
    
    def _find_affected_protocols(self, traces: List[Dict]) -> List[str]:
        """Find which protocols were affected by the flash loan."""
        protocols = set()
        
        for trace in traces:
            to_addr = trace.get("to", "").lower()
            if to_addr in self.DEX_ROUTERS:
                protocols.add(self.DEX_ROUTERS[to_addr])
        
        return list(protocols)
    
    def get_protection_recommendations(self, attack_type: MEVType) -> List[str]:
        """Get protection recommendations for specific attack type."""
        recommendations = {
            MEVType.SANDWICH: [
                "Use Flashbots Protect (rpc.flashbots.net)",
                "Use MEV Blocker (mevblocker.io)",
                "Set slippage to 0.1-0.5% for liquid pairs",
                "Avoid large trades in a single transaction",
                "Use limit orders instead of market orders",
            ],
            MEVType.FRONTRUN: [
                "Use commit-reveal scheme",
                "Submit transactions via private mempool",
                "Use submarine sends for sensitive operations",
                "Implement minimum delay between actions",
            ],
            MEVType.JIT_LIQUIDITY: [
                "Use concentrated liquidity positions",
                "Set fee tiers appropriately",
                "Consider using protocols with JIT protection",
            ],
            MEVType.ARBITRAGE: [
                "Use TWAP oracles with 30+ minute windows",
                "Implement circuit breakers for price deviation",
                "Add cooldown periods between operations",
            ],
            MEVType.LIQUIDATION: [
                "Keep positions well-collateralized",
                "Use protocols with gradual liquidation",
                "Monitor health factor continuously",
            ],
        }
        return recommendations.get(attack_type, [])
    
    def analyze_transaction(self, tx: Dict) -> Dict:
        """
        Analyze a single transaction for MEV indicators.
        """
        result = {
            "is_mev_target": False,
            "is_mev_bot": False,
            "risk": "low",
            "indicators": [],
        }
        
        # Check if sender is known MEV bot
        sender = tx.get("from", "").lower()
        if sender in [addr.lower() for addr in self.MEV_BOTS.keys()]:
            result["is_mev_bot"] = True
            result["risk"] = "high"
            result["indicators"].append("Known MEV bot address")
        
        # Check if targeting DEX router
        to_addr = tx.get("to", "").lower()
        if to_addr in [addr.lower() for addr in self.DEX_ROUTERS.keys()]:
            result["is_mev_target"] = True
            result["indicators"].append(f"Targets DEX: {self.DEX_ROUTERS.get(to_addr, 'Unknown')}")
        
        # Check gas price (high gas = likely MEV)
        gas_price = tx.get("gasPrice", 0)
        if gas_price > 100 * 10**9:  # > 100 gwei
            result["risk"] = "medium" if result["risk"] == "low" else result["risk"]
            result["indicators"].append("High gas price (potential priority gas auction)")
        
        # Check for swap signatures
        input_data = tx.get("input", "")
        swap_sigs = ["0x38ed1739", "0x7ff36ab5", "0x18cbafe5", "0xfb3bdb41", "0x022c0d9f"]
        if any(input_data.startswith(sig) for sig in swap_sigs):
            result["is_mev_target"] = True
            result["indicators"].append("Contains swap operation")
        
        # Check for flash loan
        for sig in self.FLASH_LOAN_SIGS.keys():
            if input_data.startswith(sig):
                result["indicators"].append("Flash loan detected")
                result["risk"] = "high"
        
        return result
    
    def is_known_mev_bot(self, address: str) -> bool:
        """Check if address is a known MEV bot."""
        return address.lower() in [addr.lower() for addr in self.MEV_BOTS.keys()]
    
    def generate_report(self) -> Dict:
        """Generate MEV analysis report."""
        return {
            "total_attacks_detected": len(self.detected_attacks),
            "attacks_by_type": {
                mev_type.value: len([a for a in self.detected_attacks if a.type == mev_type])
                for mev_type in MEVType
            },
            "flash_loans_detected": len(self.flash_loans),
            "malicious_flash_loans": len([f for f in self.flash_loans if f.is_attack]),
            "affected_protocols": list(set(
                protocol
                for fl in self.flash_loans
                for protocol in fl.affected_protocols
            )),
            "recommendations": list(set(
                rec
                for attack in self.detected_attacks
                for rec in attack.recommendations
            ))
        }


class SandwichSimulator:
    """
    Simulate sandwich attacks to test vulnerability.
    """
    
    def __init__(self, rpc_url: str = ""):
        self.rpc_url = rpc_url
    
    def simulate_attack(
        self,
        target_tx: Dict,
        pool_address: str,
        attacker_capital: int
    ) -> Dict:
        """
        Simulate a sandwich attack on a pending transaction.
        Returns expected profit and impact.
        """
        # This would normally fork the blockchain and simulate
        # For now, return estimated values
        
        victim_amount = target_tx.get("value", 0)
        
        # Estimate price impact
        price_impact = self._estimate_price_impact(victim_amount, attacker_capital)
        
        # Estimate profit
        estimated_profit = (victim_amount * price_impact) // 100
        gas_cost = 400000 * 50 * 10**9  # 400k gas at 50 gwei
        
        net_profit = estimated_profit - gas_cost
        
        return {
            "is_profitable": net_profit > 0,
            "estimated_profit": estimated_profit,
            "gas_cost": gas_cost,
            "net_profit": net_profit,
            "price_impact_bps": price_impact,
            "victim_loss": estimated_profit,
            "recommendation": "Vulnerable to sandwich" if net_profit > 0 else "Not profitable to sandwich"
        }
    
    def _estimate_price_impact(self, trade_size: int, liquidity: int) -> int:
        """Estimate price impact in basis points."""
        if liquidity == 0:
            return 0
        # Simplified constant product formula
        impact = (trade_size * 10000) // liquidity
        return min(impact, 5000)  # Cap at 50%


if __name__ == "__main__":
    detector = MEVDetector()
    print("SENTINEL MEV Detector")
    print("=" * 50)
    print(f"Known MEV Bots: {len(detector.MEV_BOTS)}")
    print(f"Flash Loan Signatures: {len(detector.FLASH_LOAN_SIGS)}")
    print(f"DEX Routers: {len(detector.DEX_ROUTERS)}")
