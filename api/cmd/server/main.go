/*
 ██████╗ ███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗
██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║
███████╗ █████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║
╚════██║ ██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║
███████║ ███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
╚══════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝

SENTINEL SHIELD - Multi-chain Wallet Security Scanner
API Server (Go)

Author: SENTINEL Team
*/

package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math/big"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"sync"
	"syscall"
	"time"
)

// loadEnvFile loads environment variables from a .env file
func loadEnvFile(path string) error {
	file, err := os.Open(path)
	if err != nil {
		return err
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		// Skip empty lines and comments
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		// Parse KEY=VALUE
		parts := strings.SplitN(line, "=", 2)
		if len(parts) == 2 {
			key := strings.TrimSpace(parts[0])
			value := strings.TrimSpace(parts[1])
			// Only set if not already set (env vars take precedence)
			if os.Getenv(key) == "" {
				os.Setenv(key, value)
			}
		}
	}
	return scanner.Err()
}

// loadEnv tries to load .env from multiple locations - MUST be called before any config init
var _ = loadEnv()

func loadEnv() bool {
	envPaths := []string{
		"../../config/.env", // From cmd/server/
		"../config/.env",    // From api/
		"config/.env",       // From project root
		".env",              // Current directory
		"C:/Users/Utente/Desktop/project/SENTINEL/config/.env", // Absolute path
	}

	// Also try absolute path based on executable location
	if exe, err := os.Executable(); err == nil {
		exeDir := filepath.Dir(exe)
		envPaths = append(envPaths,
			filepath.Join(exeDir, "../../config/.env"),
			filepath.Join(exeDir, "../../../config/.env"),
		)
	}

	for _, path := range envPaths {
		if err := loadEnvFile(path); err == nil {
			log.Printf("📁 Loaded environment from %s", path)
			return true
		}
	}
	return false
}

// ═══════════════════════════════════════════════════════════════════════════════
//                              CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

type Config struct {
	Port     string
	RPC      map[string]string
	CacheTTL time.Duration
}

// getEnv returns environment variable or default value
func getEnv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

// Initialize config from environment variables
func initConfig() Config {
	alchemyKey := getEnv("ALCHEMY_API_KEY", "demo") // Use env var!
	return Config{
		Port: getEnv("PORT", "8080"),
		RPC: map[string]string{
			// 🔵 Ethereum & L2s (Alchemy) - API key from environment
			"ethereum": "https://eth-mainnet.g.alchemy.com/v2/" + alchemyKey,
			"arbitrum": "https://arb-mainnet.g.alchemy.com/v2/" + alchemyKey,
			"optimism": "https://opt-mainnet.g.alchemy.com/v2/" + alchemyKey,
			"base":     "https://base-mainnet.g.alchemy.com/v2/" + alchemyKey,
			"zksync":   "https://mainnet.era.zksync.io",
			"linea":    "https://rpc.linea.build",
			"scroll":   "https://rpc.scroll.io",
			"zkevm":    "https://zkevm-rpc.com",
			// 🟡 Alt L1s
			"bsc":       "https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3",
			"polygon":   "https://polygon-rpc.com",
			"avalanche": "https://api.avax.network/ext/bc/C/rpc",
			"fantom":    "https://rpcapi.fantom.network",
			"cronos":    "https://evm.cronos.org",
			"gnosis":    "https://rpc.gnosischain.com",
			"celo":      "https://forno.celo.org",
			"moonbeam":  "https://rpc.api.moonbeam.network",
		},
		CacheTTL: 5 * time.Minute,
	}
}

// Global config instance
var config = initConfig()

// EtherscanConfig holds Etherscan API configuration
type EtherscanConfig struct {
	APIKey   string
	ChainIDs map[string]int
}

// Initialize Etherscan config
func initEtherscanConfig() EtherscanConfig {
	return EtherscanConfig{
		APIKey: getEnv("ETHERSCAN_API_KEY", ""), // Load from environment!
		ChainIDs: map[string]int{
			// Supported on Etherscan v2 free tier
			"ethereum": 1,
			"arbitrum": 42161,
			"optimism": 10,
			"polygon":  137,
			"gnosis":   100,
			"linea":    59144,
			"scroll":   534352,
			"zksync":   324,
			"zkevm":    1101,
			"celo":     42220,
			"moonbeam": 1284,
		},
	}
}

var etherscanConfig = initEtherscanConfig()

// AlchemyConfig holds Alchemy API configuration
type AlchemyConfig struct {
	APIKey    string
	Endpoints map[string]string
}

// Initialize Alchemy config
func initAlchemyConfig() AlchemyConfig {
	apiKey := getEnv("ALCHEMY_API_KEY", "demo")
	return AlchemyConfig{
		APIKey: apiKey,
		Endpoints: map[string]string{
			"ethereum": "https://eth-mainnet.g.alchemy.com/v2/" + apiKey,
			"arbitrum": "https://arb-mainnet.g.alchemy.com/v2/" + apiKey,
			"optimism": "https://opt-mainnet.g.alchemy.com/v2/" + apiKey,
			"base":     "https://base-mainnet.g.alchemy.com/v2/" + apiKey,
			"polygon":  "https://polygon-mainnet.g.alchemy.com/v2/" + apiKey,
		},
	}
}

var alchemyConfig = initAlchemyConfig()

// ═══════════════════════════════════════════════════════════════════════════════
//                                  TYPES
// ═══════════════════════════════════════════════════════════════════════════════

// ChainID enum
type ChainID string

const (
	// Ethereum & L2s
	Ethereum ChainID = "ethereum"
	Arbitrum ChainID = "arbitrum"
	Optimism ChainID = "optimism"
	Base     ChainID = "base"
	ZkSync   ChainID = "zksync"
	Linea    ChainID = "linea"
	Scroll   ChainID = "scroll"
	ZkEVM    ChainID = "zkevm"
	// Alt L1s
	BSC       ChainID = "bsc"
	Polygon   ChainID = "polygon"
	Avalanche ChainID = "avalanche"
	Fantom    ChainID = "fantom"
	Cronos    ChainID = "cronos"
	Gnosis    ChainID = "gnosis"
	Celo      ChainID = "celo"
	Moonbeam  ChainID = "moonbeam"
)

var AllChains = []ChainID{
	// Ethereum ecosystem
	Ethereum, Arbitrum, Optimism, Base, ZkSync, Linea, Scroll, ZkEVM,
	// Alt L1s
	BSC, Polygon, Avalanche, Fantom, Cronos, Gnosis, Celo, Moonbeam,
}

// Approval represents a token approval
type Approval struct {
	Chain          ChainID  `json:"chain"`
	TokenAddress   string   `json:"tokenAddress"`
	TokenSymbol    string   `json:"tokenSymbol"`
	SpenderAddress string   `json:"spenderAddress"`
	SpenderName    string   `json:"spenderName"`
	AllowanceRaw   string   `json:"allowanceRaw"`
	AllowanceHuman string   `json:"allowanceHuman"`
	IsUnlimited    bool     `json:"isUnlimited"`
	RiskLevel      string   `json:"riskLevel"` // "critical", "warning", "safe"
	RiskReasons    []string `json:"riskReasons"`
	LastUpdated    int64    `json:"lastUpdated"`
}

// ContractRisk represents analyzed contract risk
type ContractRisk struct {
	Address         string   `json:"address"`
	Chain           ChainID  `json:"chain"`
	IsVerified      bool     `json:"isVerified"`
	IsProxy         bool     `json:"isProxy"`
	HasMint         bool     `json:"hasMint"`
	HasBlacklist    bool     `json:"hasBlacklist"`
	HasPause        bool     `json:"hasPause"`
	IsHoneypot      bool     `json:"isHoneypot"`
	HiddenFee       float64  `json:"hiddenFee"`
	OwnerPrivileges []string `json:"ownerPrivileges"`
	RiskScore       int      `json:"riskScore"` // 0-100
	RiskLevel       string   `json:"riskLevel"`
	Vulnerabilities []string `json:"vulnerabilities"`
}

// WalletScan represents full wallet scan result
type WalletScanResult struct {
	WalletAddress    string         `json:"walletAddress"`
	ScanTimestamp    int64          `json:"scanTimestamp"`
	OverallRiskScore int            `json:"overallRiskScore"`
	TotalApprovals   int            `json:"totalApprovals"`
	CriticalRisks    int            `json:"criticalRisks"`
	Warnings         int            `json:"warnings"`
	ChainsScanned    []ChainID      `json:"chainsScanned"`
	Approvals        []Approval     `json:"approvals"`
	ContractRisks    []ContractRisk `json:"contractRisks"`
	Recommendations  []string       `json:"recommendations"`
}

// ═══════════════════════════════════════════════════════════════════════════════
//                              CHAIN CLIENT
// ═══════════════════════════════════════════════════════════════════════════════

