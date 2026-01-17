#!/usr/bin/env python3
"""
 ██████╗ ███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗
██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║
███████╗ █████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║
╚════██║ ██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║
███████║ ███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
╚══════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝

SENTINEL SHIELD - Free API Finder & Tester
Trova tutte le API gratuite per scan di approvazioni EVM

Author: SENTINEL Team
"""

import asyncio
import aiohttp
import json
import time
from dataclasses import dataclass
from typing import Optional, List, Dict

# ═══════════════════════════════════════════════════════════════════════════════
#                           FREE API PROVIDERS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class APIProvider:
    name: str
    base_url: str
    api_key: Optional[str]
    rate_limit: str
    chains: List[str]
    free_tier: str
    status: str = "unknown"
    response_time: float = 0

# 🆓 FREE RPC ENDPOINTS (No API key needed!)
FREE_RPCS = {
    # Ethereum & L2s
    "ethereum": [
        "https://eth.llamarpc.com",
        "https://rpc.ankr.com/eth",
        "https://ethereum.publicnode.com",
        "https://1rpc.io/eth",
        "https://eth.drpc.org",
        "https://rpc.payload.de",
    ],
    "arbitrum": [
        "https://arb1.arbitrum.io/rpc",
        "https://arbitrum.llamarpc.com",
        "https://rpc.ankr.com/arbitrum",
        "https://arbitrum-one.publicnode.com",
        "https://1rpc.io/arb",
    ],
    "optimism": [
        "https://mainnet.optimism.io",
        "https://optimism.llamarpc.com",
        "https://rpc.ankr.com/optimism",
        "https://optimism.publicnode.com",
        "https://1rpc.io/op",
    ],
    "base": [
        "https://mainnet.base.org",
        "https://base.llamarpc.com",
        "https://rpc.ankr.com/base",
        "https://base.publicnode.com",
        "https://1rpc.io/base",
    ],
    "polygon": [
        "https://polygon-rpc.com",
        "https://polygon.llamarpc.com",
        "https://rpc.ankr.com/polygon",
        "https://polygon-bor.publicnode.com",
        "https://1rpc.io/matic",
    ],
    "bsc": [
        "https://bsc-dataseed.binance.org",
        "https://bsc-dataseed1.defibit.io",
        "https://rpc.ankr.com/bsc",
        "https://bsc.publicnode.com",
        "https://1rpc.io/bnb",
    ],
    "avalanche": [
        "https://api.avax.network/ext/bc/C/rpc",
        "https://avalanche.llamarpc.com",
        "https://rpc.ankr.com/avalanche",
        "https://avalanche-c-chain.publicnode.com",
        "https://1rpc.io/avax/c",
    ],
    "fantom": [
        "https://rpcapi.fantom.network",
        "https://fantom.llamarpc.com",
        "https://rpc.ankr.com/fantom",
        "https://fantom.publicnode.com",
        "https://1rpc.io/ftm",
    ],
    "zksync": [
        "https://mainnet.era.zksync.io",
        "https://zksync.drpc.org",
        "https://1rpc.io/zksync2-era",
    ],
    "linea": [
        "https://rpc.linea.build",
        "https://linea.drpc.org",
        "https://1rpc.io/linea",
    ],
    "scroll": [
        "https://rpc.scroll.io",
        "https://scroll.drpc.org",
        "https://1rpc.io/scroll",
    ],
    "gnosis": [
        "https://rpc.gnosischain.com",
        "https://gnosis.drpc.org",
        "https://rpc.ankr.com/gnosis",
        "https://1rpc.io/gnosis",
    ],
    "celo": [
        "https://forno.celo.org",
        "https://rpc.ankr.com/celo",
        "https://1rpc.io/celo",
    ],
    "moonbeam": [
        "https://rpc.api.moonbeam.network",
        "https://moonbeam.publicnode.com",
        "https://1rpc.io/glmr",
    ],
    "cronos": [
        "https://evm.cronos.org",
        "https://cronos.drpc.org",
    ],
    "zkevm": [
        "https://zkevm-rpc.com",
        "https://polygon-zkevm.drpc.org",
        "https://1rpc.io/polygon/zkevm",
    ],
}

