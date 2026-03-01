/*
  SENTINEL SHIELD - Shared Types
*/

export interface Approval {
  chain: string;
  tokenAddress: string;
  tokenSymbol?: string;
  spenderAddress: string;
  spenderName?: string;
  allowanceRaw: string;
  allowanceHuman: string;
  isUnlimited: boolean;
  riskLevel: 'critical' | 'warning' | 'safe';
  riskReasons: string[];
  lastUpdated: number;
}

export interface ContractRisk {
  address: string;
  chain: string;
  isVerified: boolean;
  isProxy: boolean;
  hasMint: boolean;
  hasBlacklist: boolean;
  hasPause: boolean;
  isHoneypot: boolean;
  hiddenFee: number;
  ownerPrivileges: string[];
  riskScore: number;
  riskLevel: string;
  vulnerabilities: string[];
}

export interface ContractAnalysis {
  address: string;
  chain: string;
  decompilerResult: {
    functions: string[];
    storageSlots: number;
    complexity: string;
    patterns: string[];
    cfg: string;
  };
  analyzerResult: {
    vulnerabilities: Array<{
      type: string;
      severity: string;
      description: string;
      location: string;
    }>;
    riskScore: number;
    patterns: string[];
    suggestions: string[];
  };
  overallRisk: string;
  timestamp: number;
}

export interface ScanResult {
  walletAddress: string;
  scanTimestamp: number;
  overallRiskScore: number;
  totalApprovals: number;
  criticalRisks: number;
  warnings: number;
  chainsScanned: string[];
  approvals: Approval[];
  contractRisks: ContractRisk[];
  recommendations: string[];
}

export type Chain = {
  id: string;
  name: string;
  icon: string;
  color: string;
};
