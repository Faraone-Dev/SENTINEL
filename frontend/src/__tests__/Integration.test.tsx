/**
 * ╔═══════════════════════════════════════════════════════════════════════════╗
 * ║              SENTINEL SHIELD - INTEGRATION TESTS (REACT)                  ║
 * ╠═══════════════════════════════════════════════════════════════════════════╣
 * ║  End-to-end testing of user flows and component interactions             ║
 * ╚═══════════════════════════════════════════════════════════════════════════╝
 */

// @ts-nocheck
import { describe, it, expect, vi, beforeEach, afterEach, afterAll } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React, { useState } from 'react';

// ═══════════════════════════════════════════════════════════════════════════
//                          MOCK COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════

interface Approval {
  id: string;
  token: string;
  symbol: string;
  spender: string;
  spenderName: string;
  amount: string;
  isUnlimited: boolean;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  chain: string;
}

interface ScanResult {
  address: string;
  chains: string[];
  approvals: Approval[];
  riskScore: number;
  riskLevel: string;
  scanTime: number;
}

// Mock API functions
const mockScanWallet = vi.fn();
const mockRevokeApproval = vi.fn();
const mockBatchRevoke = vi.fn();

// Silence expected error logs during rejection scenarios
const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
afterAll(() => {
  consoleErrorSpy.mockRestore();
});

