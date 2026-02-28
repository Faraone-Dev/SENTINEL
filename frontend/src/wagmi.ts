/*
  SENTINEL SHIELD - Wagmi / RainbowKit Configuration
  Wallet connection setup for 16 EVM chains
*/

import { getDefaultConfig } from '@rainbow-me/rainbowkit';
import {
  mainnet,
  arbitrum,
  optimism,
  base,
  zkSync,
  linea,
  scroll,
  polygonZkEvm,
  bsc,
  polygon,
  avalanche,
  fantom,
  cronos,
  gnosis,
  celo,
  moonbeam,
} from 'wagmi/chains';

const projectId = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID || '';

export const config = getDefaultConfig({
  appName: 'SENTINEL SHIELD',
  projectId,
  chains: [
    mainnet,
    arbitrum,
    optimism,
    base,
    zkSync,
    linea,
    scroll,
    polygonZkEvm,
    bsc,
    polygon,
    avalanche,
    fantom,
    cronos,
    gnosis,
    celo,
    moonbeam,
  ],
  ssr: false,
});

// ERC20 ABI for approve(address, uint256)
export const ERC20_ABI = [
  {
    name: 'approve',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [
      { name: 'spender', type: 'address' },
      { name: 'amount', type: 'uint256' },
    ],
    outputs: [{ name: '', type: 'bool' }],
  },
] as const;

// Map chain string IDs to wagmi chain IDs
export const CHAIN_ID_MAP: Record<string, number> = {
  ethereum: 1,
  arbitrum: 42161,
  optimism: 10,
  base: 8453,
  zksync: 324,
  linea: 59144,
  scroll: 534352,
  zkevm: 1101,
  bsc: 56,
  polygon: 137,
  avalanche: 43114,
  fantom: 250,
  cronos: 25,
  gnosis: 100,
  celo: 42220,
  moonbeam: 1284,
};
