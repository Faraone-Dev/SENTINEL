/**
 * SENTINEL SHIELD - Component Unit Tests
 * Tests for all extracted components from the refactored App.tsx
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';

// ── Mock framer-motion ─────────────────────────────────────────────────────
vi.mock('framer-motion', () => ({
  motion: {
    div: React.forwardRef(({ children, initial, animate, exit, transition, whileHover, layout, ...props }: any, ref: any) => (
      <div ref={ref} {...props}>{children}</div>
    )),
    h1: React.forwardRef(({ children, ...props }: any, ref: any) => <h1 ref={ref} {...props}>{children}</h1>),
    p: React.forwardRef(({ children, ...props }: any, ref: any) => <p ref={ref} {...props}>{children}</p>),
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

// ── Mock lucide-react icons ────────────────────────────────────────────────
vi.mock('lucide-react', () => {
  const icon = ({ children, ...props }: any) => <span data-testid={`icon`} {...props} />;
  return {
    Shield: icon, AlertTriangle: icon, CheckCircle: icon, XCircle: icon,
    Loader2: icon, Wallet: icon, RefreshCw: icon, Trash2: icon,
    ExternalLink: icon, ChevronDown: icon, Search: icon, FileCode: icon,
    Activity: icon, Cpu: icon, Zap: icon, Lock: icon, Eye: icon,
    Globe: icon, ArrowUpDown: icon, Filter: icon,
  };
});

// ── Import components under test ───────────────────────────────────────────
import {
  cn,
  shortenAddress,
  getRiskColor,
  deriveRiskSummary,
  SUPPORTED_CHAINS,
  API_BASE,
  getExplorerUrl,
} from '../components/constants';
import type { Approval, ScanResult, ContractAnalysis } from '../components/types';

// ═══════════════════════════════════════════════════════════════════════════════
//                          UTILITY FUNCTION TESTS
// ═══════════════════════════════════════════════════════════════════════════════

describe('cn (classnames)', () => {
  it('joins multiple class strings', () => {
    expect(cn('a', 'b', 'c')).toBe('a b c');
  });

  it('filters out falsy values', () => {
    expect(cn('a', false, undefined, 'b', '')).toBe('a b');
  });

  it('returns empty string for all falsy', () => {
    expect(cn(false, undefined)).toBe('');
  });
});

describe('shortenAddress', () => {
  it('shortens a valid 42-char address', () => {
    expect(shortenAddress('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045'))
      .toBe('0xd8dA...6045');
  });

  it('returns Unknown for undefined', () => {
    expect(shortenAddress(undefined)).toBe('Unknown');
  });

  it('returns Unknown for empty string', () => {
    expect(shortenAddress('')).toBe('Unknown');
  });
});

describe('getRiskColor', () => {
  it('returns red classes for critical', () => {
    expect(getRiskColor('critical')).toContain('red-500');
  });

  it('returns amber classes for warning', () => {
    expect(getRiskColor('warning')).toContain('amber-500');
  });

  it('returns emerald classes for safe', () => {
    expect(getRiskColor('safe')).toContain('emerald-500');
  });

  it('returns gray classes for unknown level', () => {
    expect(getRiskColor('unknown')).toContain('gray-500');
  });
});

describe('getExplorerUrl', () => {
  it('builds etherscan url for ethereum', () => {
    const url = getExplorerUrl('ethereum', '0xabc');
    expect(url).toBe('https://etherscan.io/address/0xabc');
  });

  it('builds arbiscan url for arbitrum', () => {
    const url = getExplorerUrl('arbitrum', '0xabc', 'token');
    expect(url).toBe('https://arbiscan.io/token/0xabc');
  });

  it('defaults to etherscan for unknown chain', () => {
    const url = getExplorerUrl('somefakechain', '0xabc');
    expect(url).toContain('etherscan.io');
  });
});

describe('deriveRiskSummary', () => {
  const makeApproval = (riskLevel: 'critical' | 'warning' | 'safe', isUnlimited = false): Approval => ({
    chain: 'ethereum',
    tokenAddress: '0x' + '1'.repeat(40),
    spenderAddress: '0x' + '2'.repeat(40),
    allowanceRaw: '1000',
    allowanceHuman: '1000 USDT',
    isUnlimited,
    riskLevel,
    riskReasons: [],
    lastUpdated: Date.now(),
  });

  it('counts critical risks correctly', () => {
    const approvals = [makeApproval('critical'), makeApproval('critical'), makeApproval('safe')];
    const summary = deriveRiskSummary(approvals);
    expect(summary.criticalRisks).toBe(2);
    expect(summary.warnings).toBe(0);
    expect(summary.totalApprovals).toBe(3);
  });

  it('counts warnings correctly', () => {
    const approvals = [makeApproval('warning'), makeApproval('warning')];
    const summary = deriveRiskSummary(approvals);
    expect(summary.warnings).toBe(2);
  });

  it('calculates risk score (capped at 100)', () => {
    const approvals = [
      makeApproval('critical'), makeApproval('critical'),
      makeApproval('critical'), makeApproval('critical'),
    ];
    const summary = deriveRiskSummary(approvals);
    expect(summary.overallRiskScore).toBe(100); // 4 * 30 = 120, capped at 100
  });

  it('generates recommendation for critical approvals', () => {
    const approvals = [makeApproval('critical')];
    const summary = deriveRiskSummary(approvals);
    expect(summary.recommendations.length).toBeGreaterThan(0);
    expect(summary.recommendations[0]).toContain('Revoke');
  });

  it('handles empty approvals', () => {
    const summary = deriveRiskSummary([]);
    expect(summary.totalApprovals).toBe(0);
    expect(summary.criticalRisks).toBe(0);
    expect(summary.overallRiskScore).toBe(0);
    expect(summary.recommendations).toEqual([]);
  });
});

describe('SUPPORTED_CHAINS', () => {
  it('has 16 chains', () => {
    expect(SUPPORTED_CHAINS).toHaveLength(16);
  });

  it('includes ethereum', () => {
    expect(SUPPORTED_CHAINS.find(c => c.id === 'ethereum')).toBeDefined();
  });

  it('each chain has required fields', () => {
    SUPPORTED_CHAINS.forEach(chain => {
      expect(chain).toHaveProperty('id');
      expect(chain).toHaveProperty('name');
      expect(chain).toHaveProperty('icon');
      expect(chain).toHaveProperty('color');
    });
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
//                          COMPONENT RENDER TESTS
// ═══════════════════════════════════════════════════════════════════════════════

import { RiskGauge } from '../components/RiskGauge';

describe('RiskGauge', () => {
  it('renders score value', () => {
    render(<RiskGauge score={42} />);
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('renders 0 score', () => {
    render(<RiskGauge score={0} />);
    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('renders max score', () => {
    render(<RiskGauge score={100} />);
    expect(screen.getByText('100')).toBeInTheDocument();
  });
});

import { ErrorBoundary } from '../components/ErrorBoundary';

describe('ErrorBoundary', () => {
  const ThrowError = () => {
    throw new Error('Test error');
  };

  // Suppress console.error for error boundary tests
  const originalError = console.error;
  beforeEach(() => { console.error = vi.fn(); });

  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <div>Safe content</div>
      </ErrorBoundary>
    );
    expect(screen.getByText('Safe content')).toBeInTheDocument();
  });

  it('renders error UI when child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('Test error')).toBeInTheDocument();
    expect(screen.getByText('Reload App')).toBeInTheDocument();
    console.error = originalError;
  });
});

import { ChainSelector } from '../components/ChainSelector';

describe('ChainSelector', () => {
  it('shows selected count', () => {
    const onChange = vi.fn();
    render(<ChainSelector selectedChains={['ethereum', 'arbitrum']} onChange={onChange} />);
    expect(screen.getByText(/2 \/ 16 chains selected/)).toBeInTheDocument();
  });

  it('opens dropdown on click', async () => {
    const onChange = vi.fn();
    render(<ChainSelector selectedChains={[]} onChange={onChange} />);
    
    const button = screen.getByText(/0 \/ 16 chains selected/);
    fireEvent.click(button);
    
    expect(screen.getByText('Select All')).toBeInTheDocument();
    expect(screen.getByText('Clear')).toBeInTheDocument();
  });

  it('calls onChange when chain is toggled', async () => {
    const onChange = vi.fn();
    render(<ChainSelector selectedChains={['ethereum']} onChange={onChange} />);
    
    // Open dropdown
    fireEvent.click(screen.getByText(/1 \/ 16 chains selected/));
    
    // Click Arbitrum
    fireEvent.click(screen.getByText('Arbitrum'));
    expect(onChange).toHaveBeenCalledWith(['ethereum', 'arbitrum']);
  });

  it('deselects chain when already selected', async () => {
    const onChange = vi.fn();
    render(<ChainSelector selectedChains={['ethereum', 'arbitrum']} onChange={onChange} />);
    
    fireEvent.click(screen.getByText(/2 \/ 16 chains selected/));
    fireEvent.click(screen.getByText('Ethereum'));
    expect(onChange).toHaveBeenCalledWith(['arbitrum']);
  });

  it('select all adds all chains', () => {
    const onChange = vi.fn();
    render(<ChainSelector selectedChains={[]} onChange={onChange} />);
    
    fireEvent.click(screen.getByText(/0 \/ 16 chains selected/));
    fireEvent.click(screen.getByText('Select All'));
    
    expect(onChange).toHaveBeenCalledWith(SUPPORTED_CHAINS.map(c => c.id));
  });

  it('clear removes all chains', () => {
    const onChange = vi.fn();
    render(<ChainSelector selectedChains={['ethereum']} onChange={onChange} />);
    
    fireEvent.click(screen.getByText(/1 \/ 16 chains selected/));
    fireEvent.click(screen.getByText('Clear'));
    
    expect(onChange).toHaveBeenCalledWith([]);
  });
});

import { ApprovalCard } from '../components/ApprovalCard';

describe('ApprovalCard', () => {
  const mockApproval: Approval = {
    chain: 'ethereum',
    tokenAddress: '0xdAC17F958D2ee523a2206206994597C13D831ec7',
    tokenSymbol: 'USDT',
    spenderAddress: '0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45',
    spenderName: 'Uniswap V3 Router',
    allowanceRaw: '115792089237316195423570985008687907853269984665640564039457584007913129639935',
    allowanceHuman: '∞',
    isUnlimited: true,
    riskLevel: 'critical',
    riskReasons: ['Unlimited approval', 'Contract not verified'],
    lastUpdated: Date.now(),
  };

  it('renders token symbol', () => {
    render(<ApprovalCard approval={mockApproval} onRevoke={vi.fn()} isRevoking={false} />);
    expect(screen.getByText('USDT')).toBeInTheDocument();
  });

  it('renders spender name', () => {
    render(<ApprovalCard approval={mockApproval} onRevoke={vi.fn()} isRevoking={false} />);
    expect(screen.getByText('Uniswap V3 Router')).toBeInTheDocument();
  });

  it('shows UNLIMITED for unlimited approval', () => {
    render(<ApprovalCard approval={mockApproval} onRevoke={vi.fn()} isRevoking={false} />);
    expect(screen.getByText('∞ UNLIMITED')).toBeInTheDocument();
  });

  it('shows risk badge', () => {
    render(<ApprovalCard approval={mockApproval} onRevoke={vi.fn()} isRevoking={false} />);
    expect(screen.getByText('critical')).toBeInTheDocument();
  });

  it('shows risk reasons', () => {
    render(<ApprovalCard approval={mockApproval} onRevoke={vi.fn()} isRevoking={false} />);
    expect(screen.getByText('Unlimited approval')).toBeInTheDocument();
    expect(screen.getByText('Contract not verified')).toBeInTheDocument();
  });

  it('calls onRevoke when revoke button clicked', () => {
    const onRevoke = vi.fn();
    render(<ApprovalCard approval={mockApproval} onRevoke={onRevoke} isRevoking={false} />);
    
    fireEvent.click(screen.getByText('Revoke'));
    expect(onRevoke).toHaveBeenCalledOnce();
  });

  it('disables revoke button when revoking', () => {
    render(<ApprovalCard approval={mockApproval} onRevoke={vi.fn()} isRevoking={true} />);
    
    const revokeBtn = screen.getByText('Revoke').closest('button');
    expect(revokeBtn).toBeDisabled();
  });

  it('defaults to UNKNOWN for missing symbol', () => {
    const noSymbol = { ...mockApproval, tokenSymbol: undefined };
    render(<ApprovalCard approval={noSymbol} onRevoke={vi.fn()} isRevoking={false} />);
    expect(screen.getByText('UNKNOWN')).toBeInTheDocument();
  });

  it('renders chain badge', () => {
    render(<ApprovalCard approval={mockApproval} onRevoke={vi.fn()} isRevoking={false} />);
    expect(screen.getByText('ethereum')).toBeInTheDocument();
  });
});

import { ContractAnalysisCard } from '../components/ContractAnalysisCard';

describe('ContractAnalysisCard', () => {
  const mockAnalysis: ContractAnalysis = {
    address: '0xdAC17F958D2ee523a2206206994597C13D831ec7',
    chain: 'ethereum',
    decompilerResult: {
      functions: ['transfer', 'approve', 'balanceOf'],
      storageSlots: 5,
      complexity: 'medium',
      patterns: ['ERC20', 'Ownable'],
      cfg: '',
    },
    analyzerResult: {
      vulnerabilities: [
        { type: 'Reentrancy', severity: 'high', description: 'Potential reentrancy in withdraw', location: 'L42' },
      ],
      riskScore: 65,
      patterns: ['ERC20'],
      suggestions: ['Add reentrancy guard'],
    },
    overallRisk: 'high',
    timestamp: Date.now(),
  };

  it('renders shortened address', () => {
    render(<ContractAnalysisCard analysis={mockAnalysis} />);
    expect(screen.getByText('0xdAC1...1ec7')).toBeInTheDocument();
  });

  it('renders chain name', () => {
    render(<ContractAnalysisCard analysis={mockAnalysis} />);
    expect(screen.getByText('ethereum')).toBeInTheDocument();
  });

  it('renders overall risk badge', () => {
    render(<ContractAnalysisCard analysis={mockAnalysis} />);
    expect(screen.getByText('high Risk')).toBeInTheDocument();
  });

  it('renders function count', () => {
    render(<ContractAnalysisCard analysis={mockAnalysis} />);
    expect(screen.getByText('3')).toBeInTheDocument(); // 3 functions
  });

  it('renders vulnerability count', () => {
    render(<ContractAnalysisCard analysis={mockAnalysis} />);
    expect(screen.getByText('1')).toBeInTheDocument(); // 1 vuln
  });

  it('renders risk score', () => {
    render(<ContractAnalysisCard analysis={mockAnalysis} />);
    expect(screen.getByText('65/100')).toBeInTheDocument();
  });

  it('expands to show details on click', () => {
    render(<ContractAnalysisCard analysis={mockAnalysis} />);
    
    fireEvent.click(screen.getByText('Show Details'));
    
    expect(screen.getByText('Decompiler Analysis')).toBeInTheDocument();
    expect(screen.getByText('Vulnerabilities Detected')).toBeInTheDocument();
    expect(screen.getByText('Security Suggestions')).toBeInTheDocument();
  });

  it('shows vulnerability details when expanded', () => {
    render(<ContractAnalysisCard analysis={mockAnalysis} />);
    fireEvent.click(screen.getByText('Show Details'));
    
    expect(screen.getByText('Reentrancy')).toBeInTheDocument();
    expect(screen.getByText('Potential reentrancy in withdraw')).toBeInTheDocument();
  });

  it('toggles between show/hide', () => {
    render(<ContractAnalysisCard analysis={mockAnalysis} />);
    
    fireEvent.click(screen.getByText('Show Details'));
    expect(screen.getByText('Hide Details')).toBeInTheDocument();
    
    fireEvent.click(screen.getByText('Hide Details'));
    expect(screen.getByText('Show Details')).toBeInTheDocument();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
//                          HERO SECTION TESTS
// ═══════════════════════════════════════════════════════════════════════════════

import { FeatureCard } from '../components/HeroSection';

describe('FeatureCard', () => {
  const MockIcon = () => <span data-testid="mock-icon" />;

  it('renders title and description', () => {
    render(<FeatureCard icon={MockIcon} title="Test Title" description="Test Desc" delay={0} />);
    expect(screen.getByText('Test Title')).toBeInTheDocument();
    expect(screen.getByText('Test Desc')).toBeInTheDocument();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
//                          EDGE CASE TESTS
// ═══════════════════════════════════════════════════════════════════════════════

describe('Edge Cases', () => {
  it('ApprovalCard handles approval with no risk reasons', () => {
    const approval: Approval = {
      chain: 'bsc',
      tokenAddress: '0x' + 'a'.repeat(40),
      spenderAddress: '0x' + 'b'.repeat(40),
      allowanceRaw: '100',
      allowanceHuman: '100',
      isUnlimited: false,
      riskLevel: 'safe',
      riskReasons: [],
      lastUpdated: Date.now(),
    };
    render(<ApprovalCard approval={approval} onRevoke={vi.fn()} isRevoking={false} />);
    expect(screen.getByText('safe')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('ContractAnalysisCard handles zero vulnerabilities', () => {
    const analysis: ContractAnalysis = {
      address: '0x' + 'c'.repeat(40),
      chain: 'polygon',
      decompilerResult: {
        functions: ['transfer'],
        storageSlots: 1,
        complexity: 'low',
        patterns: [],
        cfg: '',
      },
      analyzerResult: {
        vulnerabilities: [],
        riskScore: 10,
        patterns: [],
        suggestions: [],
      },
      overallRisk: 'low',
      timestamp: Date.now(),
    };
    render(<ContractAnalysisCard analysis={analysis} />);
    expect(screen.getByText('low Risk')).toBeInTheDocument();
    
    // Expand - should NOT show vulnerabilities section
    fireEvent.click(screen.getByText('Show Details'));
    expect(screen.queryByText('Vulnerabilities Detected')).not.toBeInTheDocument();
  });

  it('deriveRiskSummary generates unlimited recommendation', () => {
    const approvals: Approval[] = Array(6).fill(null).map(() => ({
      chain: 'ethereum',
      tokenAddress: '0x' + Math.random().toString(16).slice(2).padEnd(40, '0'),
      spenderAddress: '0x' + Math.random().toString(16).slice(2).padEnd(40, '0'),
      allowanceRaw: '999',
      allowanceHuman: '∞',
      isUnlimited: true,
      riskLevel: 'warning' as const,
      riskReasons: [],
      lastUpdated: Date.now(),
    }));
    const summary = deriveRiskSummary(approvals);
    expect(summary.recommendations).toContainEqual(
      expect.stringContaining('specific approval amounts')
    );
  });
});