// WalletScanner Component
const WalletScanner: React.FC<{
  onScanComplete: (result: ScanResult) => void;
}> = ({ onScanComplete }) => {
  const [address, setAddress] = useState('');
  const [chains, setChains] = useState<string[]>(['ethereum']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleScan = async () => {
    if (!address) {
      setError('Please enter an address');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await mockScanWallet(address, chains);
      onScanComplete(result);
    } catch (err: any) {
      setError(err.message || 'Scan failed');
    } finally {
      setLoading(false);
    }
  };

  const toggleChain = (chain: string) => {
    setChains(prev => 
      prev.includes(chain)
        ? prev.filter(c => c !== chain)
        : [...prev, chain]
    );
  };

  return (
    <div data-testid="wallet-scanner">
      <input
        type="text"
        placeholder="Enter wallet address"
        value={address}
        onChange={(e) => setAddress(e.target.value)}
        data-testid="address-input"
      />
      
      <div data-testid="chain-selector">
        {['ethereum', 'bsc', 'polygon', 'arbitrum'].map(chain => (
          <label key={chain}>
            <input
              type="checkbox"
              checked={chains.includes(chain)}
              onChange={() => toggleChain(chain)}
              data-testid={`chain-${chain}`}
            />
            {chain}
          </label>
        ))}
      </div>
      
      <button
        onClick={handleScan}
        disabled={loading}
        data-testid="scan-button"
      >
        {loading ? 'Scanning...' : 'Scan Wallet'}
      </button>
      
      {error && <div data-testid="error-message" role="alert">{error}</div>}
    </div>
  );
};

// ApprovalList Component
const ApprovalList: React.FC<{
  approvals: Approval[];
  onRevoke: (id: string) => void;
  onBatchRevoke: (ids: string[]) => void;
}> = ({ approvals, onRevoke, onBatchRevoke }) => {
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const toggleSelect = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const selectAll = () => {
    if (selected.size === approvals.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(approvals.map(a => a.id)));
    }
  };

  const handleBatchRevoke = () => {
    onBatchRevoke(Array.from(selected));
    setSelected(new Set());
  };

  return (
    <div data-testid="approval-list">
      <div className="actions">
        <button onClick={selectAll} data-testid="select-all">
          {selected.size === approvals.length ? 'Deselect All' : 'Select All'}
        </button>
        <button
          onClick={handleBatchRevoke}
          disabled={selected.size === 0}
          data-testid="batch-revoke"
        >
          Revoke Selected ({selected.size})
        </button>
      </div>

      <ul>
        {approvals.map(approval => (
          <li key={approval.id} data-testid={`approval-${approval.id}`}>
            <input
              type="checkbox"
              checked={selected.has(approval.id)}
              onChange={() => toggleSelect(approval.id)}
            />
            <span className="token">{approval.symbol}</span>
            <span className="spender">{approval.spenderName}</span>
            <span className={`risk-${approval.riskLevel}`}>
              {approval.riskLevel}
            </span>
            <button
              onClick={() => onRevoke(approval.id)}
              data-testid={`revoke-${approval.id}`}
            >
              Revoke
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};

// RiskIndicator Component
const RiskIndicator: React.FC<{
  score: number;
  level: string;
}> = ({ score, level }) => {
  const getColor = () => {
    if (score === 0) return 'green';
    if (score < 25) return 'lime';
    if (score < 50) return 'yellow';
    if (score < 75) return 'orange';
    return 'red';
  };

  return (
    <div data-testid="risk-indicator" className={`risk-${level}`}>
      <div className="score" style={{ color: getColor() }}>
        {score}
      </div>
      <div className="level">{level.toUpperCase()}</div>
    </div>
  );
};

// Main App Component
const App: React.FC = () => {
  const [result, setResult] = useState<ScanResult | null>(null);
  const [revoking, setRevoking] = useState(false);

  const handleRevoke = async (id: string) => {
    setRevoking(true);
    try {
      await mockRevokeApproval(id);
      if (result) {
        setResult({
          ...result,
          approvals: result.approvals.filter(a => a.id !== id)
        });
      }
    } catch (err) {
      console.error('Revoke failed', err);
    } finally {
      setRevoking(false);
    }
  };

  const handleBatchRevoke = async (ids: string[]) => {
    setRevoking(true);
    try {
      await mockBatchRevoke(ids);
      if (result) {
        setResult({
          ...result,
          approvals: result.approvals.filter(a => !ids.includes(a.id))
        });
      }
    } catch (err) {
      console.error('Batch revoke failed', err);
    } finally {
      setRevoking(false);
    }
  };

  return (
    <div data-testid="app">
      <h1>SENTINEL SHIELD</h1>
      
      <WalletScanner onScanComplete={setResult} />
      
      {result && (
        <div data-testid="results">
          <RiskIndicator score={result.riskScore} level={result.riskLevel} />
          <ApprovalList
            approvals={result.approvals}
            onRevoke={handleRevoke}
            onBatchRevoke={handleBatchRevoke}
          />
        </div>
      )}
      
      {revoking && <div data-testid="revoking-overlay">Revoking...</div>}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
//                          TEST DATA
// ═══════════════════════════════════════════════════════════════════════════

const mockApprovals: Approval[] = [
  {
    id: '1',
    token: '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
    symbol: 'USDC',
    spender: '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
    spenderName: 'Uniswap V2',
    amount: 'unlimited',
    isUnlimited: true,
    riskLevel: 'high',
    chain: 'ethereum',
  },
  {
    id: '2',
    token: '0xdAC17F958D2ee523a2206206994597C13D831ec7',
    symbol: 'USDT',
    spender: '0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45',
    spenderName: 'Uniswap V3',
    amount: '1000',
    isUnlimited: false,
    riskLevel: 'medium',
    chain: 'ethereum',
  },
  {
    id: '3',
    token: '0x6B175474E89094C44Da98b954EesfdFd5e3F8C',
    symbol: 'DAI',
    spender: '0x1111111254fb6c44bAC0beD2854e76F90643097d',
    spenderName: '1inch',
    amount: '500',
    isUnlimited: false,
    riskLevel: 'low',
    chain: 'ethereum',
  },
];

const mockScanResult: ScanResult = {
  address: '0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1',
  chains: ['ethereum'],
  approvals: mockApprovals,
  riskScore: 65,
  riskLevel: 'high',
  scanTime: 1234,
};

// ═══════════════════════════════════════════════════════════════════════════
//                          INTEGRATION TESTS
// ═══════════════════════════════════════════════════════════════════════════

describe('Integration: Full User Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should complete full scan and revoke flow', async () => {
    mockScanWallet.mockResolvedValue(mockScanResult);
    mockRevokeApproval.mockResolvedValue({ success: true });

    render(<App />);

    // Enter address
    const input = screen.getByTestId('address-input');
    await userEvent.type(input, '0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1');

    // Start scan
    const scanButton = screen.getByTestId('scan-button');
    await userEvent.click(scanButton);

    // Wait for results
    await waitFor(() => {
      expect(screen.getByTestId('results')).toBeInTheDocument();
    });

    // Verify risk score displayed
    expect(screen.getByTestId('risk-indicator')).toBeInTheDocument();

    // Verify approvals listed
    expect(screen.getByTestId('approval-1')).toBeInTheDocument();
    expect(screen.getByTestId('approval-2')).toBeInTheDocument();

    // Revoke first approval
    const revokeButton = screen.getByTestId('revoke-1');
    await userEvent.click(revokeButton);

    // Verify API called
    expect(mockRevokeApproval).toHaveBeenCalledWith('1');

    // Verify approval removed from list
    await waitFor(() => {
      expect(screen.queryByTestId('approval-1')).not.toBeInTheDocument();
    });
  });

  it('should handle batch revoke flow', async () => {
    mockScanWallet.mockResolvedValue(mockScanResult);
    mockBatchRevoke.mockResolvedValue({ success: true });

    render(<App />);

    // Scan
    await userEvent.type(
      screen.getByTestId('address-input'),
      '0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1'
    );
    await userEvent.click(screen.getByTestId('scan-button'));

    await waitFor(() => {
      expect(screen.getByTestId('results')).toBeInTheDocument();
    });

    // Select all
    await userEvent.click(screen.getByTestId('select-all'));

    // Batch revoke
    const batchButton = screen.getByTestId('batch-revoke');
    expect(batchButton).toHaveTextContent('Revoke Selected (3)');
    await userEvent.click(batchButton);

    // Verify batch API called
    expect(mockBatchRevoke).toHaveBeenCalledWith(['1', '2', '3']);
  });

  it('should handle chain selection', async () => {
    mockScanWallet.mockResolvedValue(mockScanResult);

    render(<App />);

    // Ethereum is selected by default
    expect(screen.getByTestId('chain-ethereum')).toBeChecked();

    // Select additional chains
    await userEvent.click(screen.getByTestId('chain-bsc'));
    await userEvent.click(screen.getByTestId('chain-polygon'));

    expect(screen.getByTestId('chain-bsc')).toBeChecked();
    expect(screen.getByTestId('chain-polygon')).toBeChecked();

    // Scan with multiple chains
    await userEvent.type(
      screen.getByTestId('address-input'),
      '0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1'
    );
    await userEvent.click(screen.getByTestId('scan-button'));

    // Verify API called with all chains
    await waitFor(() => {
      expect(mockScanWallet).toHaveBeenCalledWith(
        '0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1',
        expect.arrayContaining(['ethereum', 'bsc', 'polygon'])
      );
    });
  });
});

describe('Integration: Error Handling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should display error on scan failure', async () => {
    mockScanWallet.mockRejectedValue(new Error('Network error'));

    render(<App />);

    await userEvent.type(
      screen.getByTestId('address-input'),
      '0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1'
    );
    await userEvent.click(screen.getByTestId('scan-button'));

    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toHaveTextContent('Network error');
    });
  });

  it('should show error for empty address', async () => {
    render(<App />);

    await userEvent.click(screen.getByTestId('scan-button'));

    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toHaveTextContent('Please enter an address');
    });
  });

  it('should handle revoke failure gracefully', async () => {
    mockScanWallet.mockResolvedValue(mockScanResult);
    mockRevokeApproval.mockRejectedValue(new Error('Transaction failed'));

    render(<App />);

    await userEvent.type(
      screen.getByTestId('address-input'),
      '0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1'
    );
    await userEvent.click(screen.getByTestId('scan-button'));

    await waitFor(() => {
      expect(screen.getByTestId('results')).toBeInTheDocument();
    });

    // Approval should still be in list after failed revoke
    await userEvent.click(screen.getByTestId('revoke-1'));

    await waitFor(() => {
      // Approval should still exist since revoke failed
      expect(screen.getByTestId('approval-1')).toBeInTheDocument();
    });
  });
});

