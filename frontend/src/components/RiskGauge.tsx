import React from 'react';
import { motion } from 'framer-motion';

export const RiskGauge: React.FC<{ score: number }> = ({ score }) => {
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