// Known spenders database - DEXs, bridges, protocols
// ✅ = Safe, trusted protocol
var knownSpenders = map[string]string{
	// ═══════════════════════════════════════════════════════════════════════════
	// UNISWAP ECOSYSTEM
	// ═══════════════════════════════════════════════════════════════════════════
	"0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "✅ Uniswap V3: Router 2",
	"0xe592427a0aece92de3edee1f18e0157c05861564": "✅ Uniswap V3: Router",
	"0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "✅ Uniswap V2: Router",
	"0x000000000022d473030f116ddee9f6b43ac78ba3": "✅ Uniswap: Permit2",
	"0xef1c6e67703c7bd7107eed8303fbe6ec2554bf6b": "✅ Uniswap: Universal Router",
	"0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad": "✅ Uniswap: Universal Router 2",
	"0x4c60051384bd2d3c01bfc845cf5f4b44bcbe9de5": "✅ Uniswap: Universal Router (Permit2)",
	"0x643770e279d5d0733f21d6dc03a8efbabf3255b4": "✅ Uniswap: Universal Router (Base)",

	// ═══════════════════════════════════════════════════════════════════════════
	// DEX AGGREGATORS
	// ═══════════════════════════════════════════════════════════════════════════
	// 1inch
	"0x1111111254eeb25477b68fb85ed929f73a960582": "✅ 1inch V5: Router",
	"0x1111111254fb6c44bac0bed2854e76f90643097d": "✅ 1inch V4: Router",
	"0x11111112542d85b3ef69ae05771c2dccff4faa26": "✅ 1inch V3: Router",
	"0x111111125421ca6dc452d289314280a0f8842a65": "✅ 1inch V6: Router",
	"0x1111111254760f7ab3f16433eea9304126dcd199": "✅ 1inch: Limit Order",
	// Paraswap
	"0xdef171fe48cf0115b1d80b88dc8eab59176fee57": "✅ Paraswap: Augustus V6",
	"0x216b4b4ba9f3e719726886d34a177484278bfcae": "✅ Paraswap: V5 Router",
	"0x55b916ce078ea594c10a874ba67ecc3d62e29822": "✅ Paraswap: Token Transfer Proxy",
	// 0x Protocol
	"0xdef1c0ded9bec7f1a1670819833240f027b25eff": "✅ 0x: Exchange Proxy",
	"0xdef1abe32c034e558cdd535791643c58a13acc10": "✅ 0x: Exchange Proxy (Polygon)",
	// Cowswap
	"0x9008d19f58aabd9ed0d60971565aa8510560ab41": "✅ CoW Protocol: GPv2Settlement",
	"0xc92e8bdf79f0507f65a392b0ab4667716bfe0110": "✅ CoW Protocol: Vault Relayer",
	// Kyberswap
	"0x6131b5fae19ea4f9d964eac0408e4408b66337b5": "✅ KyberSwap: Meta Aggregation Router",
	"0x617dee16b86534a5d792a4d7a62fb491b544111e": "✅ KyberSwap: Router",
	// ODOS
	"0xcf5540fffcdc3d510b18bfca6d2b9987b0772559": "✅ ODOS: Router V2",
	"0x4e3288c9ca110bcc82bf38f09a7b425c095d92bf": "✅ ODOS: Router",
	// Lifi
	"0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae": "✅ LiFi: Diamond",

	// ═══════════════════════════════════════════════════════════════════════════
	// MAJOR DEXS
	// ═══════════════════════════════════════════════════════════════════════════
	// SushiSwap
	"0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f": "✅ SushiSwap: Router",
	"0x1b02da8cb0d097eb8d57a175b88c7d8b47997506": "✅ SushiSwap: Router (Multi)",
	"0x0bfbcf9fa4f9c56b0f40a671ad40e0805a091865": "✅ SushiSwap: RouteProcessor3",
	"0x544ba588efd839d2692fc31ea991cd39993c135f": "✅ SushiSwap: RouteProcessor4",
	// PancakeSwap
	"0x10ed43c718714eb63d5aa57b78b54704e256024e": "✅ PancakeSwap: Router V2",
	"0x13f4ea83d0bd40e75c8222255bc855a974568dd4": "✅ PancakeSwap: Smart Router",
	"0x1b81d678ffb9c0263b24a97847620c99d213eb14": "✅ PancakeSwap: Router V3",
	// Curve
	"0x99a58482bd75cbab83b27ec03ca68ff489b5788f": "✅ Curve: Router",
	"0xbebe5d8f8686e0d9d5fccc16a4db509a46a7a833": "✅ Curve: Router NG",
	"0xf0d4c12a5768d806021f80a262b4d39d26c58b8d": "✅ Curve: Deposit/Withdraw",
	// Balancer
	"0xba12222222228d8ba445958a75a0704d566bf2c8": "✅ Balancer: Vault",
	"0xba12222222228d8ba445958a75a0704d566bf2c9": "✅ Balancer: Relayer",
	// Velodrome/Aerodrome
	"0xa062ae8a9c5e11aaa026fc2670b0d65ccc8b2858": "✅ Velodrome: Router V2",
	"0x9c12939390052919af3155f41bf4160fd3666a6f": "✅ Velodrome: Router",
	"0xcf77a3ba9a5ca399b7c97c74d54e5b1beb874e43": "✅ Aerodrome: Router",
	// Camelot
	"0xc873fecbd354f5a56e00e710b90ef4201db2448d": "✅ Camelot: Router V2",
	// Trader Joe
	"0xb4315e873dbcf96ffd0acd8ea43f689d8c20fb30": "✅ TraderJoe: LB Router",

	// ═══════════════════════════════════════════════════════════════════════════
	// NFT MARKETPLACES
	// ═══════════════════════════════════════════════════════════════════════════
	// OpenSea
	"0x1e0049783f008a0085193e00003d00cd54003c71": "✅ OpenSea: Seaport 1.4",
	"0x00000000000001ad428e4906ae43d8f9852d0dd6": "✅ OpenSea: Seaport 1.5",
	"0x00000000000000adc04c56bf30ac9d3c0aaf14dc": "✅ OpenSea: Seaport 1.6",
	"0x0000000000000068f116a894984e2db1123eb395": "✅ OpenSea: Seaport 1.6",
	// Blur
	"0x29469395eaf6f95920e59f858042f0e28d98a20b": "✅ Blur: Marketplace",
	"0x000000000000ad05ccc4f10045630fb830b95127": "✅ Blur: Blend",
	"0xb2ecfe4e4d61f8790bbb9de2d1259b9e2410cea5": "✅ Blur: Pool",
	// X2Y2
	"0x74312363e45dcaba76c59ec49a7aa8a65a67eed3": "✅ X2Y2: Exchange",
	// LooksRare
	"0x0000000000e655fae4d56241588680f86e3b2377": "✅ LooksRare: Exchange V2",
	// Rarible
	"0x9757f2d2b135150bbeb65308d4a91804107cd8d6": "✅ Rarible: Exchange V2",

	// ═══════════════════════════════════════════════════════════════════════════
	// LENDING & BORROWING
	// ═══════════════════════════════════════════════════════════════════════════
	// Aave
	"0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2": "✅ Aave V3: Pool",
	"0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9": "✅ Aave V2: Pool",
	"0x794a61358d6845594f94dc1db02a252b5b4814ad": "✅ Aave V3: Pool (Polygon)",
	"0x8dff5e27ea6b7ac08ebfdf9eb090f32ee9a30fcf": "✅ Aave V2: Pool (Polygon)",
	"0xa97684ead0e402dc232d5a977953df7ecbab3cdb": "✅ Aave V3: Pool Addresses Provider",
	// Compound
	"0xc3d688b66703497daa19211eedff47f25384cdc3": "✅ Compound V3: cUSDCv3",
	"0xa17581a9e3356d9a858b789d68b4d866e593ae94": "✅ Compound V3: cWETHv3",
	"0x3afdc9bca9213a35503b077a6072f3d0d5ab0d30": "✅ Compound: Comet",
	// Morpho
	"0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb": "✅ Morpho Blue",
	"0x777777c9898d384f785ee44acfe945efdff5f3e0": "✅ Morpho: Optimizer",
	// Spark (MakerDAO)
	"0xc13e21b648a5ee794902342038ff3adab66be987": "✅ Spark: Pool",
	"0x02c3ea4e34c0cbd694d2adfa2c690eecbc1793ee": "✅ Spark: Pool (Gnosis)",
	// Radiant
	"0x2032b9a8e9f7e76768ca9271003d3e43e1616b1f": "✅ Radiant: Lending Pool",

	// ═══════════════════════════════════════════════════════════════════════════
	// BRIDGES
	// ═══════════════════════════════════════════════════════════════════════════
	// Official L2 Bridges
	"0x99c9fc46f92e8a1c0dec1b1747d010903e884be1": "✅ Optimism: Gateway",
	"0x4dbd4fc535ac27206064b68ffcf827b0a60bab3f": "✅ Arbitrum: Inbox",
	"0x8315177ab297ba92a06054ce80a67ed4dbd7ed3a": "✅ Arbitrum: Bridge",
	"0x3154cf16ccdb4c6d922629664174b904d80f2c35": "✅ Base: Bridge",
	"0x32400084c286cf3e17e7b677ea9583e60a000324": "✅ zkSync: Diamond",
	"0xabea9132b05a70803a4e85094fd0e1800777fbef": "✅ zkSync: Bridge",
	"0xd19d4b5d358258f05d7b411e21a1460d11b0876f": "✅ Linea: Bridge",
	"0x504a330327a089d8364c4ab3811ee26976d388ce": "✅ Scroll: Gateway",
	// Third Party Bridges
	"0x3a23f943181408eac424116af7b7790c94cb97a5": "✅ Socket: Gateway",
	"0xc30141b657f4216252dc59af2e7cdb9d8792e1b0": "✅ Socket: Registry",
	"0x2796317b0ff8538f253012862c06787adfb8ceb6": "✅ Synapse: Bridge",
	"0xd5d61e9dfb6680cba8353988ba0337802811c2e1": "✅ Stargate: Router",
	"0x8731d54e9d02c286767d56ac03e8037c07e01e98": "✅ Stargate: Router V2",
	"0x0af91fa049a7e1894f480bfe5bba20142c6c29a9": "✅ Stargate: Pool",
	"0x5427fefa711eff984124bfbb1ab6fbf5e3da1820": "✅ Across: SpokePool V3",
	"0xe35e9842fceaca96570b734083f4a58e8f7c5f2a": "✅ Across: SpokePool",
	"0xee327f889d5947c1dc1c92e5ddbe27a7902ae07f": "✅ Hop: Bonder",
	"0x3e4a3a4796d16c0cd582c382691998f7c06420b6": "✅ Hop: Bridge",
	"0x80c67432656d59144ceff962e8faf8926599bcf8": "✅ Orbiter: Bridge",
	"0xe4edb277e41dc89ab076a1f049f4a3efa700bce8": "✅ Orbiter: Router",

	// ═══════════════════════════════════════════════════════════════════════════
	// DERIVATIVES & PERPETUALS
	// ═══════════════════════════════════════════════════════════════════════════
	"0xd5220b23e2392e1ff37e9a329d9261272b8b07dd": "✅ GMX: Vault",
	"0x489ee077994b6658eafa855c308275ead8097c4a": "✅ GMX: Router",
	"0xc8ee91a54287db53897056e12d9819156d3822fb": "✅ GMX V2: Exchange Router",
	"0x7c68c7866a64fa2160f78eeae12217ffbf871fa8": "✅ GMX V2: Deposit Vault",
	"0x5ff137d4b0fdcd49dca30c7cf57e578a026d2789": "✅ Account Abstraction: EntryPoint 0.6",
	"0x0000000071727de22e5e9d8baf0edac6f37da032": "✅ Account Abstraction: EntryPoint 0.7",

	// ═══════════════════════════════════════════════════════════════════════════
	// LIQUID STAKING
	// ═══════════════════════════════════════════════════════════════════════════
	"0xae7ab96520de3a18e5e111b5eaab095312d7fe84": "✅ Lido: stETH",
	"0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0": "✅ Lido: wstETH",
	"0x889edc2edab5f40e902b864ad4d7ade8e412f9b1": "✅ Lido: Withdrawal Queue",
	"0xbe9895146f7af43049ca1c1ae358b0541ea49704": "✅ Coinbase: cbETH",
	"0xa35b1b31ce002fbf2058d22f30f95d405200a15b": "✅ Stader: ETHx",
	"0xf951e335afb289353dc249e82926178eac7ded78": "✅ Swell: swETH",
	"0xac3e018457b222d93114458476f3e3416abbe38f": "✅ Frax: sfrxETH",
	"0xa1290d69c65a6fe4df752f95823fae25cb99e5a7": "✅ RocketPool: rETH",
	"0x9d39a5de30e57443bff2a8307a4256c8797a3497": "✅ Stakewise: sETH2",
	"0xbf5495efe5db9ce00f80364c8b423567e58d2110": "✅ EtherFi: eETH",
	"0xcd5fe23c85820f7b72d0926fc9b05b43e359b7ee": "✅ EtherFi: weETH",
	"0x858646372cc42e1a627fce94aa7a7033e7cf075a": "✅ EigenLayer: Strategy Manager",
	"0x39053d51b77dc0d36036fc1fcc8cb819df8ef37a": "✅ EigenLayer: Delegation Manager",

	// ═══════════════════════════════════════════════════════════════════════════
	// WALLETS & INFRASTRUCTURE
	// ═══════════════════════════════════════════════════════════════════════════
	"0x881d40237659c251811cec9c364ef91dc08d300c": "✅ MetaMask: Swap Router",
	"0x74de5d4fcbf63e00296fd95d33236b9794016631": "✅ MetaMask: Swap Router V2",
	"0xca11bde05977b3631167028862be2a173976ca11": "✅ Multicall3",
	"0x5ba1e12693dc8f9c48aad8770482f4739beed696": "✅ Multicall2",

	// ═══════════════════════════════════════════════════════════════════════════
	// YIELD & VAULTS
	// ═══════════════════════════════════════════════════════════════════════════
	"0xa354f35829ae975e850e23e9615b11da1b3dc4de": "✅ Yearn: yvUSDC",
	"0xdb25ca703181e7484a155dd612b06f57e12be5f0": "✅ Yearn: yETH",
	"0x8e5645e038b9fb95cd8b0beb7b2c51c9ca9e8f1d": "✅ Convex: Booster",
	"0x4e3fbd56cd56c3e72c1403e103b45db9da5b9d2b": "✅ Convex: CVX",
	"0x5a6a4d54456819380173272a5e8e9b9904bdf41b": "✅ Curve: MIM Pool",
	"0xd533a949740bb3306d119cc777fa900ba034cd52": "✅ Curve: CRV Token",
	"0xf650c3d88d12db855b8bf7d11be6c55a4e07dcc9": "✅ Compound: cUSDT",
	"0x39aa39c021dfbae8fac545936693ac917d5e7563": "✅ Compound: cUSDC",
	"0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5": "✅ Compound: cETH",
	"0xc36442b4a4522e871399cd717abdd847ab11fe88": "✅ Uniswap V3: NonfungiblePositionManager",

	// ═══════════════════════════════════════════════════════════════════════════
	// RELAY PROTOCOL - Cross-chain bridging (LEGIT but often abused in phishing)
	// ═══════════════════════════════════════════════════════════════════════════
	"0xa5f565650890fba1824ee0f21ebbbf660a179934": "⚠️ Relay: ApprovalProxyV3 (Verify Site!)",
	"0x2f0a5b80e0e1d49d5eea44fd73c7f29e5e7d0b2a": "⚠️ Relay: RouterV3 (Verify Site!)",
	"0xf70da97812cb96acdf810712aa562db8dfa3dbef": "⚠️ Relay: ApprovalProxy (Verify Site!)",

	// ═══════════════════════════════════════════════════════════════════════════
	// KNOWN DRAINERS / SCAM CONTRACTS - HIGH RISK
	// ═══════════════════════════════════════════════════════════════════════════
	"0x000000000000084e91743124a982076c59f10084": "🚨 DRAINER: Pink Drainer",
	"0x0000000000000000000000000000000000001010": "🚨 DRAINER: Inferno Drainer",
	"0x00000000000003441d59dde9a90bffb1cd3fabf1": "🚨 DRAINER: Angel Drainer",
	"0x00000000009726632680fb29d3f7a9734e3010e2": "🚨 DRAINER: Monkey Drainer",
	"0x0000000000ffe8b47b3e2130213b802212439497": "🚨 SCAM: Fake Uniswap",
	"0x00000000000045166c45af0fc6e4cf31d9e14b9a": "🚨 DRAINER: Venom Drainer",
	"0x0000000000a84d1a9b0063a910315c7ffa9cd248": "🚨 DRAINER: Ace Drainer",
}