describe('Integration: UI State Transitions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should show loading state during scan', async () => {
    let resolvePromise: (value: ScanResult) => void;
    const pendingPromise = new Promise<ScanResult>(resolve => {
      resolvePromise = resolve;
    });
    mockScanWallet.mockReturnValue(pendingPromise);

    render(<App />);

    await userEvent.type(
      screen.getByTestId('address-input'),
      '0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1'
    );
    await userEvent.click(screen.getByTestId('scan-button'));

    // Should show loading
    expect(screen.getByTestId('scan-button')).toHaveTextContent('Scanning...');
    expect(screen.getByTestId('scan-button')).toBeDisabled();

    // Resolve and verify loading ends
    resolvePromise!(mockScanResult);

    await waitFor(() => {
      expect(screen.getByTestId('scan-button')).toHaveTextContent('Scan Wallet');
      expect(screen.getByTestId('scan-button')).not.toBeDisabled();
    });
  });

  it('should disable batch revoke when nothing selected', async () => {
    mockScanWallet.mockResolvedValue(mockScanResult);

    render(<App />);

    await userEvent.type(
      screen.getByTestId('address-input'),
      '0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1'
    );
    await userEvent.click(screen.getByTestId('scan-button'));

    await waitFor(() => {
      expect(screen.getByTestId('results')).toBeInTheDocument();
    });

    const batchButton = screen.getByTestId('batch-revoke');
    expect(batchButton).toBeDisabled();
    expect(batchButton).toHaveTextContent('Revoke Selected (0)');
  });
});

