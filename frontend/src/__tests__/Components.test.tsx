/**
 * ╔═══════════════════════════════════════════════════════════════════════════╗
 * ║              SENTINEL SHIELD - COMPONENT UNIT TESTS                       ║
 * ╠═══════════════════════════════════════════════════════════════════════════╣
 * ║  Comprehensive unit tests for all React components                        ║
 * ╚═══════════════════════════════════════════════════════════════════════════╝
 */

// @ts-nocheck
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React, { useState } from 'react';

// ═══════════════════════════════════════════════════════════════════════════
//                          UTILITY COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════

// AddressInput Component
const AddressInput: React.FC<{
  value: string;
  onChange: (value: string) => void;
  onValidate?: (isValid: boolean) => void;
}> = ({ value, onChange, onValidate }) => {
  const [error, setError] = useState<string | null>(null);

  const validate = (addr: string) => {
    if (!addr) {
      setError(null);
      onValidate?.(false);
      return;
    }
    if (!addr.startsWith('0x')) {
      setError('Address must start with 0x');
      onValidate?.(false);
      return;
    }
    if (addr.length !== 42) {
      setError('Address must be 42 characters');
      onValidate?.(false);
      return;
    }
    if (!/^0x[0-9a-fA-F]{40}$/.test(addr)) {
      setError('Address contains invalid characters');
      onValidate?.(false);
      return;
    }
    setError(null);
    onValidate?.(true);
  };

  return (
    <div data-testid="address-input-wrapper">
      <input
        type="text"
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          validate(e.target.value);
        }}
        placeholder="0x..."
        data-testid="address-field"
      />
      {error && <span data-testid="address-error" className="error">{error}</span>}
    </div>
  );
};

// ChainSelector Component
const ChainSelector: React.FC<{
  chains: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
}> = ({ chains, selected, onChange }) => {
  const toggle = (chain: string) => {
    if (selected.includes(chain)) {
      onChange(selected.filter(c => c !== chain));
    } else {
      onChange([...selected, chain]);
    }
  };

  return (
    <div data-testid="chain-selector" role="group" aria-label="Select chains">
      {chains.map(chain => (
        <button
          key={chain}
          onClick={() => toggle(chain)}
          className={selected.includes(chain) ? 'selected' : ''}
          data-testid={`chain-btn-${chain}`}
          aria-pressed={selected.includes(chain)}
        >
          {chain}
        </button>
      ))}
    </div>
  );
};

// RiskBadge Component
const RiskBadge: React.FC<{
  level: 'safe' | 'low' | 'medium' | 'high' | 'critical';
}> = ({ level }) => {
  const colors = {
    safe: '#00ff00',
    low: '#88ff00',
    medium: '#ffff00',
    high: '#ff8800',
    critical: '#ff0000',
  };

  return (
    <span
      data-testid="risk-badge"
      className={`risk-badge risk-${level}`}
      style={{ backgroundColor: colors[level] }}
    >
      {level.toUpperCase()}
    </span>
  );
};

// AmountDisplay Component
const AmountDisplay: React.FC<{
  amount: string;
  decimals?: number;
  symbol?: string;
}> = ({ amount, decimals = 18, symbol }) => {
  const formatAmount = (raw: string): string => {
    if (raw === 'unlimited' || raw === 'MAX') return '∞ Unlimited';
    try {
      const num = BigInt(raw);
      const divisor = BigInt(10 ** decimals);
      const whole = num / divisor;
      const fraction = num % divisor;
      if (whole > BigInt(1e15)) return '∞ Unlimited';
      return `${whole.toString()}${fraction > 0 ? '.' + fraction.toString().slice(0, 4) : ''}`;
    } catch {
      return raw;
    }
  };

  return (
    <span data-testid="amount-display">
      {formatAmount(amount)} {symbol && <span className="symbol">{symbol}</span>}
    </span>
  );
};

// LoadingSpinner Component
const LoadingSpinner: React.FC<{
  size?: 'small' | 'medium' | 'large';
  label?: string;
}> = ({ size = 'medium', label = 'Loading...' }) => {
  const sizes = { small: 16, medium: 32, large: 64 };
  
  return (
    <div data-testid="loading-spinner" aria-label={label}>
      <div
        className="spinner"
        style={{ width: sizes[size], height: sizes[size] }}
      />
      {label && <span className="label">{label}</span>}
    </div>
  );
};