// Risk levels for spenders
// "safe" = trusted protocol, "warning" = legit but verify, "critical" = known scam
var spenderRiskLevel = map[string]string{
	// ═══════════════════════════════════════════════════════════════════════════
	// DRAINERS = CRITICAL (known malicious)
	// ═══════════════════════════════════════════════════════════════════════════
	"0x000000000000084e91743124a982076c59f10084": "critical", // Pink Drainer
	"0x0000000000000000000000000000000000001010": "critical", // Inferno Drainer
	"0x00000000000003441d59dde9a90bffb1cd3fabf1": "critical", // Angel Drainer
	"0x00000000009726632680fb29d3f7a9734e3010e2": "critical", // Monkey Drainer
	"0x0000000000ffe8b47b3e2130213b802212439497": "critical", // Fake Uniswap
	"0x00000000000045166c45af0fc6e4cf31d9e14b9a": "critical", // Venom Drainer
	"0x0000000000a84d1a9b0063a910315c7ffa9cd248": "critical", // Ace Drainer

	// ═══════════════════════════════════════════════════════════════════════════
	// WARNING = Legit but commonly abused in phishing (verify the site!)
	// ═══════════════════════════════════════════════════════════════════════════
	"0xa5f565650890fba1824ee0f21ebbbf660a179934": "warning", // Relay ApprovalProxyV3
	"0x2f0a5b80e0e1d49d5eea44fd73c7f29e5e7d0b2a": "warning", // Relay RouterV3
	"0xf70da97812cb96acdf810712aa562db8dfa3dbef": "warning", // Relay ApprovalProxy

	// ═══════════════════════════════════════════════════════════════════════════
	// SAFE = Trusted, audited protocols (no risk score impact)
	// ═══════════════════════════════════════════════════════════════════════════
	// Uniswap
	"0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "safe", // Uniswap V3 Router 2
	"0xe592427a0aece92de3edee1f18e0157c05861564": "safe", // Uniswap V3 Router
	"0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "safe", // Uniswap V2 Router
	"0x000000000022d473030f116ddee9f6b43ac78ba3": "safe", // Permit2
	"0xef1c6e67703c7bd7107eed8303fbe6ec2554bf6b": "safe", // Universal Router
	"0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad": "safe", // Universal Router 2
	// Aggregators
	"0x1111111254eeb25477b68fb85ed929f73a960582": "safe", // 1inch V5
	"0x111111125421ca6dc452d289314280a0f8842a65": "safe", // 1inch V6
	"0xdef1c0ded9bec7f1a1670819833240f027b25eff": "safe", // 0x
	"0x9008d19f58aabd9ed0d60971565aa8510560ab41": "safe", // CoW Protocol
	"0x6131b5fae19ea4f9d964eac0408e4408b66337b5": "safe", // KyberSwap
	"0xcf5540fffcdc3d510b18bfca6d2b9987b0772559": "safe", // ODOS
	"0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae": "safe", // LiFi
	// DEXs
	"0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f": "safe", // SushiSwap
	"0x10ed43c718714eb63d5aa57b78b54704e256024e": "safe", // PancakeSwap
	"0x99a58482bd75cbab83b27ec03ca68ff489b5788f": "safe", // Curve
	"0xba12222222228d8ba445958a75a0704d566bf2c8": "safe", // Balancer
	// Lending
	"0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2": "safe", // Aave V3
	"0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9": "safe", // Aave V2
	"0xc3d688b66703497daa19211eedff47f25384cdc3": "safe", // Compound V3
	"0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb": "safe", // Morpho Blue
	"0xc13e21b648a5ee794902342038ff3adab66be987": "safe", // Spark
	// Bridges
	"0x99c9fc46f92e8a1c0dec1b1747d010903e884be1": "safe", // Optimism
	"0x8315177ab297ba92a06054ce80a67ed4dbd7ed3a": "safe", // Arbitrum
	"0x3154cf16ccdb4c6d922629664174b904d80f2c35": "safe", // Base
	"0x32400084c286cf3e17e7b677ea9583e60a000324": "safe", // zkSync
	"0xd5d61e9dfb6680cba8353988ba0337802811c2e1": "safe", // Stargate
	"0x5427fefa711eff984124bfbb1ab6fbf5e3da1820": "safe", // Across
	// Staking
	"0xae7ab96520de3a18e5e111b5eaab095312d7fe84": "safe", // Lido stETH
	"0x858646372cc42e1a627fce94aa7a7033e7cf075a": "safe", // EigenLayer
	// NFT
	"0x00000000000000adc04c56bf30ac9d3c0aaf14dc": "safe", // OpenSea Seaport
	"0x29469395eaf6f95920e59f858042f0e28d98a20b": "safe", // Blur
	// Account Abstraction
	"0x5ff137d4b0fdcd49dca30c7cf57e578a026d2789": "safe", // EntryPoint 0.6
	"0x0000000071727de22e5e9d8baf0edac6f37da032": "safe", // EntryPoint 0.7
}

