import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertTriangle,
  ChevronDown,
  FileCode,
  Cpu,
  Activity,
} from 'lucide-react';
import type { ContractAnalysis } from './types';
import { cn, shortenAddress } from './constants';

export const ContractAnalysisCard: React.FC<{
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