// EmptyState Component
const EmptyState: React.FC<{
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}> = ({ title, description, action }) => {
  return (
    <div data-testid="empty-state" className="empty-state">
      <h3>{title}</h3>
      {description && <p>{description}</p>}
      {action && (
        <button onClick={action.onClick} data-testid="empty-state-action">
          {action.label}
        </button>
      )}
    </div>
  );
};

// ConfirmDialog Component
const ConfirmDialog: React.FC<{
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  confirmLabel?: string;
  cancelLabel?: string;
}> = ({ open, title, message, onConfirm, onCancel, confirmLabel = 'Confirm', cancelLabel = 'Cancel' }) => {
  if (!open) return null;

  return (
    <div data-testid="confirm-dialog" role="dialog" aria-modal="true">
      <h2>{title}</h2>
      <p>{message}</p>
      <div className="actions">
        <button onClick={onCancel} data-testid="dialog-cancel">
          {cancelLabel}
        </button>
        <button onClick={onConfirm} data-testid="dialog-confirm">
          {confirmLabel}
        </button>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
//                          UNIT TESTS
// ═══════════════════════════════════════════════════════════════════════════

describe('AddressInput', () => {
  it('renders with placeholder', () => {
    render(<AddressInput value="" onChange={() => {}} />);
    expect(screen.getByPlaceholderText('0x...')).toBeInTheDocument();
  });

  it('calls onChange when typing', async () => {
    const handleChange = vi.fn();
    render(<AddressInput value="" onChange={handleChange} />);
    
    await userEvent.type(screen.getByTestId('address-field'), 'a');
    expect(handleChange).toHaveBeenCalledWith('a');
  });

  it('shows error for invalid prefix', async () => {
    const Wrapper = () => {
      const [value, setValue] = useState('');
      return <AddressInput value={value} onChange={setValue} />;
    };

    render(<Wrapper />);
    await userEvent.type(screen.getByTestId('address-field'), '1234');
    
    expect(screen.getByTestId('address-error')).toHaveTextContent('must start with 0x');
  });

  it('shows error for wrong length', async () => {
    const Wrapper = () => {
      const [value, setValue] = useState('');
      return <AddressInput value={value} onChange={setValue} />;
    };

    render(<Wrapper />);
    await userEvent.type(screen.getByTestId('address-field'), '0x1234');
    
    expect(screen.getByTestId('address-error')).toHaveTextContent('42 characters');
  });

  it('validates correct address', async () => {
    const handleValidate = vi.fn();
    const Wrapper = () => {
      const [value, setValue] = useState('');
      return <AddressInput value={value} onChange={setValue} onValidate={handleValidate} />;
    };

    render(<Wrapper />);
    await userEvent.type(
      screen.getByTestId('address-field'),
      '0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1'
    );
    
    expect(handleValidate).toHaveBeenLastCalledWith(true);
    expect(screen.queryByTestId('address-error')).not.toBeInTheDocument();
  });

  it('detects invalid hex characters', async () => {
    const Wrapper = () => {
      const [value, setValue] = useState('');
      return <AddressInput value={value} onChange={setValue} />;
    };

    render(<Wrapper />);
    // Type address with invalid 'g' character
    await userEvent.type(
      screen.getByTestId('address-field'),
      '0xgggggggggggggggggggggggggggggggggggggggg'
    );
    
    expect(screen.getByTestId('address-error')).toHaveTextContent('invalid characters');
  });
});

describe('ChainSelector', () => {
  const chains = ['ethereum', 'bsc', 'polygon'];

  it('renders all chains', () => {
    render(<ChainSelector chains={chains} selected={[]} onChange={() => {}} />);
    
    chains.forEach(chain => {
      expect(screen.getByTestId(`chain-btn-${chain}`)).toBeInTheDocument();
    });
  });

  it('shows selected state', () => {
    render(<ChainSelector chains={chains} selected={['ethereum']} onChange={() => {}} />);
    
    expect(screen.getByTestId('chain-btn-ethereum')).toHaveClass('selected');
    expect(screen.getByTestId('chain-btn-bsc')).not.toHaveClass('selected');
  });

  it('calls onChange on selection', async () => {
    const handleChange = vi.fn();
    render(<ChainSelector chains={chains} selected={[]} onChange={handleChange} />);
    
    await userEvent.click(screen.getByTestId('chain-btn-ethereum'));
    
    expect(handleChange).toHaveBeenCalledWith(['ethereum']);
  });

  it('removes chain on deselect', async () => {
    const handleChange = vi.fn();
    render(<ChainSelector chains={chains} selected={['ethereum', 'bsc']} onChange={handleChange} />);
    
    await userEvent.click(screen.getByTestId('chain-btn-ethereum'));
    
    expect(handleChange).toHaveBeenCalledWith(['bsc']);
  });

  it('has proper aria attributes', () => {
    render(<ChainSelector chains={chains} selected={['ethereum']} onChange={() => {}} />);
    
    expect(screen.getByTestId('chain-btn-ethereum')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('chain-btn-bsc')).toHaveAttribute('aria-pressed', 'false');
  });
});

describe('RiskBadge', () => {
  const levels = ['safe', 'low', 'medium', 'high', 'critical'] as const;

  it('renders correct text for each level', () => {
    levels.forEach(level => {
      const { unmount } = render(<RiskBadge level={level} />);
      expect(screen.getByTestId('risk-badge')).toHaveTextContent(level.toUpperCase());
      unmount();
    });
  });

  it('has correct class for each level', () => {
    levels.forEach(level => {
      const { unmount } = render(<RiskBadge level={level} />);
      expect(screen.getByTestId('risk-badge')).toHaveClass(`risk-${level}`);
      unmount();
    });
  });

  it('has correct color for safe level', () => {
    render(<RiskBadge level="safe" />);
    expect(screen.getByTestId('risk-badge')).toHaveStyle({ backgroundColor: '#00ff00' });
  });

  it('has correct color for critical level', () => {
    render(<RiskBadge level="critical" />);
    expect(screen.getByTestId('risk-badge')).toHaveStyle({ backgroundColor: '#ff0000' });
  });
});

describe('AmountDisplay', () => {
  it('displays unlimited for MAX value', () => {
    render(<AmountDisplay amount="MAX" />);
    expect(screen.getByTestId('amount-display')).toHaveTextContent('∞ Unlimited');
  });

  it('displays unlimited for "unlimited" string', () => {
    render(<AmountDisplay amount="unlimited" />);
    expect(screen.getByTestId('amount-display')).toHaveTextContent('∞ Unlimited');
  });

  it('formats token amounts correctly', () => {
    render(<AmountDisplay amount="1000000000000000000" decimals={18} />);
    expect(screen.getByTestId('amount-display')).toHaveTextContent('1');
  });

  it('shows symbol when provided', () => {
    render(<AmountDisplay amount="1000000000000000000" decimals={18} symbol="ETH" />);
    expect(screen.getByTestId('amount-display')).toHaveTextContent('ETH');
  });

  it('handles very large amounts as unlimited', () => {
    const maxUint = '115792089237316195423570985008687907853269984665640564039457584007913129639935';
    render(<AmountDisplay amount={maxUint} />);
    expect(screen.getByTestId('amount-display')).toHaveTextContent('∞ Unlimited');
  });

  it('handles USDC/USDT 6 decimals', () => {
    render(<AmountDisplay amount="1000000" decimals={6} symbol="USDC" />);
    expect(screen.getByTestId('amount-display')).toHaveTextContent('1');
  });
});

describe('LoadingSpinner', () => {
  it('renders with default props', () => {
    render(<LoadingSpinner />);
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('shows custom label', () => {
    render(<LoadingSpinner label="Scanning..." />);
    expect(screen.getByText('Scanning...')).toBeInTheDocument();
  });

  it('has correct aria-label', () => {
    render(<LoadingSpinner label="Processing" />);
    expect(screen.getByTestId('loading-spinner')).toHaveAttribute('aria-label', 'Processing');
  });

  it('renders different sizes', () => {
    const { rerender } = render(<LoadingSpinner size="small" />);
    expect(screen.getByTestId('loading-spinner').querySelector('.spinner')).toHaveStyle({ width: '16px' });
    
    rerender(<LoadingSpinner size="large" />);
    expect(screen.getByTestId('loading-spinner').querySelector('.spinner')).toHaveStyle({ width: '64px' });
  });
});

describe('EmptyState', () => {
  it('renders title', () => {
    render(<EmptyState title="No approvals found" />);
    expect(screen.getByText('No approvals found')).toBeInTheDocument();
  });

  it('renders description when provided', () => {
    render(<EmptyState title="Empty" description="Start by scanning a wallet" />);
    expect(screen.getByText('Start by scanning a wallet')).toBeInTheDocument();
  });

  it('renders action button when provided', () => {
    const handleClick = vi.fn();
    render(
      <EmptyState
        title="Empty"
        action={{ label: 'Scan Now', onClick: handleClick }}
      />
    );
    
    expect(screen.getByTestId('empty-state-action')).toHaveTextContent('Scan Now');
  });

  it('calls action onClick when clicked', async () => {
    const handleClick = vi.fn();
    render(
      <EmptyState
        title="Empty"
        action={{ label: 'Scan Now', onClick: handleClick }}
      />
    );
    
    await userEvent.click(screen.getByTestId('empty-state-action'));
    expect(handleClick).toHaveBeenCalled();
  });
});

describe('ConfirmDialog', () => {
  const defaultProps = {
    open: true,
    title: 'Confirm Action',
    message: 'Are you sure?',
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
  };

  it('renders when open', () => {
    render(<ConfirmDialog {...defaultProps} />);
    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(<ConfirmDialog {...defaultProps} open={false} />);
    expect(screen.queryByTestId('confirm-dialog')).not.toBeInTheDocument();
  });

  it('displays title and message', () => {
    render(<ConfirmDialog {...defaultProps} />);
    expect(screen.getByText('Confirm Action')).toBeInTheDocument();
    expect(screen.getByText('Are you sure?')).toBeInTheDocument();
  });

  it('calls onConfirm when confirmed', async () => {
    const onConfirm = vi.fn();
    render(<ConfirmDialog {...defaultProps} onConfirm={onConfirm} />);
    
    await userEvent.click(screen.getByTestId('dialog-confirm'));
    expect(onConfirm).toHaveBeenCalled();
  });

  it('calls onCancel when cancelled', async () => {
    const onCancel = vi.fn();
    render(<ConfirmDialog {...defaultProps} onCancel={onCancel} />);
    
    await userEvent.click(screen.getByTestId('dialog-cancel'));
    expect(onCancel).toHaveBeenCalled();
  });

  it('uses custom button labels', () => {
    render(
      <ConfirmDialog
        {...defaultProps}
        confirmLabel="Revoke"
        cancelLabel="Keep"
      />
    );
    
    expect(screen.getByTestId('dialog-confirm')).toHaveTextContent('Revoke');
    expect(screen.getByTestId('dialog-cancel')).toHaveTextContent('Keep');
  });

  it('has correct aria attributes', () => {
    render(<ConfirmDialog {...defaultProps} />);
    const dialog = screen.getByTestId('confirm-dialog');
    
    expect(dialog).toHaveAttribute('role', 'dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
  });
});

// ═══════════════════════════════════════════════════════════════════════════
//                          EDGE CASE TESTS
// ═══════════════════════════════════════════════════════════════════════════

describe('Edge Cases', () => {
  describe('AddressInput edge cases', () => {
    it('handles paste event', async () => {
      const handleChange = vi.fn();
      const Wrapper = () => {
        const [value, setValue] = useState('');
        return <AddressInput value={value} onChange={(v) => { setValue(v); handleChange(v); }} />;
      };

      render(<Wrapper />);
      const input = screen.getByTestId('address-field');
      
      // Simulate paste
      await userEvent.click(input);
      fireEvent.paste(input, {
        clipboardData: {
          getData: () => '0x742d35Cc6634C0532925a3b844Bc9e7595f5b2e1',
        },
      });
    });

    it('handles empty string after clearing', async () => {
      const Wrapper = () => {
        const [value, setValue] = useState('0x123');
        return <AddressInput value={value} onChange={setValue} />;
      };

      render(<Wrapper />);
      const input = screen.getByTestId('address-field');
      
      await userEvent.clear(input);
      expect(screen.queryByTestId('address-error')).not.toBeInTheDocument();
    });
  });

  describe('AmountDisplay edge cases', () => {
    it('handles zero amount', () => {
      render(<AmountDisplay amount="0" />);
      expect(screen.getByTestId('amount-display')).toHaveTextContent('0');
    });

    it('handles invalid amount gracefully', () => {
      render(<AmountDisplay amount="not-a-number" />);
      expect(screen.getByTestId('amount-display')).toHaveTextContent('not-a-number');
    });

    it('handles negative like string gracefully', () => {
      render(<AmountDisplay amount="-1000" />);
      // Should not crash
      expect(screen.getByTestId('amount-display')).toBeInTheDocument();
    });
  });
});