// Known tokens database
var knownTokens = map[string]string{
	// Stablecoins
	"0xdac17f958d2ee523a2206206994597c13d831ec7": "USDT",
	"0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "USDC",
	"0x6b175474e89094c44da98b954eedeac495271d0f": "DAI",
	"0x4fabb145d64652a948d72533023f6e7a623c7c53": "BUSD",
	"0x853d955acef822db058eb8505911ed77f175b99e": "FRAX",
	// ETH wrapped
	"0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "WETH",
	"0x2260fac5e5542a773aa44fbcfedf7c193bc2c599": "WBTC",
	// DeFi tokens
	"0x1f9840a85d5af5bf1d1762f925bdaddc4201f984": "UNI",
	"0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9": "AAVE",
	"0x514910771af9ca656af840dff83e8264ecf986ca": "LINK",
	"0xd533a949740bb3306d119cc777fa900ba034cd52": "CRV",
	"0xc00e94cb662c3520282e6f5717214004a7f26888": "COMP",
	"0x9f8f72aa9304c8b593d555f12ef6589cc3a579a2": "MKR",
	"0x6b3595068778dd592e39a122f4f5a5cf09c90fe2": "SUSHI",
	"0x0bc529c00c6401aef6d220be8c6ea1667f6ad93e": "YFI",
	"0xba100000625a3754423978a60c9317c58a424e3d": "BAL",
	// Meme coins
	"0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce": "SHIB",
	"0x4d224452801aced8b2f0aebe155379bb5d594381": "APE",
	"0x6982508145454ce325ddbe47a25d4ec3d2311933": "PEPE",
	// Arbitrum
	"0x912ce59144191c1204e64559fe8253a0e49e6548": "ARB",
	"0x82af49447d8a07e3bd95bd0d56f35241523fbab1": "WETH (Arb)",
	// Optimism
	"0x4200000000000000000000000000000000000042": "OP",
	// Base
	"0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": "USDC (Base)",
	// Polygon
	"0x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270": "WMATIC",
	"0x7ceb23fd6bc0add59e62ac25578270cff1b9f619": "WETH (Polygon)",
}

type ChainClient struct {
	ChainID ChainID
	RPC     string
	client  *http.Client
}

func NewChainClient(chainID ChainID, rpcURL string) *ChainClient {
	return &ChainClient{
		ChainID: chainID,
		RPC:     rpcURL,
		client: &http.Client{
			Timeout: 60 * time.Second, // Increased for wallets with many approvals
		},
	}
}

// GetApprovals fetches all ERC20 approvals for a wallet
// Uses Alchemy first (faster), falls back to Etherscan
func (c *ChainClient) GetApprovals(ctx context.Context, walletAddress string) ([]Approval, error) {
	log.Printf("[%s] Scanning approvals for %s", c.ChainID, walletAddress)

	// Try Alchemy first (faster, higher rate limits)
	if endpoint, ok := alchemyConfig.Endpoints[string(c.ChainID)]; ok {
		approvals, err := c.getApprovalsAlchemy(ctx, walletAddress, endpoint)
		if err == nil && len(approvals) > 0 {
			return approvals, nil
		}
		log.Printf("[%s] Alchemy scan returned %d, trying Etherscan...", c.ChainID, len(approvals))
	}

	// Fallback to Etherscan
	return c.getApprovalsEtherscan(ctx, walletAddress)
}

