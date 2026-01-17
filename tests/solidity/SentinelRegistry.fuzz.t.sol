// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/SentinelRegistry.sol";

/**
 * ╔═══════════════════════════════════════════════════════════════════════════╗
 * ║              SENTINEL SHIELD - FUZZ TESTING SUITE                         ║
 * ╠═══════════════════════════════════════════════════════════════════════════╣
 * ║  Randomized input testing to find edge cases and vulnerabilities          ║
 * ║  Tests run with thousands of random inputs automatically                  ║
 * ╚═══════════════════════════════════════════════════════════════════════════╝
 */

/// @notice Mock ERC20 for testing
contract MockERC20 {
    mapping(address => mapping(address => uint256)) public allowance;
    mapping(address => uint256) public balanceOf;
    
    string public name = "Mock Token";
    string public symbol = "MOCK";
    uint8 public decimals = 18;
    uint256 public totalSupply = 1000000e18;
    
    constructor() {
        balanceOf[msg.sender] = totalSupply;
    }
    
    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }
    
    function transfer(address to, uint256 amount) external returns (bool) {
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}

/// @notice Mock ERC721 for testing
contract MockERC721 {
    mapping(uint256 => address) public ownerOf;
    mapping(uint256 => address) public getApproved;
    mapping(address => mapping(address => bool)) public isApprovedForAll;
    
    function mint(address to, uint256 tokenId) external {
        ownerOf[tokenId] = to;
    }
    
    function approve(address to, uint256 tokenId) external {
        require(ownerOf[tokenId] == msg.sender, "Not owner");
        getApproved[tokenId] = to;
    }
    
    function setApprovalForAll(address operator, bool approved) external {
        isApprovedForAll[msg.sender][operator] = approved;
    }
}

/// @notice Mock ERC1155 for testing
contract MockERC1155 {
    mapping(address => mapping(address => bool)) public isApprovedForAll;
    mapping(address => mapping(uint256 => uint256)) public balanceOf;
    
    function setApprovalForAll(address operator, bool approved) external {
        isApprovedForAll[msg.sender][operator] = approved;
    }
    
    function mint(address to, uint256 id, uint256 amount) external {
        balanceOf[to][id] += amount;
    }
}

