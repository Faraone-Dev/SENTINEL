// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/SentinelRegistry.sol";

/**
 * ╔═══════════════════════════════════════════════════════════════════════════╗
 * ║              SENTINEL SHIELD - GAS BENCHMARK SUITE                        ║
 * ╠═══════════════════════════════════════════════════════════════════════════╣
 * ║  Comprehensive gas measurement for all operations                         ║
 * ║  Compare against naive implementations to prove optimization              ║
 * ╚═══════════════════════════════════════════════════════════════════════════╝
 */

/// @notice Standard ERC20 mock
contract BenchmarkERC20 {
    mapping(address => mapping(address => uint256)) public allowance;
    
    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }
}

/// @notice Standard ERC721 mock
contract BenchmarkERC721 {
    mapping(uint256 => address) public ownerOf;
    mapping(uint256 => address) public getApproved;
    mapping(address => mapping(address => bool)) public isApprovedForAll;
    
    function mint(address to, uint256 tokenId) external {
        ownerOf[tokenId] = to;
    }
    
    function approve(address to, uint256 tokenId) external {
        getApproved[tokenId] = to;
    }
    
    function setApprovalForAll(address operator, bool approved) external {
        isApprovedForAll[msg.sender][operator] = approved;
    }
}

/// @notice Naive (non-optimized) implementation for comparison
contract NaiveRevoker {
    function revokeERC20(address token, address spender) external {
        // Standard Solidity call (no Yul optimization)
        (bool success,) = token.call(
            abi.encodeWithSignature("approve(address,uint256)", spender, 0)
        );
        require(success, "Revoke failed");
    }
    
    function batchRevokeERC20(address[] calldata tokens, address[] calldata spenders) external {
        require(tokens.length == spenders.length, "Length mismatch");
        for (uint i = 0; i < tokens.length; i++) {
            (bool success,) = tokens[i].call(
                abi.encodeWithSignature("approve(address,uint256)", spenders[i], 0)
            );
            require(success, "Revoke failed");
        }
    }
}