// getApprovalsAlchemy uses Alchemy's eth_getLogs (faster, parallel-friendly)
func (c *ChainClient) getApprovalsAlchemy(ctx context.Context, walletAddress string, endpoint string) ([]Approval, error) {
	approvals := []Approval{}

	// ERC20 Approval event signature
	approvalTopic := "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
	paddedWallet := "0x000000000000000000000000" + strings.TrimPrefix(strings.ToLower(walletAddress), "0x")

	// Use eth_getLogs via Alchemy RPC
	rpcRequest := map[string]interface{}{
		"jsonrpc": "2.0",
		"method":  "eth_getLogs",
		"params": []interface{}{
			map[string]interface{}{
				"fromBlock": "0x0",
				"toBlock":   "latest",
				"topics":    []string{approvalTopic, paddedWallet},
			},
		},
		"id": 1,
	}

	body, err := json.Marshal(rpcRequest)
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequestWithContext(ctx, "POST", endpoint, bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var rpcResp struct {
		Result []struct {
			Address string   `json:"address"`
			Topics  []string `json:"topics"`
			Data    string   `json:"data"`
		} `json:"result"`
		Error *struct {
			Message string `json:"message"`
		} `json:"error"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&rpcResp); err != nil {
		return nil, err
	}

	if rpcResp.Error != nil {
		return nil, fmt.Errorf("alchemy error: %s", rpcResp.Error.Message)
	}

	log.Printf("[%s] Alchemy returned %d approval events", c.ChainID, len(rpcResp.Result))

	// Process logs - keep only latest approval per token-spender pair
	latestApprovals := make(map[string]Approval)

	for _, logEntry := range rpcResp.Result {
		if len(logEntry.Topics) < 3 {
			continue
		}

		tokenAddress := logEntry.Address
		spenderAddress := "0x" + logEntry.Topics[2][26:]

		// Parse allowance
		allowanceHex := strings.TrimPrefix(logEntry.Data, "0x")
		allowance := new(big.Int)
		allowance.SetString(allowanceHex, 16)

		// Skip revoked (zero) approvals
		if allowance.Cmp(big.NewInt(0)) == 0 {
			continue
		}

		// Check unlimited
		maxUint256 := new(big.Int)
		maxUint256.SetString("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff", 16)
		threshold := new(big.Int).Div(maxUint256, big.NewInt(2))
		isUnlimited := allowance.Cmp(threshold) > 0

		// Get token and spender info
		tokenSymbol := getTokenSymbol(tokenAddress, c)
		spenderName, spenderRisk := getSpenderInfo(spenderAddress)

		// Set initial risk level based on spender trust level
		// This will be refined in calculateRiskScores based on unlimited status
		riskLevel := spenderRisk
		riskReasons := []string{}

		if isUnlimited {
			riskReasons = append(riskReasons, "Unlimited approval")
		}

		key := tokenAddress + "-" + spenderAddress
		latestApprovals[key] = Approval{
			Chain:          c.ChainID,
			TokenAddress:   tokenAddress,
			TokenSymbol:    tokenSymbol,
			SpenderAddress: spenderAddress,
			SpenderName:    spenderName,
			AllowanceRaw:   allowance.String(),
			AllowanceHuman: formatAllowance(allowance),
			IsUnlimited:    isUnlimited,
			RiskLevel:      riskLevel,
			RiskReasons:    riskReasons,
			LastUpdated:    time.Now().Unix(),
		}
	}

	for _, approval := range latestApprovals {
		approvals = append(approvals, approval)
	}

	log.Printf("[%s] Found %d active approvals via Alchemy", c.ChainID, len(approvals))
	return approvals, nil
}

// getApprovalsEtherscan uses Etherscan API v2 (fallback)
func (c *ChainClient) getApprovalsEtherscan(ctx context.Context, walletAddress string) ([]Approval, error) {
	approvals := []Approval{}

	// Get chain ID for Etherscan v2
	chainID, ok := etherscanConfig.ChainIDs[string(c.ChainID)]
	if !ok {
		log.Printf("[%s] Chain not supported by Etherscan v2, skipping", c.ChainID)
		return approvals, nil
	}

	// ERC20 Approval event signature
	approvalTopic := "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
	paddedWallet := "0x000000000000000000000000" + strings.TrimPrefix(strings.ToLower(walletAddress), "0x")

	// Etherscan API v2 endpoint
	url := fmt.Sprintf(
		"https://api.etherscan.io/v2/api?chainid=%d&module=logs&action=getLogs&fromBlock=0&toBlock=latest&topic0=%s&topic1=%s&apikey=%s",
		chainID,
		approvalTopic,
		paddedWallet,
		etherscanConfig.APIKey,
	)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("Etherscan API call failed: %w", err)
	}
	defer resp.Body.Close()

	// Use RawMessage to handle both array and string responses
	var rawResp struct {
		Status  string          `json:"status"`
		Message string          `json:"message"`
		Result  json.RawMessage `json:"result"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&rawResp); err != nil {
		return nil, fmt.Errorf("failed to decode Etherscan response: %w", err)
	}

	// Check if result is a string (error message) or array (logs)
	if len(rawResp.Result) > 0 && rawResp.Result[0] == '"' {
		// Result is a string - this is an error or "No records found"
		var errMsg string
		if err := json.Unmarshal(rawResp.Result, &errMsg); err != nil {
			log.Printf("[%s] Failed to parse Etherscan message: %v", c.ChainID, err)
		} else {
			log.Printf("[%s] Etherscan returned message: %s", c.ChainID, errMsg)
		}
		return approvals, nil // Return empty, not an error
	}

	// Parse as array of logs
	type LogEntry struct {
		Address     string   `json:"address"`
		Topics      []string `json:"topics"`
		Data        string   `json:"data"`
		BlockNumber string   `json:"blockNumber"`
		TimeStamp   string   `json:"timeStamp"`
		TxHash      string   `json:"transactionHash"`
	}
	var logs []LogEntry
	if err := json.Unmarshal(rawResp.Result, &logs); err != nil {
		log.Printf("[%s] Failed to parse logs: %v", c.ChainID, err)
		return approvals, nil
	}

	if rawResp.Status != "1" && rawResp.Message != "No records found" {
		log.Printf("[%s] Etherscan status: %s - %s", c.ChainID, rawResp.Status, rawResp.Message)
		return approvals, nil
	}

	log.Printf("[%s] Etherscan returned %d approval events", c.ChainID, len(logs))

	// Process approval events - keep track of latest approval per token+spender
	latestApprovals := make(map[string]Approval)

	for _, logEntry := range logs {
		if len(logEntry.Topics) < 3 {
			continue
		}

		tokenAddress := logEntry.Address
		spenderAddress := "0x" + logEntry.Topics[2][26:] // Extract address from padded topic

		// Parse allowance from data field
		allowanceHex := strings.TrimPrefix(logEntry.Data, "0x")
		allowance := new(big.Int)
		allowance.SetString(allowanceHex, 16)

		// Check if unlimited (max uint256 or very large)
		maxUint256 := new(big.Int)
		maxUint256.SetString("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff", 16)
		threshold := new(big.Int).Div(maxUint256, big.NewInt(2))
		isUnlimited := allowance.Cmp(threshold) > 0

		// Determine risk level
		riskReasons := []string{}

		if isUnlimited {
			riskReasons = append(riskReasons, "Unlimited approval")
		}

		// Check if approval is still active (non-zero)
		if allowance.Cmp(big.NewInt(0)) == 0 {
			continue // Skip revoked approvals
		}

		// Get token symbol from known tokens or fetch from chain
		tokenSymbol := getTokenSymbol(tokenAddress, c)

		// Get spender name from known spenders database
		spenderName, spenderRisk := getSpenderInfo(spenderAddress)

		// Set initial risk level based on spender trust level
		// This will be refined in calculateRiskScores based on unlimited status
		riskLevel := spenderRisk

		key := tokenAddress + "-" + spenderAddress
		approval := Approval{
			Chain:          c.ChainID,
			TokenAddress:   tokenAddress,
			TokenSymbol:    tokenSymbol,
			SpenderAddress: spenderAddress,
			SpenderName:    spenderName,
			AllowanceRaw:   allowance.String(),
			AllowanceHuman: formatAllowance(allowance),
			IsUnlimited:    isUnlimited,
			RiskLevel:      riskLevel,
			RiskReasons:    riskReasons,
			LastUpdated:    time.Now().Unix(),
		}

		latestApprovals[key] = approval
	}

	// Convert map to slice
	for _, approval := range latestApprovals {
		approvals = append(approvals, approval)
	}

	log.Printf("[%s] Found %d active approvals for %s", c.ChainID, len(approvals), walletAddress)
	return approvals, nil
}

// getTokenSymbol returns the token symbol from known tokens or fetches from chain
func getTokenSymbol(tokenAddress string, c *ChainClient) string {
	lowerAddr := strings.ToLower(tokenAddress)

	// Check known tokens first
	if symbol, ok := knownTokens[lowerAddr]; ok {
		return symbol
	}

	// Try to fetch from chain via eth_call to symbol()
	symbol, err := c.fetchTokenSymbol(tokenAddress)
	if err == nil && symbol != "" {
		return symbol
	}

	// Fallback: return shortened address
	if len(tokenAddress) >= 10 {
		return tokenAddress[:6] + "..." + tokenAddress[len(tokenAddress)-4:]
	}
	return "ERC20"
}

// fetchTokenSymbol calls symbol() on the token contract
func (c *ChainClient) fetchTokenSymbol(tokenAddress string) (string, error) {
	// symbol() function selector: 0x95d89b41
	callData := "0x95d89b41"

	rpcRequest := map[string]interface{}{
		"jsonrpc": "2.0",
		"method":  "eth_call",
		"params": []interface{}{
			map[string]string{
				"to":   tokenAddress,
				"data": callData,
			},
			"latest",
		},
		"id": 1,
	}

	body, err := json.Marshal(rpcRequest)
	if err != nil {
		return "", err
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, "POST", c.RPC, bytes.NewReader(body))
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	var rpcResp struct {
		Result string `json:"result"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&rpcResp); err != nil {
		return "", err
	}

	// Decode the result (ABI encoded string)
	return decodeString(rpcResp.Result), nil
}

// decodeString decodes an ABI-encoded string from eth_call result
func decodeString(hexData string) string {
	if len(hexData) < 130 { // 0x + 64 (offset) + 64 (length) + at least some data
		return ""
	}

	// Remove 0x prefix
	data := strings.TrimPrefix(hexData, "0x")
	if len(data) < 128 {
		return ""
	}

	// Parse length (second 32 bytes = chars 64-128)
	lengthHex := data[64:128]
	length := new(big.Int)
	length.SetString(lengthHex, 16)

	// Extract string data
	strLen := int(length.Int64())
	if strLen == 0 || strLen > 100 { // sanity check
		return ""
	}

	// String starts at byte 128
	if len(data) < 128+strLen*2 {
		return ""
	}

	strHex := data[128 : 128+strLen*2]
	strBytes, err := hex.DecodeString(strHex)
	if err != nil {
		return ""
	}

	return string(strBytes)
}

// getSpenderInfo returns spender name and risk level
func getSpenderInfo(spenderAddress string) (string, string) {
	lowerAddr := strings.ToLower(spenderAddress)

	// Check known spenders
	if name, ok := knownSpenders[lowerAddr]; ok {
		// Check if this spender has a custom risk level
		if riskLevel, hasRisk := spenderRiskLevel[lowerAddr]; hasRisk {
			return name, riskLevel // Known risky spender (drainer, etc.)
		}
		return name, "safe" // Known legitimate protocol
	}

	// Unknown spender - return formatted address with warning
	if len(spenderAddress) >= 10 {
		return spenderAddress[:6] + "..." + spenderAddress[len(spenderAddress)-4:], "warning"
	}
	return "Unknown Contract", "warning"
}

// Known token decimals (non-standard tokens)
var tokenDecimals = map[string]int{
	// 6 decimal tokens
	"0xdac17f958d2ee523a2206206994597c13d831ec7": 6, // USDT
	"0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": 6, // USDC
	"0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": 6, // USDC (Base)
	// 8 decimal tokens
	"0x2260fac5e5542a773aa44fbcfedf7c193bc2c599": 8, // WBTC
}

// getTokenDecimals returns the decimals for a token (default 18)
func getTokenDecimals(tokenAddress string) int {
	if decimals, ok := tokenDecimals[strings.ToLower(tokenAddress)]; ok {
		return decimals
	}
	return 18 // Standard ERC20 default
}

// formatAllowance converts big.Int to human-readable format
// Uses default 18 decimals - for token-specific decimals use formatAllowanceForToken
func formatAllowance(amount *big.Int) string {
	return formatAllowanceWithDecimals(amount, 18)
}

// formatAllowanceForToken converts big.Int to human-readable format with token-specific decimals
func formatAllowanceForToken(amount *big.Int, tokenAddress string) string {
	return formatAllowanceWithDecimals(amount, getTokenDecimals(tokenAddress))
}

// formatAllowanceWithDecimals converts big.Int to human-readable format with specific decimals
func formatAllowanceWithDecimals(amount *big.Int, decimals int) string {
	// Check for unlimited
	maxUint256 := new(big.Int)
	maxUint256.SetString("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff", 16)
	threshold := new(big.Int).Div(maxUint256, big.NewInt(2))

	if amount.Cmp(threshold) > 0 {
		return "UNLIMITED"
	}

	// Convert to float with correct decimals
	divisor := new(big.Float).SetInt(new(big.Int).Exp(big.NewInt(10), big.NewInt(int64(decimals)), nil))
	amountFloat := new(big.Float).SetInt(amount)
	result := new(big.Float).Quo(amountFloat, divisor)

	// Format based on size
	f, _ := result.Float64()
	if f >= 1e9 {
		return fmt.Sprintf("%.2fB", f/1e9)
	} else if f >= 1e6 {
		return fmt.Sprintf("%.2fM", f/1e6)
	} else if f >= 1e3 {
		return fmt.Sprintf("%.2fK", f/1e3)
	}
	return fmt.Sprintf("%.4f", f)
}

// GetContractBytecode fetches contract bytecode for analysis
func (c *ChainClient) GetContractBytecode(ctx context.Context, contractAddress string) ([]byte, error) {
	log.Printf("[%s] Fetching bytecode for %s", c.ChainID, contractAddress)

	// JSON-RPC call: eth_getCode
	rpcRequest := map[string]interface{}{
		"jsonrpc": "2.0",
		"method":  "eth_getCode",
		"params":  []interface{}{contractAddress, "latest"},
		"id":      1,
	}

	body, err := json.Marshal(rpcRequest)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal RPC request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", c.RPC, bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("RPC call failed: %w", err)
	}
	defer resp.Body.Close()

	var rpcResp struct {
		Result string `json:"result"`
		Error  *struct {
			Message string `json:"message"`
		} `json:"error"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&rpcResp); err != nil {
		return nil, fmt.Errorf("failed to decode RPC response: %w", err)
	}

	if rpcResp.Error != nil {
		return nil, fmt.Errorf("RPC error: %s", rpcResp.Error.Message)
	}

	// Decode hex bytecode
	bytecode, err := hex.DecodeString(strings.TrimPrefix(rpcResp.Result, "0x"))
	if err != nil {
		return nil, fmt.Errorf("failed to decode bytecode: %w", err)
	}

	log.Printf("[%s] Fetched %d bytes of bytecode for %s", c.ChainID, len(bytecode), contractAddress)
	return bytecode, nil
}

// ═══════════════════════════════════════════════════════════════════════════════
//                              SCANNER
// ═══════════════════════════════════════════════════════════════════════════════

type Scanner struct {
	clients map[ChainID]*ChainClient
	cache   *Cache
}

func NewScanner() *Scanner {
	clients := make(map[ChainID]*ChainClient)

	for chain, rpc := range config.RPC {
		clients[ChainID(chain)] = NewChainClient(ChainID(chain), rpc)
	}

	return &Scanner{
		clients: clients,
		cache:   NewCache(config.CacheTTL),
	}
}

// ScanWallet performs sequential multi-chain scan with rate limiting
// Etherscan free tier: 3 calls/sec max
func (s *Scanner) ScanWallet(ctx context.Context, walletAddress string, chains []ChainID) (*WalletScanResult, error) {
	log.Printf("Starting multi-chain scan for %s across %d chains", walletAddress, len(chains))

	result := &WalletScanResult{
		WalletAddress: walletAddress,
		ScanTimestamp: time.Now().Unix(),
		ChainsScanned: chains,
		Approvals:     []Approval{},
		ContractRisks: []ContractRisk{},
	}

	// Sequential scan with rate limiting
	// Alchemy supports 25 req/sec, Etherscan free tier 5 req/sec
	// Using 100ms as safe middle ground
	for i, chain := range chains {
		// Rate limit: wait 100ms between calls (except first)
		if i > 0 {
			time.Sleep(100 * time.Millisecond)
		}

		client, ok := s.clients[chain]
		if !ok {
			log.Printf("No client for chain %s", chain)
			continue
		}

		// Get approvals
		approvals, err := client.GetApprovals(ctx, walletAddress)
		if err != nil {
			log.Printf("Error scanning %s: %v", chain, err)
			continue
		}

		result.Approvals = append(result.Approvals, approvals...)
	}

	// Calculate risk scores
	s.calculateRiskScores(result)

	// Generate recommendations
	s.generateRecommendations(result)

	log.Printf("Scan complete: %d approvals, %d critical risks",
		len(result.Approvals), result.CriticalRisks)

	return result, nil
}

func (s *Scanner) calculateRiskScores(result *WalletScanResult) {
	totalRisk := 0

	// First pass: calculate individual risk scores and update levels
	for i, approval := range result.Approvals {
		riskScore := 0
		initialRiskLevel := approval.RiskLevel
		isTrustedProtocol := initialRiskLevel == "safe"
		isDrainer := initialRiskLevel == "critical" // Known drainer/scam

		// Base risk from initial approval level
		switch initialRiskLevel {
		case "critical":
			riskScore = 50 // Drainer = very high base score
			result.Approvals[i].RiskReasons = append(result.Approvals[i].RiskReasons, "🚨 Known malicious contract")
		case "warning":
			riskScore = 15 // Unknown or Relay-type
		case "safe":
			riskScore = 2 // Trusted protocol
		}

		// Additional risk factors
		if approval.IsUnlimited {
			if isDrainer {
				riskScore += 20 // Drainer + unlimited = maximum danger
				result.Approvals[i].RiskReasons = append(result.Approvals[i].RiskReasons, "Unlimited allowance to dangerous contract!")
			} else if isTrustedProtocol {
				riskScore += 8 // Trusted + unlimited = just a warning
				result.Approvals[i].RiskReasons = append(result.Approvals[i].RiskReasons, "Unlimited allowance (consider reducing)")
			} else {
				riskScore += 15 // Unknown + unlimited = suspicious
				result.Approvals[i].RiskReasons = append(result.Approvals[i].RiskReasons, "Unlimited allowance to unknown contract")
			}
		}

		if strings.HasPrefix(approval.SpenderName, "0x") || approval.SpenderName == "Unknown" {
			riskScore += 10
			result.Approvals[i].RiskReasons = append(result.Approvals[i].RiskReasons, "Unknown spender contract")
		}

		// SMART RISK LEVEL ASSIGNMENT:
		// critical = ONLY for actual dangerous situations
		// warning = unlimited on trusted OR any unknown
		// safe = limited approval on trusted protocol
		if isDrainer {
			// Keep critical - this is a real threat
			result.Approvals[i].RiskLevel = "critical"
		} else if isTrustedProtocol {
			if approval.IsUnlimited {
				// Trusted + unlimited = warning (yellow), not critical
				result.Approvals[i].RiskLevel = "warning"
			} else {
				// Trusted + limited = safe (green)
				result.Approvals[i].RiskLevel = "safe"
			}
		} else {
			// Unknown contract
			if approval.IsUnlimited {
				// Unknown + unlimited = critical (could be dangerous)
				result.Approvals[i].RiskLevel = "critical"
			} else {
				// Unknown + limited = warning
				result.Approvals[i].RiskLevel = "warning"
			}
		}

		totalRisk += riskScore
	}

	// Second pass: count final risk levels (no double counting!)
	for _, approval := range result.Approvals {
		switch approval.RiskLevel {
		case "critical":
			result.CriticalRisks++
		case "warning":
			result.Warnings++
		}
	}

	result.TotalApprovals = len(result.Approvals)
	result.OverallRiskScore = min(100, totalRisk)
}

func (s *Scanner) generateRecommendations(result *WalletScanResult) {
	recommendations := []string{}

	// Critical risk recommendations
	if result.CriticalRisks > 0 {
		recommendations = append(recommendations,
			fmt.Sprintf("🚨 URGENT: Revoke %d critical approvals immediately", result.CriticalRisks))
	}

	// Unlimited approval recommendations
	unlimitedCount := 0
	for _, a := range result.Approvals {
		if a.IsUnlimited {
			unlimitedCount++
		}
	}

	if unlimitedCount > 0 {
		recommendations = append(recommendations,
			fmt.Sprintf("⚠️ You have %d unlimited approvals. Consider setting specific limits.", unlimitedCount))
	}

	if unlimitedCount > 5 {
		recommendations = append(recommendations,
			"💡 Use SENTINEL's batch revoke feature to clean up old approvals")
	}

	// Unknown spender recommendations
	unknownCount := 0
	for _, a := range result.Approvals {
		if a.SpenderName == "Unknown" {
			unknownCount++
		}
	}

	if unknownCount > 0 {
		recommendations = append(recommendations,
			fmt.Sprintf("🔍 %d approvals are to unknown contracts. Verify these are legitimate.", unknownCount))
	}

	// General security tips
	if result.TotalApprovals > 20 {
		recommendations = append(recommendations,
			"📝 You have many active approvals. Consider periodic cleanup of unused ones.")
	}

	if result.OverallRiskScore >= 50 {
		recommendations = append(recommendations,
			"🛡️ Your wallet has elevated risk. Review all approvals carefully.")
	}

	// Chain-specific recommendations
	chainApprovalCount := make(map[ChainID]int)
	for _, a := range result.Approvals {
		chainApprovalCount[a.Chain]++
	}

	for chain, count := range chainApprovalCount {
		if count > 10 {
			recommendations = append(recommendations,
				fmt.Sprintf("📊 %d approvals on %s - consider consolidating", count, chain))
		}
	}

	result.Recommendations = recommendations
}

// ═══════════════════════════════════════════════════════════════════════════════
//                          SERVICE CLIENTS
// ═══════════════════════════════════════════════════════════════════════════════

// DecompilerClient connects to the Rust decompiler service
type DecompilerClient struct {
	baseURL string
	client  *http.Client
}

// DecompilerResponse represents the decompiler analysis result
type DecompilerResponse struct {
	Success    bool     `json:"success"`
	Opcodes    []string `json:"opcodes"`
	Functions  []string `json:"functions"`
	Selectors  []string `json:"selectors"`
	IsProxy    bool     `json:"is_proxy"`
	HasSSTORE  bool     `json:"has_sstore"`
	HasCALL    bool     `json:"has_call"`
	Complexity int      `json:"complexity"`
	Warnings   []string `json:"warnings"`
}

func NewDecompilerClient() *DecompilerClient {
	decompilerURL := os.Getenv("DECOMPILER_URL")
	if decompilerURL == "" {
		decompilerURL = "http://localhost:3000"
	}
	return &DecompilerClient{
		baseURL: decompilerURL,
		client:  &http.Client{Timeout: 60 * time.Second},
	}
}

// Analyze sends bytecode to the Rust decompiler for analysis
func (d *DecompilerClient) Analyze(ctx context.Context, bytecode []byte) (*DecompilerResponse, error) {
	log.Printf("Sending %d bytes to decompiler", len(bytecode))

	reqBody := map[string]interface{}{
		"bytecode": hex.EncodeToString(bytecode),
	}
	body, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", d.baseURL+"/analyze", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := d.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("decompiler request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("decompiler error (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	var result DecompilerResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode decompiler response: %w", err)
	}

	return &result, nil
}