# 🔑 FREE API KEYS (registrazione gratuita)
FREE_API_PROVIDERS = [
    APIProvider(
        name="Alchemy",
        base_url="https://{chain}-mainnet.g.alchemy.com/v2/{key}",
        api_key=None,  # Get free key at: https://dashboard.alchemy.com
        rate_limit="300 req/sec (free tier)",
        chains=["ethereum", "arbitrum", "optimism", "base", "polygon", "zksync"],
        free_tier="300M compute units/month FREE"
    ),
    APIProvider(
        name="Infura",
        base_url="https://{chain}.infura.io/v3/{key}",
        api_key=None,  # Get free key at: https://infura.io
        rate_limit="100K req/day",
        chains=["ethereum", "arbitrum", "optimism", "polygon", "avalanche", "linea"],
        free_tier="100K requests/day FREE"
    ),
    APIProvider(
        name="QuickNode",
        base_url="https://{subdomain}.quiknode.pro/{key}",
        api_key=None,  # Get free key at: https://quicknode.com
        rate_limit="25 req/sec",
        chains=["ethereum", "arbitrum", "optimism", "base", "polygon", "bsc", "avalanche"],
        free_tier="10M API credits/month FREE"
    ),
    APIProvider(
        name="Ankr",
        base_url="https://rpc.ankr.com/{chain}",
        api_key=None,  # No key needed for public endpoint!
        rate_limit="30 req/sec",
        chains=["ethereum", "arbitrum", "optimism", "base", "polygon", "bsc", "avalanche", "fantom", "gnosis", "celo"],
        free_tier="Unlimited FREE (public endpoint)"
    ),
    APIProvider(
        name="LlamaNodes",
        base_url="https://{chain}.llamarpc.com",
        api_key=None,  # No key needed!
        rate_limit="50 req/sec",
        chains=["ethereum", "arbitrum", "optimism", "base", "polygon", "bsc", "avalanche", "fantom"],
        free_tier="Unlimited FREE"
    ),
    APIProvider(
        name="PublicNode",
        base_url="https://{chain}.publicnode.com",
        api_key=None,  # No key needed!
        rate_limit="Unlimited",
        chains=["ethereum", "arbitrum", "optimism", "base", "polygon", "bsc", "avalanche", "fantom", "gnosis"],
        free_tier="Unlimited FREE"
    ),
    APIProvider(
        name="1RPC",
        base_url="https://1rpc.io/{chain}",
        api_key=None,  # No key needed! Privacy-focused
        rate_limit="Unlimited",
        chains=["ethereum", "arbitrum", "optimism", "base", "polygon", "bsc", "avalanche", "fantom", "zksync", "linea", "scroll", "gnosis", "celo", "moonbeam"],
        free_tier="Unlimited FREE + Privacy Protection"
    ),
    APIProvider(
        name="DRPC",
        base_url="https://{chain}.drpc.org",
        api_key=None,  # No key needed!
        rate_limit="Unlimited",
        chains=["ethereum", "arbitrum", "optimism", "base", "polygon", "bsc", "zksync", "linea", "scroll", "gnosis", "cronos", "zkevm"],
        free_tier="Unlimited FREE"
    ),
    APIProvider(
        name="Chainstack",
        base_url="https://{chain}-mainnet.core.chainstack.com/{key}",
        api_key=None,  # Get free key at: https://chainstack.com
        rate_limit="25 req/sec",
        chains=["ethereum", "arbitrum", "optimism", "polygon", "bsc", "avalanche", "fantom", "gnosis"],
        free_tier="3M req/month FREE"
    ),
    APIProvider(
        name="GetBlock",
        base_url="https://{chain}.getblock.io/mainnet/?api_key={key}",
        api_key=None,  # Get free key at: https://getblock.io
        rate_limit="60 req/sec",
        chains=["ethereum", "arbitrum", "optimism", "polygon", "bsc", "avalanche", "fantom"],
        free_tier="40K req/day FREE"
    ),
    APIProvider(
        name="Blast API",
        base_url="https://{chain}-mainnet.blastapi.io/{key}",
        api_key=None,  # Get free key at: https://blastapi.io
        rate_limit="25 req/sec",
        chains=["ethereum", "arbitrum", "optimism", "polygon", "bsc", "avalanche", "fantom", "gnosis", "moonbeam"],
        free_tier="12M req/month FREE"
    ),
    APIProvider(
        name="BlockPi",
        base_url="https://{chain}.blockpi.network/v1/rpc/{key}",
        api_key=None,  # Get free key at: https://blockpi.io
        rate_limit="20 req/sec",
        chains=["ethereum", "arbitrum", "optimism", "base", "polygon", "bsc", "avalanche", "zksync", "linea", "scroll"],
        free_tier="100M req/month FREE"
    ),
]

