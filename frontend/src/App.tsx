/*
 ██████╗ ███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗
██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║
███████╗ █████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║
╚════██║ ██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║
███████║ ███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
╚══════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝

SENTINEL SHIELD - Single Page Application
Hero + Dashboard Integrated
*/

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Shield, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  Loader2,
  Wallet,
  RefreshCw,
  Trash2,
  ExternalLink,
  ChevronDown,
  Search,
  FileCode,
  Activity,
  Cpu,
  Zap,
  Lock,
  Eye,
  Globe,
  ArrowUpDown,
  Filter
} from 'lucide-react';

// ═══════════════════════════════════════════════════════════════════════════════
//                              TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface Approval {
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

interface ContractRisk {
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

interface ContractAnalysis {
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

interface ScanResult {
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

type Chain = {
  id: string;
  name: string;
  icon: string;
  color: string;
};

// ═══════════════════════════════════════════════════════════════════════════════
//                              CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

const SUPPORTED_CHAINS: Chain[] = [
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

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8080';

// Block Explorer URLs per chain
const EXPLORER_URLS: Record<string, string> = {
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

// Get explorer URL for address
const getExplorerUrl = (chain: string, address: string, type: 'address' | 'token' = 'address') => {
  const baseUrl = EXPLORER_URLS[chain] || EXPLORER_URLS.ethereum;
  return `${baseUrl}/${type}/${address}`;
};

// ═══════════════════════════════════════════════════════════════════════════════
//                              UTILITIES
// ═══════════════════════════════════════════════════════════════════════════════

const cn = (...classes: (string | boolean | undefined)[]) => 
  classes.filter(Boolean).join(' ');

const shortenAddress = (address?: string) => 
  address ? `${address.slice(0, 6)}...${address.slice(-4)}` : 'Unknown';

const getRiskColor = (level: string) => {
  switch (level) {
    case 'critical': return 'text-red-500 bg-red-500/10 border-red-500/30';
    case 'warning': return 'text-amber-500 bg-amber-500/10 border-amber-500/30';
    case 'safe': return 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30';
    default: return 'text-gray-500 bg-gray-500/10 border-gray-500/30';
  }
};

const deriveRiskSummary = (approvals: Approval[]) => {
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

// ═══════════════════════════════════════════════════════════════════════════════
//                              COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

// Risk Score Gauge
const RiskGauge: React.FC<{ score: number }> = ({ score }) => {
  const rotation = (score / 100) * 180 - 90;
  const getColor = () => {
    if (score >= 70) return '#ef4444';
    if (score >= 40) return '#f59e0b';
    return '#10b981';
  };

  return (
    <div className="relative w-48 h-24 overflow-hidden">
      <div className="absolute inset-0 border-8 border-gray-700 rounded-t-full" />
      <motion.div
        className="absolute bottom-0 left-1/2 w-1 h-20 origin-bottom -ml-0.5"
        style={{ backgroundColor: getColor() }}
        initial={{ rotate: -90 }}
        animate={{ rotate: rotation }}
        transition={{ type: 'spring', damping: 15 }}
      />
      <div className="absolute bottom-2 left-1/2 -translate-x-1/2 text-2xl font-bold">
        {score}
      </div>
    </div>
  );
};

// Approval Card
const ApprovalCard: React.FC<{ 
  approval: Approval; 
  onRevoke: () => void;
  isRevoking: boolean;
}> = ({ approval, onRevoke, isRevoking }) => {
  const tokenSymbol = approval.tokenSymbol || 'UNKNOWN';
  const spenderName = approval.spenderName || 'Unknown Contract';
  const chain = approval.chain || 'ethereum';
  
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -100 }}
      className={cn(
        "p-4 rounded-xl border backdrop-blur-sm",
        getRiskColor(approval.riskLevel)
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Token Info */}
          <div className="w-10 h-10 rounded-full bg-gray-800 flex items-center justify-center">
            <span className="text-lg font-bold">
              {tokenSymbol.slice(0, 2)}
            </span>
          </div>
          <div>
            <a 
              href={getExplorerUrl(chain, approval.tokenAddress, 'token')}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold hover:text-cyan-400 transition-colors"
            >
              {tokenSymbol}
            </a>
            <a 
              href={getExplorerUrl(chain, approval.tokenAddress, 'address')}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-gray-400 hover:text-cyan-400 transition-colors block"
            >
              {shortenAddress(approval.tokenAddress)}
            </a>
          </div>
        </div>

        {/* Chain & Risk Badge */}
        <div className="flex items-center gap-2">
          <div className="px-2 py-1 rounded bg-gray-800 text-xs text-gray-300 uppercase">
            {chain}
          </div>
          <div className={cn(
            "px-3 py-1 rounded-full text-xs font-medium uppercase",
            getRiskColor(approval.riskLevel)
          )}>
            {approval.riskLevel}
          </div>
        </div>
      </div>

      {/* Spender Info */}
      <div className="mt-4 p-3 rounded-lg bg-gray-800/50">
        <div className="text-sm text-gray-400">Approved Spender</div>
        <div className="flex items-center justify-between mt-1">
          <div>
            <div className="font-medium">{spenderName}</div>
            <a 
              href={getExplorerUrl(chain, approval.spenderAddress, 'address')}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-gray-500 hover:text-cyan-400 transition-colors"
            >
              {shortenAddress(approval.spenderAddress)}
            </a>
          </div>
          <a
            href={getExplorerUrl(chain, approval.spenderAddress, 'address')}
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
            title={`View on ${EXPLORER_URLS[chain] ? new URL(EXPLORER_URLS[chain]).hostname : 'Explorer'}`}
          >
            <ExternalLink size={16} />
          </a>
        </div>
      </div>

      {/* Allowance */}
      <div className="mt-3 flex items-center justify-between">
        <div>
          <span className="text-sm text-gray-400">Allowance: </span>
          <span className={cn(
            "font-medium",
            approval.isUnlimited && "text-red-400"
          )}>
            {approval.isUnlimited ? '∞ UNLIMITED' : approval.allowanceHuman}
          </span>
        </div>
        
        {/* Revoke Button */}
        <button
          onClick={onRevoke}
          disabled={isRevoking}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all",
            "bg-red-500/20 text-red-400 hover:bg-red-500/30",
            isRevoking && "opacity-50 cursor-not-allowed"
          )}
        >
          {isRevoking ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Trash2 size={16} />
          )}
          Revoke
        </button>
      </div>

