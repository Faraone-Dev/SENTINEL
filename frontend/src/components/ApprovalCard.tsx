import React from 'react';
import { motion } from 'framer-motion';
import {
  AlertTriangle,
  Trash2,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import type { Approval } from './types';
import { cn, getRiskColor, shortenAddress, getExplorerUrl, EXPLORER_URLS } from './constants';

export const ApprovalCard: React.FC<{
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