// AnalyzerClient connects to the Python analyzer service
type AnalyzerClient struct {
	baseURL string
	client  *http.Client
}

// AnalyzerResponse represents the security analysis result
type AnalyzerResponse struct {
	RiskScore       int                `json:"risk_score"`
	RiskLevel       string             `json:"risk_level"`
	Vulnerabilities []VulnerabilityHit `json:"vulnerabilities"`
	Patterns        []PatternMatch     `json:"patterns"`
	Recommendations []string           `json:"recommendations"`
}

type VulnerabilityHit struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Severity    string `json:"severity"`
	Description string `json:"description"`
	Location    string `json:"location"`
}

type PatternMatch struct {
	Pattern     string `json:"pattern"`
	Description string `json:"description"`
	IsMalicious bool   `json:"is_malicious"`
}

func NewAnalyzerClient() *AnalyzerClient {
	analyzerURL := os.Getenv("ANALYZER_URL")
	if analyzerURL == "" {
		analyzerURL = "http://localhost:5000"
	}
	return &AnalyzerClient{
		baseURL: analyzerURL,
		client:  &http.Client{Timeout: 60 * time.Second},
	}
}

// Analyze sends contract data to the Python analyzer for security scoring
func (a *AnalyzerClient) Analyze(ctx context.Context, address string, chain string, bytecode []byte) (*AnalyzerResponse, error) {
	log.Printf("Sending contract %s to analyzer", address)

	reqBody := map[string]interface{}{
		"address":  address,
		"chain":    chain,
		"bytecode": hex.EncodeToString(bytecode),
	}
	body, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", a.baseURL+"/api/analyze", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := a.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("analyzer request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("analyzer error (%d): %s", resp.StatusCode, string(bodyBytes))
	}

	var result AnalyzerResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode analyzer response: %w", err)
	}

	return &result, nil
}