      {/* Risk Reasons */}
      {approval.riskReasons && approval.riskReasons.length > 0 && (
        <div className="mt-3 space-y-1">
          {approval.riskReasons.map((reason, i) => (
            <div key={i} className="flex items-center gap-2 text-sm text-gray-400">
              <AlertTriangle size={12} />
              {reason}
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
};

// Chain Selector
const ChainSelector: React.FC<{
  selectedChains: string[];
  onChange: (chains: string[]) => void;
}> = ({ selectedChains, onChange }) => {
  const [isOpen, setIsOpen] = useState(false);

  const toggleChain = (chainId: string) => {
    if (selectedChains.includes(chainId)) {
      onChange(selectedChains.filter(c => c !== chainId));
    } else {
      onChange([...selectedChains, chainId]);
    }
  };

  const selectAll = () => onChange(SUPPORTED_CHAINS.map(c => c.id));
  const selectNone = () => onChange([]);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gray-800 border border-gray-700 hover:border-gray-600 transition-colors"
      >
        <span>{selectedChains.length} / {SUPPORTED_CHAINS.length} chains selected</span>
        <ChevronDown size={16} className={cn("transition-transform", isOpen && "rotate-180")} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="absolute top-full mt-2 left-0 w-72 p-2 rounded-xl bg-gray-800 border border-gray-700 shadow-xl z-50 max-h-96 overflow-y-auto"
          >
            {/* Quick Actions */}
            <div className="flex gap-2 mb-2 px-2">
              <button onClick={selectAll} className="text-xs text-blue-400 hover:underline">
                Select All
              </button>
              <span className="text-gray-600">|</span>
              <button onClick={selectNone} className="text-xs text-gray-400 hover:underline">
                Clear
              </button>
            </div>
            
            {/* L2 Section */}
            <div className="px-2 py-1 text-xs text-gray-500 uppercase">Ethereum L2s</div>
            {SUPPORTED_CHAINS.slice(0, 8).map(chain => (
              <button
                key={chain.id}
                onClick={() => toggleChain(chain.id)}
                className={cn(
                  "flex items-center gap-3 w-full px-3 py-2 rounded-lg transition-colors",
                  selectedChains.includes(chain.id) 
                    ? "bg-blue-500/20 text-blue-400" 
                    : "hover:bg-gray-700"
                )}
              >
                <span>{chain.icon}</span>
                <span>{chain.name}</span>
                {selectedChains.includes(chain.id) && (
                  <CheckCircle size={16} className="ml-auto" />
                )}
              </button>
            ))}
            
            {/* Alt L1 Section */}
            <div className="px-2 py-1 text-xs text-gray-500 uppercase mt-2">Alt L1s</div>
            {SUPPORTED_CHAINS.slice(8).map(chain => (
              <button
                key={chain.id}
                onClick={() => toggleChain(chain.id)}
                className={cn(
                  "flex items-center gap-3 w-full px-3 py-2 rounded-lg transition-colors",
                  selectedChains.includes(chain.id) 
                    ? "bg-blue-500/20 text-blue-400" 
                    : "hover:bg-gray-700"
                )}
              >
                <span>{chain.icon}</span>
                <span>{chain.name}</span>
                {selectedChains.includes(chain.id) && (
                  <CheckCircle size={16} className="ml-auto" />
                )}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// Contract Analysis Card
const ContractAnalysisCard: React.FC<{
  analysis: ContractAnalysis;
}> = ({ analysis }) => {
  const [expanded, setExpanded] = useState(false);
  
  const getRiskBadge = (risk: string) => {
    switch (risk) {
      case 'critical': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'high': return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      case 'medium': return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'low': return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-4 rounded-xl bg-gray-800/50 border border-gray-700"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
            <FileCode size={20} className="text-purple-400" />
          </div>
          <div>
            <div className="font-mono text-sm">{shortenAddress(analysis.address)}</div>
            <div className="text-xs text-gray-500">{analysis.chain}</div>
          </div>
        </div>
        <div className={cn("px-3 py-1 rounded-full text-xs font-medium uppercase border", getRiskBadge(analysis.overallRisk))}>
          {analysis.overallRisk} Risk
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-4 mt-4">
        <div className="p-3 rounded-lg bg-gray-900/50">
          <div className="text-xs text-gray-500">Functions</div>
          <div className="text-xl font-bold">{analysis.decompilerResult.functions.length}</div>
        </div>
        <div className="p-3 rounded-lg bg-gray-900/50">
          <div className="text-xs text-gray-500">Vulnerabilities</div>
          <div className="text-xl font-bold text-red-400">
            {analysis.analyzerResult.vulnerabilities.length}
          </div>
        </div>
        <div className="p-3 rounded-lg bg-gray-900/50">
          <div className="text-xs text-gray-500">Risk Score</div>
          <div className="text-xl font-bold">{analysis.analyzerResult.riskScore}/100</div>
        </div>
      </div>

      {/* Expand Button */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full mt-4 py-2 text-sm text-gray-400 hover:text-white flex items-center justify-center gap-2"
      >
        <ChevronDown size={16} className={cn("transition-transform", expanded && "rotate-180")} />
        {expanded ? 'Hide Details' : 'Show Details'}
      </button>

      {/* Expanded Details */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            {/* Decompiler Results */}
            <div className="mt-4 p-4 rounded-lg bg-gray-900/50">
              <div className="flex items-center gap-2 mb-3">
                <Cpu size={16} className="text-blue-400" />
                <span className="font-semibold">Decompiler Analysis</span>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Complexity:</span>
                  <span className="capitalize">{analysis.decompilerResult.complexity}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Storage Slots:</span>
                  <span>{analysis.decompilerResult.storageSlots}</span>
                </div>
                <div>
                  <span className="text-gray-400">Detected Patterns:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {analysis.decompilerResult.patterns.map((p, i) => (
                      <span key={i} className="px-2 py-0.5 text-xs rounded bg-blue-500/20 text-blue-400">
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Vulnerabilities */}
            {analysis.analyzerResult.vulnerabilities.length > 0 && (
              <div className="mt-4 p-4 rounded-lg bg-red-500/5 border border-red-500/20">
                <div className="flex items-center gap-2 mb-3">
                  <AlertTriangle size={16} className="text-red-400" />
                  <span className="font-semibold text-red-400">Vulnerabilities Detected</span>
                </div>
                <div className="space-y-2">
                  {analysis.analyzerResult.vulnerabilities.map((v, i) => (
                    <div key={i} className="p-2 rounded bg-gray-800/50 text-sm">
                      <div className="flex items-center gap-2">
                        <span className={cn(
                          "px-2 py-0.5 rounded text-xs uppercase",
                          v.severity === 'critical' ? 'bg-red-500/20 text-red-400' :
                          v.severity === 'high' ? 'bg-orange-500/20 text-orange-400' :
                          'bg-amber-500/20 text-amber-400'
                        )}>
                          {v.severity}
                        </span>
                        <span className="font-medium">{v.type}</span>
                      </div>
                      <p className="text-gray-400 mt-1">{v.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Suggestions */}
            {analysis.analyzerResult.suggestions.length > 0 && (
              <div className="mt-4 p-4 rounded-lg bg-blue-500/5 border border-blue-500/20">
                <div className="flex items-center gap-2 mb-3">
                  <Activity size={16} className="text-blue-400" />
                  <span className="font-semibold text-blue-400">Security Suggestions</span>
                </div>
                <ul className="space-y-1 text-sm text-gray-300">
                  {analysis.analyzerResult.suggestions.map((s, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-blue-400">•</span>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
//                              HERO COMPONENTS (INTEGRATED)
// ═══════════════════════════════════════════════════════════════════════════════

// Particles Background
const ParticlesBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    const particles: { x: number; y: number; vx: number; vy: number; size: number; opacity: number }[] = [];
    for (let i = 0; i < 80; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        size: Math.random() * 2 + 0.5,
        opacity: Math.random() * 0.5 + 0.2,
      });
    }

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 255, 209, ${p.opacity})`;
        ctx.fill();
      });
      particles.forEach((p1, i) => {
        particles.slice(i + 1).forEach((p2) => {
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(0, 255, 209, ${0.1 * (1 - dist / 120)})`;
            ctx.stroke();
          }
        });
      });
      requestAnimationFrame(animate);
    };
    animate();

    return () => window.removeEventListener('resize', resize);
  }, []);

  return <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none" />;
};

// Curved Text - Simple arc above shield
const CurvedText: React.FC = () => {
  return (
    <svg viewBox="0 0 500 100" className="w-full h-full">
      <defs>
        <path id="curve" d="M 50,90 Q 250,10 450,90" fill="transparent" />
        <linearGradient id="textGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#00ffd1" />
          <stop offset="50%" stopColor="#00d4ff" />
          <stop offset="100%" stopColor="#0066ff" />
        </linearGradient>
      </defs>
      <text
        fill="url(#textGradient)"
        fontSize="48"
        fontWeight="bold"
        fontFamily="monospace"
        style={{ filter: 'drop-shadow(0 0 20px rgba(0, 255, 209, 0.9))' }}
      >
        <textPath href="#curve" startOffset="50%" textAnchor="middle">
          SENTINEL
        </textPath>
      </text>
    </svg>
  );
};

// Animated Shield
const AnimatedShield: React.FC = () => (
  <div className="relative w-32 h-32 md:w-40 md:h-40">
    <motion.div
      className="absolute inset-0 rounded-full"
      style={{
        background: 'radial-gradient(circle, rgba(0, 255, 209, 0.3) 0%, transparent 70%)',
      }}
      animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.8, 0.5] }}
      transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
    />
    <div className="absolute inset-0 flex items-center justify-center">
      <Shield
        className="w-16 h-16 md:w-20 md:h-20"
        style={{
          color: '#00ffd1',
          filter: 'drop-shadow(0 0 20px rgba(0, 255, 209, 0.8)) drop-shadow(0 0 40px rgba(0, 255, 209, 0.4))',
        }}
      />
    </div>
  </div>
);

// Feature Card
const FeatureCard: React.FC<{ icon: React.ElementType; title: string; description: string; delay: number }> = ({
  icon: Icon,
  title,
  description,
  delay,
}) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.6, delay }}
    whileHover={{ scale: 1.02, y: -4 }}
    className="relative p-5 rounded-xl bg-slate-800/40 border border-slate-700/50 backdrop-blur-sm hover:border-cyan-500/30 transition-all duration-300 group"
  >
    <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-cyan-500/5 to-blue-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
    <div className="relative">
      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20 flex items-center justify-center mb-3">
        <Icon className="w-5 h-5 text-cyan-400" />
      </div>
      <h3 className="text-base font-semibold text-white mb-1">{title}</h3>
      <p className="text-sm text-slate-400 leading-relaxed">{description}</p>
    </div>
  </motion.div>
);

// ═══════════════════════════════════════════════════════════════════════════════
//                              MAIN APP
// ═══════════════════════════════════════════════════════════════════════════════

const App: React.FC = () => {
  // Risultati scroll ref
  const resultsRef = useRef<HTMLDivElement>(null);
  
  const [walletAddress, setWalletAddress] = useState('');
  const [contractAddress, setContractAddress] = useState('');
  const [selectedChains, setSelectedChains] = useState<string[]>(
    SUPPORTED_CHAINS.map(c => c.id)
  );
  const [selectedChain, setSelectedChain] = useState('ethereum');
  const [activeTab, setActiveTab] = useState<'scan' | 'analyze'>('scan');
  const [isScanning, setIsScanning] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [contractAnalysis, setContractAnalysis] = useState<ContractAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revokingApprovals, setRevokingApprovals] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<'all' | 'critical' | 'warning' | 'safe'>('all');
  const [sortBy, setSortBy] = useState<'risk' | 'token'>('risk');

  // Scan wallet function
  const performScan = useCallback(async (address: string) => {
    if (!address || address.length !== 42) {
      setError('Please enter a valid Ethereum address');
      return;
    }

    setIsScanning(true);
    setError(null);
    setScanResult(null);

    try {
      const chainsParam = selectedChains.join(',');
      const response = await fetch(
        `${API_BASE}/api/v1/scan?wallet=${address}&chains=${chainsParam}`
      );
      
      if (!response.ok) {
        throw new Error('Scan failed');
      }

      const result = await response.json();
      setScanResult(result);
      
      // Scroll to results
      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 300);
    } catch (err) {
      setError('Failed to scan wallet. Please try again.');
      console.error(err);
    } finally {
      setIsScanning(false);
    }
  }, [selectedChains]);

  // Scan wallet (manual trigger)
  const handleScan = () => {
    performScan(walletAddress);
  };

  // Analyze contract
  const handleAnalyze = useCallback(async () => {
    if (!contractAddress || contractAddress.length !== 42) {
      setError('Please enter a valid contract address');
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    setContractAnalysis(null);

    try {
      const response = await fetch(`${API_BASE}/api/v1/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: contractAddress,
          chain: selectedChain,
        }),
      });
      
      if (!response.ok) {
        throw new Error('Analysis failed');
      }

      const result = await response.json();
      setContractAnalysis(result);
      
      // Scroll to results
      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 300);
    } catch (err) {
      setError('Failed to analyze contract. Make sure the API server is running.');
      console.error(err);
    } finally {
      setIsAnalyzing(false);
    }
  }, [contractAddress, selectedChain]);

  // Revoke approval
  const handleRevoke = useCallback(async (approval: Approval) => {
    const key = `${approval.tokenAddress}-${approval.spenderAddress}`;
    setRevokingApprovals(prev => new Set([...prev, key]));

    try {
      await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate

      setScanResult(prev => {
        if (!prev) return null;
        const updatedApprovals = prev.approvals.filter(
          a => !(a.tokenAddress === approval.tokenAddress &&
                 a.spenderAddress === approval.spenderAddress)
        );
        const summary = deriveRiskSummary(updatedApprovals);

        return {
          ...prev,
          approvals: updatedApprovals,
          totalApprovals: summary.totalApprovals,
          criticalRisks: summary.criticalRisks,
          warnings: summary.warnings,
          overallRiskScore: summary.overallRiskScore,
          recommendations: summary.recommendations,
        };
      });
    } catch (err) {
      console.error('Revoke failed:', err);
    } finally {
      setRevokingApprovals(prev => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    }
  }, []);

  // Show Hero page - AFTER all hooks!
  // REMOVED: Now single integrated page

  return (
    <div className="min-h-screen bg-slate-900 text-white overflow-x-hidden">
      {/* ═══════════════════════════════════════════════════════════════════
          HERO SECTION - Integrated at top
      ════════════════════════════════════════════════════════════════════ */}
      <section className="relative min-h-[90vh] flex flex-col">
        {/* Particles Background */}
        <ParticlesBackground />
        
        {/* Gradient Overlays */}
        <div className="absolute inset-0 bg-gradient-to-b from-slate-900/50 via-transparent to-slate-900 pointer-events-none" />
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyan-500/20 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-blue-500/15 rounded-full blur-3xl" />
        
        {/* Header */}
        <header className="relative z-10 px-6 py-2">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Shield className="w-7 h-7 text-cyan-400 drop-shadow-[0_0_10px_rgba(0,255,209,0.5)]" />
              <span className="text-lg font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
                SENTINEL SHIELD
              </span>
            </div>
            <button className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 transition-all shadow-lg shadow-cyan-500/20 text-sm">
              <Wallet size={16} />
              Connect Wallet
            </button>
          </div>
        </header>

        {/* Hero Content */}
        <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-6 pt-0 pb-4">
          {/* Curved Text Banner */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="w-full max-w-md h-20 mb-2"
          >
            <CurvedText />
          </motion.div>
          
          {/* Shield */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="relative mb-2"
          >
            <AnimatedShield />
          </motion.div>

          {/* Title & Subtitle */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="text-3xl md:text-4xl font-bold text-center mb-1"
          >
            <span className="bg-gradient-to-r from-white via-cyan-200 to-white bg-clip-text text-transparent">
              Multi-Chain Wallet Security Scanner
            </span>
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="text-slate-400 text-center max-w-xl mb-6"
          >
            Scan token approvals across 16 EVM chains. Analyze smart contracts for vulnerabilities.
          </motion.p>

          {/* Tab Selector */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="flex bg-slate-800/50 backdrop-blur rounded-xl p-1 border border-slate-700/50 mb-4"
          >
            <button
              onClick={() => setActiveTab('scan')}
              className={cn(
                "flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium transition-all text-sm",
                activeTab === 'scan' 
                  ? "bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-lg shadow-cyan-500/20" 
                  : "text-gray-400 hover:text-white"
              )}
            >
              <Wallet size={16} />
              Wallet Scan
            </button>
            <button
              onClick={() => setActiveTab('analyze')}
              className={cn(
                "flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium transition-all text-sm",
                activeTab === 'analyze' 
                  ? "bg-purple-600 text-white" 
                  : "text-gray-400 hover:text-white"
              )}
            >
              <FileCode size={16} />
              Contract Analysis
            </button>
          </motion.div>

          {/* Input Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 }}
            className="w-full max-w-xl"
          >
            {activeTab === 'scan' ? (
              <div className="flex flex-col gap-3">
                <div className="flex gap-3">
                  <div className="flex-1 relative">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                    <input
                      type="text"
                      value={walletAddress}
                      onChange={(e) => setWalletAddress(e.target.value)}
                      placeholder="Enter wallet address (0x...)"
                      className="w-full pl-11 pr-4 py-3 rounded-xl bg-slate-800/80 border border-slate-700 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 outline-none transition-all text-sm"
                      onKeyDown={(e) => e.key === 'Enter' && handleScan()}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handleScan}
                    disabled={isScanning}
                    className={cn(
                      "px-6 py-3 rounded-xl font-semibold transition-all flex items-center gap-2 text-sm",
                      isScanning 
                        ? "bg-slate-700 cursor-not-allowed" 
                        : "bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 shadow-lg shadow-cyan-500/20"
                    )}
                  >
                    {isScanning ? (
                      <Loader2 className="animate-spin" size={18} />
                    ) : (
                      <RefreshCw size={18} />
                    )}
                    {isScanning ? 'Scanning...' : 'Scan'}
                  </button>
                </div>
                <ChainSelector 
                  selectedChains={selectedChains}
                  onChange={setSelectedChains}
                />
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                <div className="flex gap-3">
                  <div className="flex-1 relative">
                    <FileCode className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                    <input
                      type="text"
                      value={contractAddress}
                      onChange={(e) => setContractAddress(e.target.value)}
                      placeholder="Enter contract address (0x...)"
                      className="w-full pl-11 pr-4 py-3 rounded-xl bg-slate-800/80 border border-slate-700 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none transition-all text-sm"
                      onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handleAnalyze}
                    disabled={isAnalyzing}
                    className={cn(
                      "px-6 py-3 rounded-xl font-semibold transition-all flex items-center gap-2 text-sm",
                      isAnalyzing 
                        ? "bg-slate-700 cursor-not-allowed" 
                        : "bg-purple-600 hover:bg-purple-500 shadow-lg shadow-purple-500/20"
                    )}
                  >
                    {isAnalyzing ? (
                      <Loader2 className="animate-spin" size={18} />
                    ) : (
                      <Cpu size={18} />
                    )}
                    {isAnalyzing ? 'Analyzing...' : 'Analyze'}
                  </button>
                </div>
                <select
                  value={selectedChain}
                  onChange={(e) => setSelectedChain(e.target.value)}
                  className="px-4 py-2 rounded-xl bg-slate-800/80 border border-slate-700 text-white focus:border-purple-500 outline-none text-sm"
                >
                  {SUPPORTED_CHAINS.map(chain => (
                    <option key={chain.id} value={chain.id}>
                      {chain.icon} {chain.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </motion.div>

          {/* Error */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="mt-4 max-w-xl w-full p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 flex items-center gap-2 text-sm"
              >
                <XCircle size={18} />
                {error}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Feature Cards */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-8 max-w-4xl w-full"
          >
            <FeatureCard icon={Globe} title="16 Chains" description="All major EVM networks" delay={0.9} />
            <FeatureCard icon={Eye} title="Deep Scan" description="Token approvals analysis" delay={1.0} />
            <FeatureCard icon={Cpu} title="AI Analysis" description="Smart contract decompiler" delay={1.1} />
            <FeatureCard icon={Lock} title="One-Click" description="Instant revoke access" delay={1.2} />
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          RESULTS SECTION - Shows below Hero when scan/analyze completes
      ════════════════════════════════════════════════════════════════════ */}
      <section ref={resultsRef} className="relative z-10 bg-slate-900">
        <AnimatePresence mode="wait">
          {/* Contract Analysis Results */}
          {activeTab === 'analyze' && contractAnalysis && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="max-w-7xl mx-auto px-6 py-12"
            >
              <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <Cpu className="text-purple-400" />
                Contract Analysis Results
              </h2>
              <div className="max-w-2xl mx-auto">
                <ContractAnalysisCard analysis={contractAnalysis} />
              </div>
            </motion.div>
          )}

          {/* Wallet Scan Results */}
          {activeTab === 'scan' && scanResult && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="max-w-7xl mx-auto px-6 py-12"
            >
              {/* Stats */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div className="p-6 rounded-xl bg-gray-800/50 border border-gray-700">
                  <div className="text-gray-400 mb-2">Risk Score</div>
                  <RiskGauge score={scanResult.overallRiskScore} />
                </div>
                <div className="p-6 rounded-xl bg-gray-800/50 border border-gray-700">
                  <div className="text-gray-400 mb-2">Total Approvals</div>
                  <div className="text-4xl font-bold">{scanResult.totalApprovals}</div>
                </div>
                <div className="p-6 rounded-xl bg-red-500/10 border border-red-500/30">
                  <div className="text-red-400 mb-2">Critical Risks</div>
                  <div className="text-4xl font-bold text-red-500">
                    {scanResult.criticalRisks}
                  </div>
                </div>
                <div className="p-6 rounded-xl bg-amber-500/10 border border-amber-500/30">
                  <div className="text-amber-400 mb-2">Warnings</div>
                  <div className="text-4xl font-bold text-amber-500">
                    {scanResult.warnings}
                  </div>
                </div>
              </div>

              {/* Recommendations */}
              {scanResult.recommendations.length > 0 && (
                <div className="mb-8 p-6 rounded-xl bg-blue-500/10 border border-blue-500/30">
                  <h3 className="text-lg font-semibold text-blue-400 mb-4">
                    Recommendations
                  </h3>
                  <ul className="space-y-2">
                    {scanResult.recommendations.map((rec, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <AlertTriangle size={18} className="mt-0.5 text-blue-400" />
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Approvals List */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
                <h2 className="text-2xl font-bold">Token Approvals</h2>
                <div className="flex flex-wrap items-center gap-2">
                  {/* Filter Buttons */}
                  <div className="flex gap-1 bg-gray-800/50 rounded-lg p-1">
                    <button
                      onClick={() => setFilter('all')}
                      className={cn(
                        "px-3 py-1.5 rounded-md text-sm font-medium transition-all",
                        filter === 'all' ? "bg-cyan-500 text-white" : "text-gray-400 hover:text-white"
                      )}
                    >
                      All ({scanResult.approvals.length})
                    </button>
                    <button
                      onClick={() => setFilter('critical')}
                      className={cn(
                        "px-3 py-1.5 rounded-md text-sm font-medium transition-all",
                        filter === 'critical' ? "bg-red-500 text-white" : "text-gray-400 hover:text-white"
                      )}
                    >
                      🚨 Critical ({scanResult.approvals.filter(a => a.riskLevel === 'critical').length})
                    </button>
                    <button
                      onClick={() => setFilter('warning')}
                      className={cn(
                        "px-3 py-1.5 rounded-md text-sm font-medium transition-all",
                        filter === 'warning' ? "bg-amber-500 text-white" : "text-gray-400 hover:text-white"
                      )}
                    >
                      ⚠️ Warning ({scanResult.approvals.filter(a => a.riskLevel === 'warning').length})
                    </button>
                    <button
                      onClick={() => setFilter('safe')}
                      className={cn(
                        "px-3 py-1.5 rounded-md text-sm font-medium transition-all",
                        filter === 'safe' ? "bg-emerald-500 text-white" : "text-gray-400 hover:text-white"
                      )}
                    >
                      ✅ Safe ({scanResult.approvals.filter(a => a.riskLevel === 'safe').length})
                    </button>
                  </div>
                  {/* Sort Button */}
                  <button
                    onClick={() => setSortBy(sortBy === 'risk' ? 'token' : 'risk')}
                    className="flex items-center gap-1 px-3 py-1.5 bg-gray-800/50 rounded-lg text-sm text-gray-400 hover:text-white transition-all"
                  >
                    <ArrowUpDown size={14} />
                    {sortBy === 'risk' ? 'By Risk' : 'By Token'}
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <AnimatePresence>
                  {scanResult.approvals
                    .filter(a => filter === 'all' || a.riskLevel === filter)
                    .sort((a, b) => {
                      if (sortBy === 'risk') {
                        // Safe (green) first, then warning (yellow), then critical (red)
                        const riskOrder = { safe: 0, warning: 1, critical: 2 };
                        return (riskOrder[a.riskLevel] || 3) - (riskOrder[b.riskLevel] || 3);
                      }
                      return (a.tokenSymbol || '').localeCompare(b.tokenSymbol || '');
                    })
                    .map((approval, index) => (
                    <ApprovalCard
                      key={`${approval.tokenAddress || index}-${approval.spenderAddress || index}-${index}`}
                      approval={approval}
                      onRevoke={() => handleRevoke(approval)}
                      isRevoking={revokingApprovals.has(
                        `${approval.tokenAddress}-${approval.spenderAddress}`
                      )}
                    />
                  ))}
                </AnimatePresence>
              </div>

              {scanResult.approvals.length === 0 && (
                <div className="text-center py-12 text-gray-500">
                  <CheckCircle size={48} className="mx-auto mb-4 text-emerald-500" />
                  <p className="text-xl">No risky approvals found!</p>
                  <p>Your wallet is clean.</p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-8 bg-slate-900">
        <div className="max-w-7xl mx-auto px-6 text-center text-gray-500">
          <p>Built by SENTINEL Team</p>
          <p className="text-sm mt-2">
            SENTINEL SHIELD - 16-Chain Wallet Security Scanner & Contract Analyzer
          </p>
          <div className="flex flex-wrap justify-center gap-2 mt-4 text-xs">
            {SUPPORTED_CHAINS.map(chain => (
              <span key={chain.id} className="px-2 py-1 rounded bg-gray-800">
                {chain.icon} {chain.name}
              </span>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