# 🔍 BLOCK EXPLORERS (per API di logs/approvals)
BLOCK_EXPLORER_APIS = {
    "ethereum": {
        "explorer": "Etherscan",
        "api": "https://api.etherscan.io/api",
        "free_key": "https://etherscan.io/register",
        "rate_limit": "5 req/sec (free)",
    },
    "arbitrum": {
        "explorer": "Arbiscan",
        "api": "https://api.arbiscan.io/api",
        "free_key": "https://arbiscan.io/register",
        "rate_limit": "5 req/sec (free)",
    },
    "optimism": {
        "explorer": "Optimistic Etherscan",
        "api": "https://api-optimistic.etherscan.io/api",
        "free_key": "https://optimistic.etherscan.io/register",
        "rate_limit": "5 req/sec (free)",
    },
    "base": {
        "explorer": "BaseScan",
        "api": "https://api.basescan.org/api",
        "free_key": "https://basescan.org/register",
        "rate_limit": "5 req/sec (free)",
    },
    "polygon": {
        "explorer": "PolygonScan",
        "api": "https://api.polygonscan.com/api",
        "free_key": "https://polygonscan.com/register",
        "rate_limit": "5 req/sec (free)",
    },
    "bsc": {
        "explorer": "BscScan",
        "api": "https://api.bscscan.com/api",
        "free_key": "https://bscscan.com/register",
        "rate_limit": "5 req/sec (free)",
    },
    "avalanche": {
        "explorer": "SnowTrace",
        "api": "https://api.snowtrace.io/api",
        "free_key": "https://snowtrace.io/register",
        "rate_limit": "5 req/sec (free)",
    },
    "fantom": {
        "explorer": "FTMScan",
        "api": "https://api.ftmscan.com/api",
        "free_key": "https://ftmscan.com/register",
        "rate_limit": "5 req/sec (free)",
    },
    "gnosis": {
        "explorer": "GnosisScan",
        "api": "https://api.gnosisscan.io/api",
        "free_key": "https://gnosisscan.io/register",
        "rate_limit": "5 req/sec (free)",
    },
    "linea": {
        "explorer": "LineaScan",
        "api": "https://api.lineascan.build/api",
        "free_key": "https://lineascan.build/register",
        "rate_limit": "5 req/sec (free)",
    },
    "scroll": {
        "explorer": "ScrollScan",
        "api": "https://api.scrollscan.com/api",
        "free_key": "https://scrollscan.com/register",
        "rate_limit": "5 req/sec (free)",
    },
    "zksync": {
        "explorer": "zkSync Explorer",
        "api": "https://block-explorer-api.mainnet.zksync.io/api",
        "free_key": "No key needed",
        "rate_limit": "Unlimited",
    },
    "moonbeam": {
        "explorer": "Moonscan",
        "api": "https://api-moonbeam.moonscan.io/api",
        "free_key": "https://moonscan.io/register",
        "rate_limit": "5 req/sec (free)",
    },
    "celo": {
        "explorer": "CeloScan",
        "api": "https://api.celoscan.io/api",
        "free_key": "https://celoscan.io/register",
        "rate_limit": "5 req/sec (free)",
    },
    "cronos": {
        "explorer": "CronoScan",
        "api": "https://api.cronoscan.com/api",
        "free_key": "https://cronoscan.com/register",
        "rate_limit": "5 req/sec (free)",
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
#                           RPC TESTER
# ═══════════════════════════════════════════════════════════════════════════════

async def test_rpc(session: aiohttp.ClientSession, chain: str, rpc_url: str) -> Dict:
    """Test an RPC endpoint for speed and availability"""
    try:
        start = time.time()
        async with session.post(
            rpc_url,
            json={
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1
            },
            timeout=aiohttp.ClientTimeout(total=5)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                if "result" in data:
                    response_time = (time.time() - start) * 1000
                    return {
                        "chain": chain,
                        "url": rpc_url,
                        "status": "✅ OK",
                        "response_time_ms": round(response_time, 1),
                        "block": int(data["result"], 16)
                    }
            return {"chain": chain, "url": rpc_url, "status": "❌ Error", "response_time_ms": 0}
    except Exception as e:
        return {"chain": chain, "url": rpc_url, "status": f"❌ {str(e)[:30]}", "response_time_ms": 0}


async def test_all_rpcs():
    """Test all free RPCs and find the fastest ones"""
    print("\n" + "="*80)
    print("🔍 TESTING FREE RPC ENDPOINTS")
    print("="*80)
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for chain, urls in FREE_RPCS.items():
            for url in urls:
                tasks.append(test_rpc(session, chain, url))
        
        results = await asyncio.gather(*tasks)
    
    # Group by chain and sort by speed
    by_chain: Dict[str, List[Dict]] = {}
    for result in results:
        chain = result["chain"]
        if chain not in by_chain:
            by_chain[chain] = []
        by_chain[chain].append(result)
    
    # Print fastest per chain
    print("\n🏆 FASTEST FREE RPCs PER CHAIN:")
    print("-"*80)
    
    fastest_config = {}
    
    for chain in sorted(by_chain.keys()):
        working = [r for r in by_chain[chain] if "OK" in r["status"]]
        if working:
            fastest = min(working, key=lambda x: x["response_time_ms"])
            fastest_config[chain] = fastest["url"]
            print(f"  {chain:12} | {fastest['response_time_ms']:6.1f}ms | {fastest['url']}")
        else:
            print(f"  {chain:12} | ❌ No working RPCs found")
    
    return fastest_config


def print_api_providers():
    """Print all free API providers"""
    print("\n" + "="*80)
    print("🆓 FREE API PROVIDERS FOR EVM SCANNING")
    print("="*80)
    
    for provider in FREE_API_PROVIDERS:
        print(f"\n📌 {provider.name}")
        print(f"   Rate Limit: {provider.rate_limit}")
        print(f"   Free Tier:  {provider.free_tier}")
        print(f"   Chains:     {', '.join(provider.chains)}")
        if provider.api_key is None:
            print(f"   API Key:    🔓 NO KEY NEEDED (public)")
        else:
            print(f"   API Key:    Get free at provider website")


def print_explorer_apis():
    """Print all block explorer APIs"""
    print("\n" + "="*80)
    print("🔍 BLOCK EXPLORER APIs (for approval logs)")
    print("="*80)
    
    for chain, info in BLOCK_EXPLORER_APIS.items():
        print(f"\n  {chain:12} | {info['explorer']}")
        print(f"               | API: {info['api']}")
        print(f"               | Rate: {info['rate_limit']}")


def generate_go_config(fastest_rpcs: Dict[str, str]):
    """Generate Go config for the fastest RPCs"""
    print("\n" + "="*80)
    print("📝 GO CONFIG (copy to main.go)")
    print("="*80)
    
    print("""
// FREE RPCs - Fastest endpoints (no API key needed!)
var freeRPCs = map[string][]string{""")
    
    for chain, urls in FREE_RPCS.items():
        urls_str = ', '.join(f'"{url}"' for url in urls[:3])  # Top 3
        print(f'\t"{chain}": {{{urls_str}}},')
    
    print("}")
    
    print("""
// Fastest RPC per chain (auto-tested)
var fastestRPCs = map[string]string{""")
    
    for chain, url in fastest_rpcs.items():
        print(f'\t"{chain}": "{url}",')
    
    print("}")


async def main():
    print("""
 ██████╗ ███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗
██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║
███████╗ █████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║
╚════██║ ██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║
███████║ ███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
╚══════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝

              FREE API FINDER & SPEED TESTER
    """)
    
    # 1. Print API providers
    print_api_providers()
    
    # 2. Print explorer APIs
    print_explorer_apis()
    
    # 3. Test all RPCs for speed
    fastest = await test_all_rpcs()
    
    # 4. Generate Go config
    generate_go_config(fastest)
    
    print("\n" + "="*80)
    print("✅ DONE! Use the fastest RPCs in your Go server")
    print("="*80)
    
    # Save results to JSON
    results = {
        "fastest_rpcs": fastest,
        "all_rpcs": FREE_RPCS,
        "api_providers": [
            {
                "name": p.name,
                "rate_limit": p.rate_limit,
                "free_tier": p.free_tier,
                "chains": p.chains
            }
            for p in FREE_API_PROVIDERS
        ],
        "explorer_apis": BLOCK_EXPLORER_APIS
    }
    
    with open("free_apis_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n📁 Results saved to: free_apis_results.json")


if __name__ == "__main__":
    asyncio.run(main())