// ═══════════════════════════════════════════════════════════════════════════════
//                       CONTRACT ANALYSIS SERVICE
// ═══════════════════════════════════════════════════════════════════════════════

// ContractAnalysisResult is the full analysis result combining decompiler + analyzer
type ContractAnalysisResult struct {
	Address        string              `json:"address"`
	Chain          ChainID             `json:"chain"`
	BytecodeSize   int                 `json:"bytecode_size"`
	Decompilation  *DecompilerResponse `json:"decompilation"`
	SecurityReport *AnalyzerResponse   `json:"security_report"`
	OverallRisk    int                 `json:"overall_risk"`
	AnalyzedAt     int64               `json:"analyzed_at"`
}

// ContractAnalyzer orchestrates decompiler + analyzer
type ContractAnalyzer struct {
	chainClients map[ChainID]*ChainClient
	decompiler   *DecompilerClient
	analyzer     *AnalyzerClient
	cache        *Cache
}

func NewContractAnalyzer(chainClients map[ChainID]*ChainClient) *ContractAnalyzer {
	return &ContractAnalyzer{
		chainClients: chainClients,
		decompiler:   NewDecompilerClient(),
		analyzer:     NewAnalyzerClient(),
		cache:        NewCache(10 * time.Minute),
	}
}

// AnalyzeContract performs full analysis pipeline
func (ca *ContractAnalyzer) AnalyzeContract(ctx context.Context, address string, chain ChainID) (*ContractAnalysisResult, error) {
	cacheKey := fmt.Sprintf("analysis:%s:%s", chain, address)

	// Check cache
	if cached, ok := ca.cache.Get(cacheKey); ok {
		log.Printf("Cache hit for %s on %s", address, chain)
		return cached.(*ContractAnalysisResult), nil
	}

	log.Printf("Starting full analysis for %s on %s", address, chain)

	// Step 1: Fetch bytecode
	client, ok := ca.chainClients[chain]
	if !ok {
		return nil, fmt.Errorf("unsupported chain: %s", chain)
	}

	bytecode, err := client.GetContractBytecode(ctx, address)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch bytecode: %w", err)
	}

	if len(bytecode) == 0 {
		return nil, fmt.Errorf("no bytecode found (not a contract or EOA)")
	}

	result := &ContractAnalysisResult{
		Address:      address,
		Chain:        chain,
		BytecodeSize: len(bytecode),
		AnalyzedAt:   time.Now().Unix(),
	}

	// Step 2: Decompile (non-blocking errors)
	decompResult, err := ca.decompiler.Analyze(ctx, bytecode)
	if err != nil {
		log.Printf("Decompiler warning: %v", err)
	} else {
		result.Decompilation = decompResult
	}

	// Step 3: Security analysis (non-blocking errors)
	analyzerResult, err := ca.analyzer.Analyze(ctx, address, string(chain), bytecode)
	if err != nil {
		log.Printf("Analyzer warning: %v", err)
	} else {
		result.SecurityReport = analyzerResult
		result.OverallRisk = analyzerResult.RiskScore
	}

	// Cache result
	ca.cache.Set(cacheKey, result)

	log.Printf("Analysis complete for %s: risk=%d, bytecode=%d bytes",
		address, result.OverallRisk, result.BytecodeSize)

	return result, nil
}

// ═══════════════════════════════════════════════════════════════════════════════
//                                  CACHE
// ═══════════════════════════════════════════════════════════════════════════════

