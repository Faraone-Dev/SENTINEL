/*
  SENTINEL SHIELD - Constants & Utilities
*/

import type { Chain, Approval } from './types';

// ═══════════════════════════════════════════════════════════════════════════════
//                              CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

export const SUPPORTED_CHAINS: Chain[] = [
  // Ethereum L2s
  { id: 'ethereum', name: 'Ethereum', icon: '⟠', color: '#627EEA' },
  { id: 'arbitrum', name: 'Arbitrum', icon: '🔵', color: '#28A0F0' },
  { id: 'optimism', name: 'Optimism', icon: '🔴', color: '#FF0420' },
  { id: 'base', name: 'Base', icon: '🔷', color: '#0052FF' },
  { id: 'zksync', name: 'zkSync Era', icon: '⚡', color: '#8B8DFC' },
  { id: 'linea', name: 'Linea', icon: '📐', color: '#61DFFF' },
  { id: 'scroll', name: 'Scroll', icon: '📜', color: '#FFCB45' },
  { id: 'zkevm', name: 'Polygon zkEVM', icon: '🔐', color: '#7B3FE4' },
  // Alt L1s
  { id: 'bsc', name: 'BNB Chain', icon: '⬡', color: '#F3BA2F' },
  { id: 'polygon', name: 'Polygon PoS', icon: '⬢', color: '#8247E5' },
  { id: 'avalanche', name: 'Avalanche', icon: '🔺', color: '#E84142' },
  { id: 'fantom', name: 'Fantom', icon: '👻', color: '#1969FF' },
  { id: 'cronos', name: 'Cronos', icon: '🌙', color: '#002D74' },
  { id: 'gnosis', name: 'Gnosis', icon: '🦉', color: '#04795B' },
  { id: 'celo', name: 'Celo', icon: '🌿', color: '#35D07F' },
  { id: 'moonbeam', name: 'Moonbeam', icon: '🌙', color: '#53CBC9' },
];

export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8080';

// Block Explorer URLs per chain
export const EXPLORER_URLS: Record<string, string> = {
  ethereum: 'https://etherscan.io',
  arbitrum: 'https://arbiscan.io',
  optimism: 'https://optimistic.etherscan.io',
  base: 'https://basescan.org',
  zksync: 'https://explorer.zksync.io',
  linea: 'https://lineascan.build',
  scroll: 'https://scrollscan.com',
  zkevm: 'https://zkevm.polygonscan.com',
  bsc: 'https://bscscan.com',
  polygon: 'https://polygonscan.com',
  avalanche: 'https://snowtrace.io',
  fantom: 'https://ftmscan.com',
  cronos: 'https://cronoscan.com',
  gnosis: 'https://gnosisscan.io',
  celo: 'https://celoscan.io',
  moonbeam: 'https://moonscan.io',
};

// ═══════════════════════════════════════════════════════════════════════════════
//                              UTILITIES
// ═══════════════════════════════════════════════════════════════════════════════

// Get explorer URL for address
export const getExplorerUrl = (chain: string, address: string, type: 'address' | 'token' = 'address') => {
  const baseUrl = EXPLORER_URLS[chain] || EXPLORER_URLS.ethereum;
  return `${baseUrl}/${type}/${address}`;
};

export const cn = (...classes: (string | boolean | undefined)[]) =>
  classes.filter(Boolean).join(' ');

export const shortenAddress = (address?: string) =>
  address ? `${address.slice(0, 6)}...${address.slice(-4)}` : 'Unknown';

export const getRiskColor = (level: string) => {
  switch (level) {
    case 'critical': return 'text-red-500 bg-red-500/10 border-red-500/30';
    case 'warning': return 'text-amber-500 bg-amber-500/10 border-amber-500/30';
    case 'safe': return 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30';
    default: return 'text-gray-500 bg-gray-500/10 border-gray-500/30';
  }
};

export const deriveRiskSummary = (approvals: Approval[]) => {
  let criticalRisks = 0;
  let warnings = 0;
  let unlimitedCount = 0;

  approvals.forEach((approval) => {
    if (approval.riskLevel === 'critical') {
      criticalRisks += 1;
    } else if (approval.riskLevel === 'warning') {
      warnings += 1;
    }
    if (approval.isUnlimited) {
      unlimitedCount += 1;
    }
  });

  const overallRiskScore = Math.min(100, criticalRisks * 30 + warnings * 10);
  const recommendations: string[] = [];

  if (criticalRisks > 0) {
    recommendations.push(`⚠️ Revoke ${criticalRisks} critical approvals immediately`);
  }
  if (unlimitedCount > 5) {
    recommendations.push('Consider setting specific approval amounts instead of unlimited');
  }

  return {
    totalApprovals: approvals.length,
    criticalRisks,
    warnings,
    overallRiskScore,
    recommendations,
  };
};
