// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {SentinelRegistry} from "../src/SentinelRegistry.sol";

/**
 * @title SentinelRegistryTest
 * @author SENTINEL Team
 * @notice Comprehensive test suite for SentinelRegistry
 */
contract SentinelRegistryTest is Test {
    SentinelRegistry public registry;
    
    address public alice = makeAddr("alice");
    address public bob = makeAddr("bob");
    address public mockToken;
    address public mockNFT;
    
    event ApprovalRevoked(address indexed owner, address indexed token, address indexed spender);
    event NFTApprovalRevoked(address indexed owner, address indexed collection, uint256 indexed tokenId);
    event OperatorRevoked(address indexed owner, address indexed collection, address indexed operator);
    event BatchRevokeComplete(address indexed owner, uint256 totalRevoked, uint256 gasUsed);

    function setUp() public {
        registry = new SentinelRegistry();
        
        // Deploy mock ERC20
        mockToken = address(new MockERC20());
        
        // Deploy mock ERC721
        mockNFT = address(new MockERC721());
        
        // Give Alice some tokens and approvals
        vm.startPrank(alice);
        MockERC20(mockToken).approve(bob, type(uint256).max);
        vm.stopPrank();
    }

    // ═══════════════════════════════════════════════════════════════════════
    //                         ERC20 TESTS
    // ═══════════════════════════════════════════════════════════════════════

    function test_RevokeERC20() public {
        // Check initial approval
        assertEq(MockERC20(mockToken).allowance(alice, bob), type(uint256).max);
        
        // Revoke
        vm.prank(alice);
        vm.expectEmit(true, true, true, true);
        emit ApprovalRevoked(alice, mockToken, bob);
        registry.revokeERC20(mockToken, bob);
        
        // Verify revoked
        assertEq(MockERC20(mockToken).allowance(alice, bob), 0);
    }

    function test_BatchRevokeERC20() public {
        // Setup multiple approvals
        address spender2 = makeAddr("spender2");
        address spender3 = makeAddr("spender3");
        
        vm.startPrank(alice);
        MockERC20(mockToken).approve(spender2, 1000e18);
        MockERC20(mockToken).approve(spender3, 500e18);
        vm.stopPrank();
        
        // Prepare batch
        SentinelRegistry.ERC20Revoke[] memory revokes = new SentinelRegistry.ERC20Revoke[](3);
        revokes[0] = SentinelRegistry.ERC20Revoke(mockToken, bob);
        revokes[1] = SentinelRegistry.ERC20Revoke(mockToken, spender2);
        revokes[2] = SentinelRegistry.ERC20Revoke(mockToken, spender3);
        
        // Execute batch revoke
        vm.prank(alice);
        registry.batchRevokeERC20(revokes);
        
        // Verify all revoked
        assertEq(MockERC20(mockToken).allowance(alice, bob), 0);
        assertEq(MockERC20(mockToken).allowance(alice, spender2), 0);
        assertEq(MockERC20(mockToken).allowance(alice, spender3), 0);
    }

    function test_RevertEmptyArray() public {
        SentinelRegistry.ERC20Revoke[] memory revokes = new SentinelRegistry.ERC20Revoke[](0);
        
        vm.prank(alice);
        vm.expectRevert(SentinelRegistry.EmptyArray.selector);
        registry.batchRevokeERC20(revokes);
    }

    function test_RevertInvalidToken() public {
        vm.prank(alice);
        vm.expectRevert(SentinelRegistry.InvalidTokenAddress.selector);
        registry.revokeERC20(address(0), bob);
    }

    // ═══════════════════════════════════════════════════════════════════════
    //                         GAS BENCHMARKS
    // ═══════════════════════════════════════════════════════════════════════

    function test_GasBenchmark_SingleRevoke() public {
        vm.prank(alice);
        uint256 gasBefore = gasleft();
        registry.revokeERC20(mockToken, bob);
        uint256 gasUsed = gasBefore - gasleft();
        console.log("Gas used for single revoke:", gasUsed);
    }

    function test_GasBenchmark_BatchRevoke10() public {
        // Setup 10 approvals
        SentinelRegistry.ERC20Revoke[] memory revokes = new SentinelRegistry.ERC20Revoke[](10);
        for (uint256 i = 0; i < 10; i++) {
            address spender = address(uint160(i + 100));
            vm.prank(alice);
            MockERC20(mockToken).approve(spender, 1000e18);
            revokes[i] = SentinelRegistry.ERC20Revoke(mockToken, spender);
        }
        
        vm.prank(alice);
        uint256 gasBefore = gasleft();
        registry.batchRevokeERC20(revokes);
        uint256 gasUsed = gasBefore - gasleft();
        console.log("Gas used for batch revoke (10):", gasUsed);
        console.log("Gas per revoke:", gasUsed / 10);
    }

    // ═══════════════════════════════════════════════════════════════════════
    //                         FUZZ TESTS
    // ═══════════════════════════════════════════════════════════════════════

    function testFuzz_RevokeERC20(address spender) public {
        vm.assume(spender != address(0));
        
        // Setup approval
        vm.prank(alice);
        MockERC20(mockToken).approve(spender, 1000e18);
        
        // Revoke
        vm.prank(alice);
        registry.revokeERC20(mockToken, spender);
        
        // Verify
        assertEq(MockERC20(mockToken).allowance(alice, spender), 0);
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
//                              MOCKS
// ═══════════════════════════════════════════════════════════════════════════════

contract MockERC20 {
    mapping(address => mapping(address => uint256)) public allowance;
    
    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }
}

contract MockERC721 {
    mapping(uint256 => address) public getApproved;
    mapping(address => mapping(address => bool)) public isApprovedForAll;
    
    function approve(address to, uint256 tokenId) external {
        getApproved[tokenId] = to;
    }
    
    function setApprovalForAll(address operator, bool approved) external {
        isApprovedForAll[msg.sender][operator] = approved;
    }
}
