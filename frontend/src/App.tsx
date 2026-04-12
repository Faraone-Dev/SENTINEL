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
import { ConnectButton } from '@rainbow-me/rainbowkit';
import { useAccount, useWriteContract, useSwitchChain } from 'wagmi';
import {
  Shield,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader2,
  Wallet,
  RefreshCw,
  FileCode,
  Cpu,
  Lock,
  Eye,
  Globe,
  ArrowUpDown,
  Search,
} from 'lucide-react';
import { ERC20_ABI, CHAIN_ID_MAP } from './wagmi';

// ── Component imports ────────────────────────────────────────────────────────
import {
  ErrorBoundary,
  RiskGauge,
  ApprovalCard,
  ChainSelector,
  ContractAnalysisCard,
  ParticlesBackground,
  CurvedText,
  AnimatedShield,
  FeatureCard,
  // Constants & utilities
  SUPPORTED_CHAINS,
  API_BASE,
  cn,
  deriveRiskSummary,
  // Types
  type Approval,
  type ScanResult,
  type ContractAnalysis,
} from './components';

// ═══════════════════════════════════════════════════════════════════════════════
//                              MAIN APP
// ═══════════════════════════════════════════════════════════════════════════════

const App: React.FC = () => {
  // Wallet connection via wagmi
  const { address: connectedAddress, isConnected } = useAccount();
  const { writeContractAsync } = useWriteContract();
  const { switchChainAsync } = useSwitchChain();

  // Results scroll ref
  const resultsRef = useRef<HTMLDivElement>(null);

  const [walletAddress, setWalletAddress] = useState('');
  const [contractAddress, setContractAddress] = useState('');
  const [selectedChains, setSelectedChains] = useState<string[]>(
    SUPPORTED_CHAINS.map((c) => c.id)
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

  // Auto-fill wallet address when wallet connects
  useEffect(() => {
    if (isConnected && connectedAddress && !walletAddress) {
      setWalletAddress(connectedAddress);
    }
  }, [isConnected, connectedAddress]);

  // ── Scan wallet ──────────────────────────────────────────────────────────
  const performScan = useCallback(
    async (address: string) => {
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

        if (!response.ok) throw new Error('Scan failed');

        const result = await response.json();
        setScanResult(result);

        setTimeout(() => {
          resultsRef.current?.scrollIntoView({ behavior: 'smooth' });
        }, 300);
      } catch (err) {
        setError('Failed to scan wallet. Please try again.');
        console.error(err);
      } finally {
        setIsScanning(false);
      }
    },
    [selectedChains]
  );

  const handleScan = () => performScan(walletAddress);

  // ── Analyze contract ─────────────────────────────────────────────────────
  const handleAnalyze = useCallback(async () => {
    if (!contractAddress || contractAddress.length !== 42) {
      setError('Please enter a valid contract address');
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    setContractAnalysis(null);

    try {
      const query = new URLSearchParams({
        contract: contractAddress,
        chain: selectedChain,
      });
      const response = await fetch(`${API_BASE}/api/v1/analyze?${query.toString()}`);

      if (!response.ok) throw new Error('Analysis failed');

      const result = await response.json();
      setContractAnalysis(result);

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

  // ── Revoke approval (on-chain via wagmi) ─────────────────────────────────
  const handleRevoke = useCallback(
    async (approval: Approval) => {
      if (!isConnected) {
        setError('Please connect your wallet first to revoke approvals');
        return;
      }

      const key = `${approval.tokenAddress}-${approval.spenderAddress}`;
      setRevokingApprovals((prev) => new Set([...prev, key]));

      try {
        const targetChainId = CHAIN_ID_MAP[approval.chain];
        if (targetChainId) {
          try {
            await switchChainAsync({ chainId: targetChainId });
          } catch {
            // User may have rejected chain switch, or already on correct chain
          }
        }

        await writeContractAsync({
          address: approval.tokenAddress as `0x${string}`,
          abi: ERC20_ABI,
          functionName: 'approve',
          args: [approval.spenderAddress as `0x${string}`, BigInt(0)],
        });

        // Remove from UI on success
        setScanResult((prev) => {
          if (!prev) return null;
          const updatedApprovals = prev.approvals.filter(
            (a) =>
              !(
                a.tokenAddress === approval.tokenAddress &&
                a.spenderAddress === approval.spenderAddress
              )
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
      } catch (err: any) {
        const msg = err?.shortMessage || err?.message || 'Revoke transaction failed';
        setError(`Revoke failed: ${msg}`);
        console.error('Revoke failed:', err);
      } finally {
        setRevokingApprovals((prev) => {
          const next = new Set(prev);
          next.delete(key);
          return next;
        });
      }
    },
    [isConnected, writeContractAsync, switchChainAsync]
  );

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-slate-900 text-white overflow-x-hidden">
      {/* ═══════════════════════════════════════════════════════════════════
          HERO SECTION
      ════════════════════════════════════════════════════════════════════ */}
      <section className="relative min-h-[90vh] flex flex-col">
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
            <ConnectButton showBalance={false} chainStatus="icon" accountStatus="address" />
          </div>
        </header>

        {/* Hero Content */}
        <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-6 pt-0 pb-4">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="w-full max-w-md h-20 mb-2"
          >
            <CurvedText />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="relative mb-2"
          >
            <AnimatedShield />
          </motion.div>

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
                'flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium transition-all text-sm',
                activeTab === 'scan'
                  ? 'bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-lg shadow-cyan-500/20'
                  : 'text-gray-400 hover:text-white'
              )}
            >
              <Wallet size={16} />
              Wallet Scan
            </button>
            <button
              onClick={() => setActiveTab('analyze')}
              className={cn(
                'flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium transition-all text-sm',
                activeTab === 'analyze'
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:text-white'
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
                      'px-6 py-3 rounded-xl font-semibold transition-all flex items-center gap-2 text-sm',
                      isScanning
                        ? 'bg-slate-700 cursor-not-allowed'
                        : 'bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 shadow-lg shadow-cyan-500/20'
                    )}
                  >
                    {isScanning ? <Loader2 className="animate-spin" size={18} /> : <RefreshCw size={18} />}
                    {isScanning ? 'Scanning...' : 'Scan'}
                  </button>
                </div>
                <ChainSelector selectedChains={selectedChains} onChange={setSelectedChains} />
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
                      'px-6 py-3 rounded-xl font-semibold transition-all flex items-center gap-2 text-sm',
                      isAnalyzing
                        ? 'bg-slate-700 cursor-not-allowed'
                        : 'bg-purple-600 hover:bg-purple-500 shadow-lg shadow-purple-500/20'
                    )}
                  >
                    {isAnalyzing ? <Loader2 className="animate-spin" size={18} /> : <Cpu size={18} />}
                    {isAnalyzing ? 'Analyzing...' : 'Analyze'}
                  </button>
                </div>
                <select
                  value={selectedChain}
                  onChange={(e) => setSelectedChain(e.target.value)}
                  aria-label="Select blockchain network"
                  className="px-4 py-2 rounded-xl bg-slate-800/80 border border-slate-700 text-white focus:border-purple-500 outline-none text-sm"
                >
                  {SUPPORTED_CHAINS.map((chain) => (
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
            <FeatureCard icon={Cpu} title="Smart Analysis" description="Contract decompiler" delay={1.1} />
            <FeatureCard icon={Lock} title="One-Click" description="Instant revoke access" delay={1.2} />
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          RESULTS SECTION
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
                  <div className="text-4xl font-bold text-red-500">{scanResult.criticalRisks}</div>
                </div>
                <div className="p-6 rounded-xl bg-amber-500/10 border border-amber-500/30">
                  <div className="text-amber-400 mb-2">Warnings</div>
                  <div className="text-4xl font-bold text-amber-500">{scanResult.warnings}</div>
                </div>
              </div>

              {/* Recommendations */}
              {scanResult.recommendations.length > 0 && (
                <div className="mb-8 p-6 rounded-xl bg-blue-500/10 border border-blue-500/30">
                  <h3 className="text-lg font-semibold text-blue-400 mb-4">Recommendations</h3>
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
                  <div className="flex gap-1 bg-gray-800/50 rounded-lg p-1">
                    <button
                      onClick={() => setFilter('all')}
                      className={cn(
                        'px-3 py-1.5 rounded-md text-sm font-medium transition-all',
                        filter === 'all' ? 'bg-cyan-500 text-white' : 'text-gray-400 hover:text-white'
                      )}
                    >
                      All ({scanResult.approvals.length})
                    </button>
                    <button
                      onClick={() => setFilter('critical')}
                      className={cn(
                        'px-3 py-1.5 rounded-md text-sm font-medium transition-all',
                        filter === 'critical' ? 'bg-red-500 text-white' : 'text-gray-400 hover:text-white'
                      )}
                    >
                      Critical ({scanResult.approvals.filter((a) => a.riskLevel === 'critical').length})
                    </button>
                    <button
                      onClick={() => setFilter('warning')}
                      className={cn(
                        'px-3 py-1.5 rounded-md text-sm font-medium transition-all',
                        filter === 'warning' ? 'bg-amber-500 text-white' : 'text-gray-400 hover:text-white'
                      )}
                    >
                      Warning ({scanResult.approvals.filter((a) => a.riskLevel === 'warning').length})
                    </button>
                    <button
                      onClick={() => setFilter('safe')}
                      className={cn(
                        'px-3 py-1.5 rounded-md text-sm font-medium transition-all',
                        filter === 'safe' ? 'bg-emerald-500 text-white' : 'text-gray-400 hover:text-white'
                      )}
                    >
                      Safe ({scanResult.approvals.filter((a) => a.riskLevel === 'safe').length})
                    </button>
                  </div>
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
                    .filter((a) => filter === 'all' || a.riskLevel === filter)
                    .sort((a, b) => {
                      if (sortBy === 'risk') {
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
          <p>Built by Faraone-Dev</p>
          <p className="text-sm mt-2">
            SENTINEL SHIELD - 16-Chain Wallet Security Scanner &amp; Contract Analyzer
          </p>
          <div className="flex flex-wrap justify-center gap-2 mt-4 text-xs">
            {SUPPORTED_CHAINS.map((chain) => (
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

export default function WrappedApp() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}
