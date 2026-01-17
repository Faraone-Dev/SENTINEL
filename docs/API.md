# 📡 SENTINEL SHIELD - API Reference

## Base URL

```
http://localhost:8080/api/v1
```

---

## Endpoints

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "chains": 16
}
```

---

### Scan Wallet

```http
GET /api/v1/scan?wallet={address}&chains={chains}
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `wallet` | string | Yes | Ethereum address (0x...) |
| `chains` | string | No | Comma-separated chain IDs (default: all) |

**Example:**
```bash
curl "http://localhost:8080/api/v1/scan?wallet=0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
```

**Response:**
```json
{
  "walletAddress": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
  "scanTimestamp": 1737118400,
  "overallRiskScore": 100,
  "totalApprovals": 133,
  "criticalRisks": 46,
  "warnings": 46,
  "chainsScanned": ["ethereum", "arbitrum", "optimism", ...],
  "approvals": [
    {
      "chain": "ethereum",
      "tokenAddress": "0x6b17...",
      "tokenSymbol": "DAI",
      "spenderAddress": "0x68b3...",
      "spenderName": "Uniswap V3: Router 2",
      "allowanceRaw": "115792089237316195423570...",
      "allowanceHuman": "∞ UNLIMITED",
      "isUnlimited": true,
      "riskLevel": "critical",
      "riskReasons": ["Unlimited approval", "Unlimited allowance"]
    }
  ],
  "recommendations": [
    "🚨 URGENT: Revoke 46 critical approvals immediately",
    "⚠️ You have 46 unlimited approvals. Consider setting specific limits."
  ]
}
```

---

### Analyze Contract

```http
GET /api/v1/analyze?contract={address}&chain={chain}
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `contract` | string | Yes | Contract address |
| `chain` | string | No | Chain ID (default: ethereum) |

**Response:**
```json
{
  "address": "0x...",
  "chain": "ethereum",
  "bytecodeHash": "abc123...",
  "isVerified": true,
  "isProxy": false,
  "vulnerabilities": [
    {
      "type": "honeypot",
      "severity": "critical",
      "title": "Possible Honeypot",
      "description": "Contract may restrict selling",
      "confidence": 0.75
    }
  ],
  "riskScore": 85,
  "riskLevel": "critical"
}
```

---

### Batch Analyze

```http
POST /api/v1/analyze/batch
```

**Body:**
```json
{
  "contracts": [
    { "address": "0x...", "chain": "ethereum" },
    { "address": "0x...", "chain": "arbitrum" }
  ]
}
```

---

### List Supported Chains

```http
GET /api/v1/chains
```

**Response:**
```json
{
  "chains": [
    { "id": "ethereum", "name": "Ethereum", "chainId": 1 },
    { "id": "arbitrum", "name": "Arbitrum One", "chainId": 42161 },
    ...
  ]
}
```

---

## Error Responses

```json
{
  "error": "Invalid wallet address",
  "code": "INVALID_ADDRESS"
}
```

| Code | Description |
|------|-------------|
| `INVALID_ADDRESS` | Malformed Ethereum address |
| `CHAIN_NOT_SUPPORTED` | Unknown chain ID |
| `RATE_LIMITED` | Too many requests |
| `RPC_ERROR` | Chain RPC unavailable |