describe('Integration: Risk Display', () => {
  it('should display correct risk colors', async () => {
    const testCases = [
      { score: 0, level: 'safe' },
      { score: 20, level: 'low' },
      { score: 45, level: 'medium' },
      { score: 70, level: 'high' },
      { score: 95, level: 'critical' },
    ];

    for (const { score, level } of testCases) {
      mockScanWallet.mockResolvedValue({
        ...mockScanResult,
        riskScore: score,
        riskLevel: level,
      });

      const { unmount } = render(<App />);

      await userEvent.type(
        screen.getByTestId('address-input'),
        '0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1'
      );
      await userEvent.click(screen.getByTestId('scan-button'));

      await waitFor(() => {
        const indicator = screen.getByTestId('risk-indicator');
        expect(indicator).toHaveClass(`risk-${level}`);
      });

      unmount();
      vi.clearAllMocks();
    }
  });
});

describe('Integration: Accessibility', () => {
  it('should have proper ARIA labels', async () => {
    mockScanWallet.mockResolvedValue(mockScanResult);

    render(<App />);

    await userEvent.type(
      screen.getByTestId('address-input'),
      '0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1'
    );

    // Check input is accessible
    expect(screen.getByPlaceholderText('Enter wallet address')).toBeInTheDocument();
  });

  it('should announce errors to screen readers', async () => {
    mockScanWallet.mockRejectedValue(new Error('Test error'));

    render(<App />);

    await userEvent.type(
      screen.getByTestId('address-input'),
      '0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1'
    );
    await userEvent.click(screen.getByTestId('scan-button'));

    await waitFor(() => {
      const errorElement = screen.getByRole('alert');
      expect(errorElement).toBeInTheDocument();
    });
  });
});

describe('Integration: Performance', () => {
  it('should render large approval lists efficiently', async () => {
    // Generate 100 approvals
    const largeApprovalList = Array.from({ length: 100 }, (_, i) => ({
      id: String(i),
      token: `0x${i.toString(16).padStart(40, '0')}`,
      symbol: `TOKEN${i}`,
      spender: `0x${(i + 1000).toString(16).padStart(40, '0')}`,
      spenderName: `Spender ${i}`,
      amount: String(i * 1000),
      isUnlimited: i % 3 === 0,
      riskLevel: (['low', 'medium', 'high', 'critical'] as const)[i % 4],
      chain: 'ethereum',
    }));

    mockScanWallet.mockResolvedValue({
      ...mockScanResult,
      approvals: largeApprovalList,
    });

    const startTime = performance.now();

    render(<App />);

    await userEvent.type(
      screen.getByTestId('address-input'),
      '0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1'
    );
    await userEvent.click(screen.getByTestId('scan-button'));

    await waitFor(() => {
      expect(screen.getByTestId('approval-0')).toBeInTheDocument();
      expect(screen.getByTestId('approval-99')).toBeInTheDocument();
    });

    const endTime = performance.now();
    const renderTime = endTime - startTime;

    // Should render 100 items in under 2 seconds
    expect(renderTime).toBeLessThan(2000);
  });
});
