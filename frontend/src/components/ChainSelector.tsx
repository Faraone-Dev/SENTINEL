import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, ChevronDown } from 'lucide-react';
import { cn, SUPPORTED_CHAINS } from './constants';

export const ChainSelector: React.FC<{
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
            <div className="flex gap-2 mb-2 px-2">
              <button onClick={selectAll} className="text-xs text-blue-400 hover:underline">
                Select All
              </button>
              <span className="text-gray-600">|</span>
              <button onClick={selectNone} className="text-xs text-gray-400 hover:underline">
                Clear
              </button>
            </div>

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