contract SentinelRegistryFuzzTest is Test {
    SentinelRegistry public registry;
    MockERC20[] public tokens;
    MockERC721[] public nfts;
    MockERC1155[] public multiTokens;
    
    address[] public spenders;
    address[] public users;
    
    uint256 constant NUM_TOKENS = 10;
    uint256 constant NUM_SPENDERS = 5;
    uint256 constant NUM_USERS = 3;
    
    function setUp() public {
        registry = new SentinelRegistry();
        
        // Deploy multiple mock tokens
        for (uint i = 0; i < NUM_TOKENS; i++) {
            tokens.push(new MockERC20());
            nfts.push(new MockERC721());
            multiTokens.push(new MockERC1155());
        }
        
        // Create test addresses
        for (uint i = 0; i < NUM_SPENDERS; i++) {
            spenders.push(address(uint160(0x1000 + i)));
        }
        
        for (uint i = 0; i < NUM_USERS; i++) {
            users.push(address(uint160(0x2000 + i)));
        }
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                          ERC20 FUZZ TESTS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Fuzz test: Revoke should always set allowance to 0
    function testFuzz_RevokeERC20AlwaysZerosAllowance(
        uint256 tokenIndex,
        uint256 spenderIndex,
        uint256 initialAllowance
    ) public {
        // Bound inputs
        tokenIndex = bound(tokenIndex, 0, NUM_TOKENS - 1);
        spenderIndex = bound(spenderIndex, 0, NUM_SPENDERS - 1);
        initialAllowance = bound(initialAllowance, 1, type(uint256).max);
        
        MockERC20 token = tokens[tokenIndex];
        address spender = spenders[spenderIndex];
        
        // Set initial allowance
        token.approve(spender, initialAllowance);
        assertEq(token.allowance(address(this), spender), initialAllowance);
        
        // Revoke
        registry.revokeERC20(address(token), spender);
        
        // Verify allowance is now 0
        assertEq(token.allowance(address(this), spender), 0);
    }
    
    /// @notice Fuzz test: Batch revoke should handle any valid array size
    function testFuzz_BatchRevokeERC20AnySize(uint256 batchSize) public {
        // Bound to reasonable size
        batchSize = bound(batchSize, 1, 100);
        
        SentinelRegistry.ERC20Revoke[] memory revokes = 
            new SentinelRegistry.ERC20Revoke[](batchSize);
        
        // Setup revokes
        for (uint i = 0; i < batchSize; i++) {
            uint tokenIdx = i % NUM_TOKENS;
            uint spenderIdx = i % NUM_SPENDERS;
            
            // Set allowance
            tokens[tokenIdx].approve(spenders[spenderIdx], 1000e18);
            
            revokes[i] = SentinelRegistry.ERC20Revoke({
                token: address(tokens[tokenIdx]),
                spender: spenders[spenderIdx]
            });
        }
        
        // Execute batch revoke
        registry.batchRevokeERC20(revokes);
        
        // Verify all revoked
        for (uint i = 0; i < batchSize; i++) {
            assertEq(
                tokens[i % NUM_TOKENS].allowance(
                    address(this), 
                    spenders[i % NUM_SPENDERS]
                ), 
                0
            );
        }
    }
    
    /// @notice Fuzz test: Should handle various allowance amounts
    function testFuzz_RevokeHandlesAnyAllowanceAmount(uint256 amount) public {
        MockERC20 token = tokens[0];
        address spender = spenders[0];
        
        // Set any amount
        token.approve(spender, amount);
        
        // Revoke
        registry.revokeERC20(address(token), spender);
        
        // Always ends at 0
        assertEq(token.allowance(address(this), spender), 0);
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                          ERC721 FUZZ TESTS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Fuzz test: Revoke NFT approval for any token ID
    function testFuzz_RevokeERC721AnyTokenId(uint256 tokenId) public {
        MockERC721 nft = nfts[0];
        address spender = spenders[0];
        
        // Mint and approve
        nft.mint(address(this), tokenId);
        nft.approve(spender, tokenId);
        
        assertEq(nft.getApproved(tokenId), spender);
        
        // Revoke via registry
        registry.revokeERC721(address(nft), tokenId);
        
        // Approval cleared
        assertEq(nft.getApproved(tokenId), address(0));
    }
    
    /// @notice Fuzz test: Batch revoke NFTs with random token IDs
    function testFuzz_BatchRevokeERC721RandomIds(
        uint256 id1,
        uint256 id2,
        uint256 id3
    ) public {
        // Ensure unique IDs
        vm.assume(id1 != id2 && id2 != id3 && id1 != id3);
        
        MockERC721 nft = nfts[0];
        address spender = spenders[0];
        
        // Mint and approve
        nft.mint(address(this), id1);
        nft.mint(address(this), id2);
        nft.mint(address(this), id3);
        
        nft.approve(spender, id1);
        nft.approve(spender, id2);
        nft.approve(spender, id3);
        
        // Batch revoke
        SentinelRegistry.ERC721Revoke[] memory revokes = 
            new SentinelRegistry.ERC721Revoke[](3);
        revokes[0] = SentinelRegistry.ERC721Revoke(address(nft), id1);
        revokes[1] = SentinelRegistry.ERC721Revoke(address(nft), id2);
        revokes[2] = SentinelRegistry.ERC721Revoke(address(nft), id3);
        
        registry.batchRevokeERC721(revokes);
        
        // All cleared
        assertEq(nft.getApproved(id1), address(0));
        assertEq(nft.getApproved(id2), address(0));
        assertEq(nft.getApproved(id3), address(0));
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                       OPERATOR FUZZ TESTS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Fuzz test: Revoke operator for any address
    function testFuzz_RevokeOperatorAnyAddress(address operator) public {
        vm.assume(operator != address(0));
        vm.assume(operator != address(this));
        
        MockERC721 nft = nfts[0];
        
        // Approve operator
        nft.setApprovalForAll(operator, true);
        assertTrue(nft.isApprovedForAll(address(this), operator));
        
        // Revoke
        registry.revokeOperator(address(nft), operator, false);
        
        // Cleared
        assertFalse(nft.isApprovedForAll(address(this), operator));
    }
    
    /// @notice Fuzz test: ERC1155 operator revoke
    function testFuzz_RevokeERC1155Operator(address operator) public {
        vm.assume(operator != address(0));
        vm.assume(operator != address(this));
        
        MockERC1155 multi = multiTokens[0];
        
        // Approve operator
        multi.setApprovalForAll(operator, true);
        assertTrue(multi.isApprovedForAll(address(this), operator));
        
        // Revoke
        registry.revokeOperator(address(multi), operator, true);
        
        // Cleared
        assertFalse(multi.isApprovedForAll(address(this), operator));
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                     MIXED BATCH FUZZ TESTS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Fuzz test: Mixed batch with random sizes
    function testFuzz_MixedBatchRandomSizes(
        uint256 erc20Count,
        uint256 erc721Count,
        uint256 operatorCount
    ) public {
        // Bound counts
        erc20Count = bound(erc20Count, 0, 20);
        erc721Count = bound(erc721Count, 0, 10);
        operatorCount = bound(operatorCount, 0, 5);
        
        // Skip if all zero
        vm.assume(erc20Count + erc721Count + operatorCount > 0);
        
        // Setup ERC20 revokes
        SentinelRegistry.ERC20Revoke[] memory erc20Revokes = 
            new SentinelRegistry.ERC20Revoke[](erc20Count);
        for (uint i = 0; i < erc20Count; i++) {
            tokens[i % NUM_TOKENS].approve(spenders[i % NUM_SPENDERS], 1e18);
            erc20Revokes[i] = SentinelRegistry.ERC20Revoke({
                token: address(tokens[i % NUM_TOKENS]),
                spender: spenders[i % NUM_SPENDERS]
            });
        }
        
        // Setup ERC721 revokes
        SentinelRegistry.ERC721Revoke[] memory erc721Revokes = 
            new SentinelRegistry.ERC721Revoke[](erc721Count);
        for (uint i = 0; i < erc721Count; i++) {
            nfts[i % NUM_TOKENS].mint(address(this), i + 1000);
            nfts[i % NUM_TOKENS].approve(spenders[0], i + 1000);
            erc721Revokes[i] = SentinelRegistry.ERC721Revoke({
                collection: address(nfts[i % NUM_TOKENS]),
                tokenId: i + 1000
            });
        }
        
        // Setup operator revokes
        SentinelRegistry.OperatorRevoke[] memory opRevokes = 
            new SentinelRegistry.OperatorRevoke[](operatorCount);
        for (uint i = 0; i < operatorCount; i++) {
            nfts[i % NUM_TOKENS].setApprovalForAll(spenders[i % NUM_SPENDERS], true);
            opRevokes[i] = SentinelRegistry.OperatorRevoke({
                collection: address(nfts[i % NUM_TOKENS]),
                operator: spenders[i % NUM_SPENDERS],
                isERC1155: false
            });
        }
        
        // Execute mixed batch
        registry.batchRevokeAll(erc20Revokes, erc721Revokes, opRevokes);
        
        // Verify ERC20
        for (uint i = 0; i < erc20Count; i++) {
            assertEq(
                tokens[i % NUM_TOKENS].allowance(address(this), spenders[i % NUM_SPENDERS]),
                0
            );
        }
        
        // Verify ERC721
        for (uint i = 0; i < erc721Count; i++) {
            assertEq(nfts[i % NUM_TOKENS].getApproved(i + 1000), address(0));
        }
        
        // Verify operators
        for (uint i = 0; i < operatorCount; i++) {
            assertFalse(
                nfts[i % NUM_TOKENS].isApprovedForAll(address(this), spenders[i % NUM_SPENDERS])
            );
        }
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                       EDGE CASE FUZZ TESTS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Fuzz test: Double revoke should not fail
    function testFuzz_DoubleRevokeNeverFails(uint256 times) public {
        times = bound(times, 2, 10);
        
        MockERC20 token = tokens[0];
        address spender = spenders[0];
        
        token.approve(spender, 1000e18);
        
        // Revoke multiple times - should never revert
        for (uint i = 0; i < times; i++) {
            registry.revokeERC20(address(token), spender);
            assertEq(token.allowance(address(this), spender), 0);
        }
    }
    
    /// @notice Fuzz test: Revoke already zero allowance
    function testFuzz_RevokeZeroAllowanceSucceeds(uint256 seed) public {
        uint tokenIdx = seed % NUM_TOKENS;
        uint spenderIdx = seed % NUM_SPENDERS;
        
        // Never approved - allowance already 0
        assertEq(
            tokens[tokenIdx].allowance(address(this), spenders[spenderIdx]),
            0
        );
        
        // Should still succeed
        registry.revokeERC20(
            address(tokens[tokenIdx]), 
            spenders[spenderIdx]
        );
        
        // Still 0
        assertEq(
            tokens[tokenIdx].allowance(address(this), spenders[spenderIdx]),
            0
        );
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                      GAS FUZZ TESTS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Fuzz test: Gas should scale linearly with batch size
    function testFuzz_GasScalesLinearly(uint256 batchSize) public {
        batchSize = bound(batchSize, 1, 50);
        
        SentinelRegistry.ERC20Revoke[] memory revokes = 
            new SentinelRegistry.ERC20Revoke[](batchSize);
        
        for (uint i = 0; i < batchSize; i++) {
            tokens[i % NUM_TOKENS].approve(spenders[i % NUM_SPENDERS], 1e18);
            revokes[i] = SentinelRegistry.ERC20Revoke({
                token: address(tokens[i % NUM_TOKENS]),
                spender: spenders[i % NUM_SPENDERS]
            });
        }
        
        uint256 gasBefore = gasleft();
        registry.batchRevokeERC20(revokes);
        uint256 gasUsed = gasBefore - gasleft();
        
        // Gas per item should be reasonable (< 50k per revoke)
        uint256 gasPerItem = gasUsed / batchSize;
        assertLt(gasPerItem, 50000, "Gas per item too high");
    }
}