type Cache struct {
	data map[string]cacheEntry
	mu   sync.RWMutex
	ttl  time.Duration
}

type cacheEntry struct {
	value     interface{}
	expiresAt time.Time
}

func NewCache(ttl time.Duration) *Cache {
	return &Cache{
		data: make(map[string]cacheEntry),
		ttl:  ttl,
	}
}

func (c *Cache) Get(key string) (interface{}, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	entry, ok := c.data[key]
	if !ok || time.Now().After(entry.expiresAt) {
		return nil, false
	}
	return entry.value, true
}

func (c *Cache) Set(key string, value interface{}) {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.data[key] = cacheEntry{
		value:     value,
		expiresAt: time.Now().Add(c.ttl),
	}
}

// ═══════════════════════════════════════════════════════════════════════════════
//                              HTTP HANDLERS
// ═══════════════════════════════════════════════════════════════════════════════

type Server struct {
	scanner          ScannerService
	contractAnalyzer *ContractAnalyzer
	chainClients     map[ChainID]*ChainClient
}

func NewServer() *Server {
	clients := make(map[ChainID]*ChainClient)
	for chain, rpc := range config.RPC {
		clients[ChainID(chain)] = NewChainClient(ChainID(chain), rpc)
	}

	scanner := &Scanner{
		clients: clients,
		cache:   NewCache(config.CacheTTL),
	}

	return &Server{
		scanner:          scanner,
		contractAnalyzer: NewContractAnalyzer(clients),
		chainClients:     clients,
	}
}

// ScannerService describes the wallet scanning operations consumed by HTTP handlers.
type ScannerService interface {
	ScanWallet(ctx context.Context, walletAddress string, chains []ChainID) (*WalletScanResult, error)
}

func NewServerWithScanner(scanner ScannerService) *Server {
	clients := make(map[ChainID]*ChainClient)
	for chain, rpc := range config.RPC {
		clients[ChainID(chain)] = NewChainClient(ChainID(chain), rpc)
	}
	return &Server{
		scanner:          scanner,
		contractAnalyzer: NewContractAnalyzer(clients),
		chainClients:     clients,
	}
}

// CORS middleware
func corsMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next(w, r)
	}
}

// Health check
func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"status":  "healthy",
		"service": "sentinel-api",
		"version": "1.0.0",
		"endpoints": map[string]string{
			"scan":          "GET /api/v1/scan?wallet=0x...&chains=ethereum,polygon",
			"analyze":       "GET /api/v1/analyze?contract=0x...&chain=ethereum",
			"analyze_batch": "POST /api/v1/analyze/batch",
			"chains":        "GET /api/v1/chains",
		},
		"services": map[string]string{
			"decompiler": os.Getenv("DECOMPILER_URL"),
			"analyzer":   os.Getenv("ANALYZER_URL"),
		},
	})
}

// Scan wallet endpoint
func (s *Server) handleScan(w http.ResponseWriter, r *http.Request) {
	walletAddress := r.URL.Query().Get("wallet")
	if walletAddress == "" {
		http.Error(w, "wallet parameter required", http.StatusBadRequest)
		return
	}

	// Parse chains (default: all)
	chainsParam := r.URL.Query().Get("chains")
	chains := AllChains

	if chainsParam != "" {
		validChains := make(map[ChainID]struct{}, len(AllChains))
		for _, chain := range AllChains {
			validChains[chain] = struct{}{}
		}

		seen := make(map[ChainID]struct{})
		selected := make([]ChainID, 0)
		invalid := make([]string, 0)

		for _, raw := range strings.Split(chainsParam, ",") {
			trimmed := strings.TrimSpace(raw)
			if trimmed == "" {
				continue
			}

			chainID := ChainID(strings.ToLower(trimmed))
			if _, ok := validChains[chainID]; !ok {
				invalid = append(invalid, trimmed)
				continue
			}

			if _, already := seen[chainID]; !already {
				seen[chainID] = struct{}{}
				selected = append(selected, chainID)
			}
		}

		if len(invalid) > 0 {
			http.Error(w, fmt.Sprintf("unsupported chains: %s", strings.Join(invalid, ", ")), http.StatusBadRequest)
			return
		}

		if len(selected) == 0 {
			http.Error(w, "no valid chains provided", http.StatusBadRequest)
			return
		}

		chains = selected
	}

	ctx, cancel := context.WithTimeout(r.Context(), 30*time.Second)
	defer cancel()

	result, err := s.scanner.ScanWallet(ctx, walletAddress, chains)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(result)
}

// Get supported chains
func (s *Server) handleChains(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"chains": AllChains,
	})
}

// Analyze contract endpoint - uses Decompiler + Analyzer services
func (s *Server) handleAnalyze(w http.ResponseWriter, r *http.Request) {
	contractAddress := r.URL.Query().Get("contract")
	if contractAddress == "" {
		http.Error(w, "contract parameter required", http.StatusBadRequest)
		return
	}

	// Validate address format
	if !strings.HasPrefix(contractAddress, "0x") || len(contractAddress) != 42 {
		http.Error(w, "invalid contract address format", http.StatusBadRequest)
		return
	}

	// Parse chain (default: ethereum)
	chainParam := r.URL.Query().Get("chain")
	chain := Ethereum
	if chainParam != "" {
		chain = ChainID(strings.ToLower(chainParam))
		// Validate chain
		validChain := false
		for _, c := range AllChains {
			if c == chain {
				validChain = true
				break
			}
		}
		if !validChain {
			http.Error(w, fmt.Sprintf("unsupported chain: %s", chainParam), http.StatusBadRequest)
			return
		}
	}

	ctx, cancel := context.WithTimeout(r.Context(), 60*time.Second)
	defer cancel()

	result, err := s.contractAnalyzer.AnalyzeContract(ctx, contractAddress, chain)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(result)
}

// Batch analyze multiple contracts
func (s *Server) handleBatchAnalyze(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST method required", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Contracts []struct {
			Address string  `json:"address"`
			Chain   ChainID `json:"chain"`
		} `json:"contracts"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid JSON body", http.StatusBadRequest)
		return
	}

	if len(req.Contracts) == 0 {
		http.Error(w, "no contracts provided", http.StatusBadRequest)
		return
	}

	if len(req.Contracts) > 10 {
		http.Error(w, "max 10 contracts per batch", http.StatusBadRequest)
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 120*time.Second)
	defer cancel()

	results := make([]*ContractAnalysisResult, 0, len(req.Contracts))
	errors := make([]string, 0)

	// Analyze in parallel
	var wg sync.WaitGroup
	var mu sync.Mutex

	for _, contract := range req.Contracts {
		wg.Add(1)
		go func(addr string, chain ChainID) {
			defer wg.Done()

			if chain == "" {
				chain = Ethereum
			}

			result, err := s.contractAnalyzer.AnalyzeContract(ctx, addr, chain)
			mu.Lock()
			defer mu.Unlock()

			if err != nil {
				errors = append(errors, fmt.Sprintf("%s: %s", addr, err.Error()))
			} else {
				results = append(results, result)
			}
		}(contract.Address, contract.Chain)
	}

	wg.Wait()

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"results": results,
		"errors":  errors,
		"total":   len(req.Contracts),
		"success": len(results),
		"failed":  len(errors),
	})
}

// ═══════════════════════════════════════════════════════════════════════════════
//                                  MAIN
// ═══════════════════════════════════════════════════════════════════════════════

func main() {
	fmt.Println(`
 ██████╗ ███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗
██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║
███████╗ █████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║
╚════██║ ██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║
███████║ ███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
╚══════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝

              Multi-chain Wallet Security Scanner
                     API Server v1.0.0

  Endpoints:
    GET  /api/v1/scan           - Scan wallet approvals
    GET  /api/v1/analyze        - Analyze contract (decompiler + security)
    POST /api/v1/analyze/batch  - Batch analyze contracts
    GET  /api/v1/chains         - List supported chains
	`)

	server := NewServer()

	// Routes
	http.HandleFunc("/health", corsMiddleware(server.handleHealth))
	http.HandleFunc("/api/v1/scan", corsMiddleware(server.handleScan))
	http.HandleFunc("/api/v1/chains", corsMiddleware(server.handleChains))
	http.HandleFunc("/api/v1/analyze", corsMiddleware(server.handleAnalyze))
	http.HandleFunc("/api/v1/analyze/batch", corsMiddleware(server.handleBatchAnalyze))

	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = config.Port
	}

	httpServer := &http.Server{
		Addr:         ":" + port,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 60 * time.Second,
	}

	// Graceful shutdown
	go func() {
		sigChan := make(chan os.Signal, 1)
		signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
		<-sigChan

		log.Println("Shutting down...")
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := httpServer.Shutdown(ctx); err != nil {
			log.Printf("Shutdown error: %v", err)
		}
	}()

	log.Printf("🚀 Sentinel API running on http://localhost:%s", port)
	log.Printf("📡 Scanning %d chains", len(AllChains))

	if err := httpServer.ListenAndServe(); err != http.ErrServerClosed {
		log.Fatalf("Server error: %v", err)
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