contract SentinelGasBenchmarkTest is Test {
    SentinelRegistry public registry;
    NaiveRevoker public naiveRevoker;
    
    BenchmarkERC20[] public tokens;
    BenchmarkERC721[] public nfts;
    address[] public spenders;
    
    uint256 constant NUM_TOKENS = 20;
    uint256 constant NUM_SPENDERS = 10;
    
    struct GasReport {
        string operation;
        uint256 sentinelGas;
        uint256 naiveGas;
        int256 savings;
        string savingsPercent;
    }
    
    GasReport[] public reports;
    
    function setUp() public {
        registry = new SentinelRegistry();
        naiveRevoker = new NaiveRevoker();
        
        for (uint i = 0; i < NUM_TOKENS; i++) {
            tokens.push(new BenchmarkERC20());
            nfts.push(new BenchmarkERC721());
        }
        
        for (uint i = 0; i < NUM_SPENDERS; i++) {
            spenders.push(address(uint160(0x1000 + i)));
        }
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                      SINGLE OPERATION BENCHMARKS
    // ═══════════════════════════════════════════════════════════════════════
    
    function test_Benchmark_SingleRevokeERC20() public {
        // Setup
        tokens[0].approve(spenders[0], 1000e18);
        
        // Sentinel
        uint256 gasBefore = gasleft();
        registry.revokeERC20(address(tokens[0]), spenders[0]);
        uint256 sentinelGas = gasBefore - gasleft();
        
        // Reset
        tokens[0].approve(spenders[0], 1000e18);
        
        // Naive
        gasBefore = gasleft();
        naiveRevoker.revokeERC20(address(tokens[0]), spenders[0]);
        uint256 naiveGas = gasBefore - gasleft();
        
        emit log_named_uint("Sentinel Gas", sentinelGas);
        emit log_named_uint("Naive Gas", naiveGas);
        emit log_named_int("Savings", int256(naiveGas) - int256(sentinelGas));
        
        // Sentinel should be at least as efficient
        assertLe(sentinelGas, naiveGas + 5000, "Sentinel should not be significantly worse");
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                      BATCH OPERATION BENCHMARKS
    // ═══════════════════════════════════════════════════════════════════════
    
    function test_Benchmark_BatchRevoke_5() public {
        _benchmarkBatch(5);
    }
    
    function test_Benchmark_BatchRevoke_10() public {
        _benchmarkBatch(10);
    }
    
    function test_Benchmark_BatchRevoke_20() public {
        _benchmarkBatch(20);
    }
    
    function test_Benchmark_BatchRevoke_50() public {
        _benchmarkBatch(50);
    }
    
    function test_Benchmark_BatchRevoke_100() public {
        _benchmarkBatch(100);
    }
    
    function _benchmarkBatch(uint256 size) internal {
        // Setup approvals
        for (uint i = 0; i < size; i++) {
            tokens[i % NUM_TOKENS].approve(spenders[i % NUM_SPENDERS], 1000e18);
        }
        
        // Prepare Sentinel batch
        SentinelRegistry.ERC20Revoke[] memory revokes = 
            new SentinelRegistry.ERC20Revoke[](size);
        for (uint i = 0; i < size; i++) {
            revokes[i] = SentinelRegistry.ERC20Revoke({
                token: address(tokens[i % NUM_TOKENS]),
                spender: spenders[i % NUM_SPENDERS]
            });
        }
        
        // Sentinel batch
        uint256 gasBefore = gasleft();
        registry.batchRevokeERC20(revokes);
        uint256 sentinelGas = gasBefore - gasleft();
        
        // Reset approvals
        for (uint i = 0; i < size; i++) {
            tokens[i % NUM_TOKENS].approve(spenders[i % NUM_SPENDERS], 1000e18);
        }
        
        // Prepare Naive batch
        address[] memory tokenAddrs = new address[](size);
        address[] memory spenderAddrs = new address[](size);
        for (uint i = 0; i < size; i++) {
            tokenAddrs[i] = address(tokens[i % NUM_TOKENS]);
            spenderAddrs[i] = spenders[i % NUM_SPENDERS];
        }
        
        // Naive batch
        gasBefore = gasleft();
        naiveRevoker.batchRevokeERC20(tokenAddrs, spenderAddrs);
        uint256 naiveGas = gasBefore - gasleft();
        
        // Calculate savings
        int256 savings = int256(naiveGas) - int256(sentinelGas);
        uint256 savingsPercent = naiveGas > 0 ? (uint256(savings > 0 ? savings : -savings) * 100) / naiveGas : 0;
        
        emit log_string("=====================================");
        emit log_named_uint("Batch Size", size);
        emit log_named_uint("Sentinel Gas", sentinelGas);
        emit log_named_uint("Naive Gas", naiveGas);
        emit log_named_int("Savings (gas)", savings);
        emit log_named_uint("Savings (%)", savingsPercent);
        emit log_named_uint("Gas per Item (Sentinel)", sentinelGas / size);
        emit log_named_uint("Gas per Item (Naive)", naiveGas / size);
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                      NFT BENCHMARKS
    // ═══════════════════════════════════════════════════════════════════════
    
    function test_Benchmark_SingleRevokeERC721() public {
        // Setup
        nfts[0].mint(address(this), 1);
        nfts[0].approve(spenders[0], 1);
        
        // Benchmark
        uint256 gasBefore = gasleft();
        registry.revokeERC721(address(nfts[0]), 1);
        uint256 gasUsed = gasBefore - gasleft();
        
        emit log_named_uint("ERC721 Single Revoke Gas", gasUsed);
        assertLt(gasUsed, 50000, "Gas too high");
    }
    
    function test_Benchmark_BatchRevokeERC721() public {
        uint256 size = 10;
        
        // Setup
        for (uint i = 0; i < size; i++) {
            nfts[i % NUM_TOKENS].mint(address(this), i + 100);
            nfts[i % NUM_TOKENS].approve(spenders[0], i + 100);
        }
        
        // Prepare batch
        SentinelRegistry.ERC721Revoke[] memory revokes = 
            new SentinelRegistry.ERC721Revoke[](size);
        for (uint i = 0; i < size; i++) {
            revokes[i] = SentinelRegistry.ERC721Revoke({
                collection: address(nfts[i % NUM_TOKENS]),
                tokenId: i + 100
            });
        }
        
        // Benchmark
        uint256 gasBefore = gasleft();
        registry.batchRevokeERC721(revokes);
        uint256 gasUsed = gasBefore - gasleft();
        
        emit log_named_uint("ERC721 Batch Revoke (10) Gas", gasUsed);
        emit log_named_uint("Gas per NFT", gasUsed / size);
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                      OPERATOR BENCHMARKS
    // ═══════════════════════════════════════════════════════════════════════
    
    function test_Benchmark_RevokeOperator() public {
        // Setup
        nfts[0].setApprovalForAll(spenders[0], true);
        
        // Benchmark
        uint256 gasBefore = gasleft();
        registry.revokeOperator(address(nfts[0]), spenders[0], false);
        uint256 gasUsed = gasBefore - gasleft();
        
        emit log_named_uint("Operator Revoke Gas", gasUsed);
        assertLt(gasUsed, 30000, "Gas too high");
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                      MIXED BATCH BENCHMARKS
    // ═══════════════════════════════════════════════════════════════════════
    
    function test_Benchmark_MixedBatchRevoke() public {
        // Setup ERC20
        for (uint i = 0; i < 5; i++) {
            tokens[i].approve(spenders[i % NUM_SPENDERS], 1000e18);
        }
        
        // Setup ERC721
        for (uint i = 0; i < 3; i++) {
            nfts[i].mint(address(this), i + 200);
            nfts[i].approve(spenders[0], i + 200);
        }
        
        // Setup operators
        for (uint i = 0; i < 2; i++) {
            nfts[i].setApprovalForAll(spenders[i], true);
        }
        
        // Prepare batches
        SentinelRegistry.ERC20Revoke[] memory erc20Revokes = 
            new SentinelRegistry.ERC20Revoke[](5);
        for (uint i = 0; i < 5; i++) {
            erc20Revokes[i] = SentinelRegistry.ERC20Revoke({
                token: address(tokens[i]),
                spender: spenders[i % NUM_SPENDERS]
            });
        }
        
        SentinelRegistry.ERC721Revoke[] memory erc721Revokes = 
            new SentinelRegistry.ERC721Revoke[](3);
        for (uint i = 0; i < 3; i++) {
            erc721Revokes[i] = SentinelRegistry.ERC721Revoke({
                collection: address(nfts[i]),
                tokenId: i + 200
            });
        }
        
        SentinelRegistry.OperatorRevoke[] memory opRevokes = 
            new SentinelRegistry.OperatorRevoke[](2);
        for (uint i = 0; i < 2; i++) {
            opRevokes[i] = SentinelRegistry.OperatorRevoke({
                collection: address(nfts[i]),
                operator: spenders[i],
                isERC1155: false
            });
        }
        
        // Benchmark
        uint256 gasBefore = gasleft();
        registry.batchRevokeAll(erc20Revokes, erc721Revokes, opRevokes);
        uint256 gasUsed = gasBefore - gasleft();
        
        emit log_string("=====================================");
        emit log_string("MIXED BATCH BENCHMARK");
        emit log_named_uint("Total Gas", gasUsed);
        emit log_named_uint("Items (5 ERC20 + 3 ERC721 + 2 Operators)", 10);
        emit log_named_uint("Gas per Item", gasUsed / 10);
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                      SCALING BENCHMARKS
    // ═══════════════════════════════════════════════════════════════════════
    
    function test_Benchmark_ScalingAnalysis() public {
        uint256[] memory sizes = new uint256[](5);
        sizes[0] = 1;
        sizes[1] = 5;
        sizes[2] = 10;
        sizes[3] = 25;
        sizes[4] = 50;
        
        uint256[] memory gasPerItem = new uint256[](5);
        
        for (uint s = 0; s < sizes.length; s++) {
            uint256 size = sizes[s];
            
            // Setup
            for (uint i = 0; i < size; i++) {
                tokens[i % NUM_TOKENS].approve(spenders[i % NUM_SPENDERS], 1000e18);
            }
            
            // Prepare batch
            SentinelRegistry.ERC20Revoke[] memory revokes = 
                new SentinelRegistry.ERC20Revoke[](size);
            for (uint i = 0; i < size; i++) {
                revokes[i] = SentinelRegistry.ERC20Revoke({
                    token: address(tokens[i % NUM_TOKENS]),
                    spender: spenders[i % NUM_SPENDERS]
                });
            }
            
            // Benchmark
            uint256 gasBefore = gasleft();
            registry.batchRevokeERC20(revokes);
            uint256 gasUsed = gasBefore - gasleft();
            
            gasPerItem[s] = gasUsed / size;
        }
        
        emit log_string("=====================================");
        emit log_string("SCALING ANALYSIS (Gas per item)");
        emit log_named_uint("Size 1", gasPerItem[0]);
        emit log_named_uint("Size 5", gasPerItem[1]);
        emit log_named_uint("Size 10", gasPerItem[2]);
        emit log_named_uint("Size 25", gasPerItem[3]);
        emit log_named_uint("Size 50", gasPerItem[4]);
        
        // Gas per item should decrease with batch size (amortized overhead)
        assertLt(gasPerItem[4], gasPerItem[0], "Batch should be more efficient");
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                      COST ESTIMATION
    // ═══════════════════════════════════════════════════════════════════════
    
    function test_Benchmark_CostEstimation() public {
        // Assume 30 gwei gas price, $2500 ETH
        uint256 gasPrice = 30 gwei;
        uint256 ethPrice = 2500;
        
        // Single revoke
        tokens[0].approve(spenders[0], 1000e18);
        uint256 gasBefore = gasleft();
        registry.revokeERC20(address(tokens[0]), spenders[0]);
        uint256 singleGas = gasBefore - gasleft();
        
        // Batch of 10
        for (uint i = 0; i < 10; i++) {
            tokens[i % NUM_TOKENS].approve(spenders[i % NUM_SPENDERS], 1000e18);
        }
        
        SentinelRegistry.ERC20Revoke[] memory revokes = 
            new SentinelRegistry.ERC20Revoke[](10);
        for (uint i = 0; i < 10; i++) {
            revokes[i] = SentinelRegistry.ERC20Revoke({
                token: address(tokens[i % NUM_TOKENS]),
                spender: spenders[i % NUM_SPENDERS]
            });
        }
        
        gasBefore = gasleft();
        registry.batchRevokeERC20(revokes);
        uint256 batch10Gas = gasBefore - gasleft();
        
        // Calculate costs
        uint256 singleCostWei = singleGas * gasPrice;
        uint256 batch10CostWei = batch10Gas * gasPrice;
        
        uint256 singleCostUsd = (singleCostWei * ethPrice) / 1e18;
        uint256 batch10CostUsd = (batch10CostWei * ethPrice) / 1e18;
        uint256 tenSinglesCostUsd = singleCostUsd * 10;
        
        emit log_string("=====================================");
        emit log_string("COST ESTIMATION (30 gwei, $2500/ETH)");
        emit log_named_uint("Single Revoke Gas", singleGas);
        emit log_named_uint("Batch 10 Gas", batch10Gas);
        emit log_named_uint("10x Single Gas", singleGas * 10);
        emit log_named_uint("Batch Savings (gas)", (singleGas * 10) - batch10Gas);
        emit log_string("---");
        emit log_string("USD Costs (in cents):");
        emit log_named_uint("Single Revoke (cents)", singleCostUsd * 100 / 1e15);
        emit log_named_uint("Batch 10 (cents)", batch10CostUsd * 100 / 1e15);
        emit log_named_uint("10x Single (cents)", tenSinglesCostUsd * 100 / 1e15);
    }
}
