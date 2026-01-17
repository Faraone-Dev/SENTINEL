// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/*
 ═══════════════════════════════════════════════════════════════════════════════
  SENTINEL SHIELD - Extended Foundry Tests
  Comprehensive test suite for smart contracts
  Author: SENTINEL Team
 ═══════════════════════════════════════════════════════════════════════════════
*/

import {Test, console2} from "forge-std/Test.sol";
import {SentinelRegistry} from "../src/SentinelRegistry.sol";

contract SentinelRegistryExtendedTest is Test {
    SentinelRegistry public registry;
    
    address public owner;
    address public user1;
    address public user2;
    address public attacker;
    
    MockERC20 public token1;
    MockERC20 public token2;
    MockERC20 public token3;
    MockERC721 public nft1;
    MockERC721 public nft2;
    
    address public spender1;
    address public spender2;
    address public spender3;
    
    event EmergencyRevoke(address indexed user, uint256 tokensRevoked, uint256 nftsRevoked);
    
    function setUp() public {
        owner = makeAddr("owner");
        user1 = makeAddr("user1");
        user2 = makeAddr("user2");
        attacker = makeAddr("attacker");
        
        spender1 = makeAddr("spender1");
        spender2 = makeAddr("spender2");
        spender3 = makeAddr("spender3");
        
        vm.startPrank(owner);
        registry = new SentinelRegistry();
        
        // Deploy mock tokens
        token1 = new MockERC20("Token1", "TK1");
        token2 = new MockERC20("Token2", "TK2");
        token3 = new MockERC20("Token3", "TK3");
        
        nft1 = new MockERC721("NFT1", "NFT1");
        nft2 = new MockERC721("NFT2", "NFT2");
        vm.stopPrank();
        
        // Mint tokens to users
        token1.mint(user1, 1000 ether);
        token2.mint(user1, 1000 ether);
        token3.mint(user1, 1000 ether);
        token1.mint(user2, 500 ether);
        
        // Mint NFTs
        nft1.mint(user1, 1);
        nft1.mint(user1, 2);
        nft2.mint(user1, 100);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //                          BASIC FUNCTIONALITY
    // ═══════════════════════════════════════════════════════════════════════════

    function test_BatchRevokeERC20_SingleToken() public {
        // Setup: User approves spender
        vm.startPrank(user1);
        token1.approve(spender1, type(uint256).max);
        assertEq(token1.allowance(user1, spender1), type(uint256).max);
        
        // Revoke
        address[] memory tokens = new address[](1);
        tokens[0] = address(token1);
        address[] memory spenders = new address[](1);
        spenders[0] = spender1;
        
        registry.batchRevokeERC20(tokens, spenders);
        vm.stopPrank();
        
        assertEq(token1.allowance(user1, spender1), 0);
    }

    function test_BatchRevokeERC20_MultipleTokens() public {
        // Setup: User approves multiple spenders
        vm.startPrank(user1);
        token1.approve(spender1, type(uint256).max);
        token2.approve(spender1, type(uint256).max);
        token3.approve(spender2, 1000 ether);
        
        // Revoke all
        address[] memory tokens = new address[](3);
        tokens[0] = address(token1);
        tokens[1] = address(token2);
        tokens[2] = address(token3);
        
        address[] memory spenders = new address[](3);
        spenders[0] = spender1;
        spenders[1] = spender1;
        spenders[2] = spender2;
        
        registry.batchRevokeERC20(tokens, spenders);
        vm.stopPrank();
        
        assertEq(token1.allowance(user1, spender1), 0);
        assertEq(token2.allowance(user1, spender1), 0);
        assertEq(token3.allowance(user1, spender2), 0);
    }

    function test_BatchRevokeERC721() public {
        // Setup: User approves NFTs
        vm.startPrank(user1);
        nft1.approve(spender1, 1);
        nft1.approve(spender2, 2);
        
        // Revoke
        address[] memory nfts = new address[](2);
        nfts[0] = address(nft1);
        nfts[1] = address(nft1);
        
        uint256[] memory tokenIds = new uint256[](2);
        tokenIds[0] = 1;
        tokenIds[1] = 2;
        
        registry.batchRevokeERC721(nfts, tokenIds);
        vm.stopPrank();
        
        assertEq(nft1.getApproved(1), address(0));
        assertEq(nft1.getApproved(2), address(0));
    }

    function test_BatchRevokeAll() public {
        // Setup: User approves everything
        vm.startPrank(user1);
        token1.approve(spender1, type(uint256).max);
        token2.approve(spender2, type(uint256).max);
        nft1.approve(spender1, 1);
        nft1.approve(spender2, 2);
        
        // Prepare arrays
        address[] memory tokens = new address[](2);
        tokens[0] = address(token1);
        tokens[1] = address(token2);
        
        address[] memory tokenSpenders = new address[](2);
        tokenSpenders[0] = spender1;
        tokenSpenders[1] = spender2;
        
        address[] memory nfts = new address[](2);
        nfts[0] = address(nft1);
        nfts[1] = address(nft1);
        
        uint256[] memory tokenIds = new uint256[](2);
        tokenIds[0] = 1;
        tokenIds[1] = 2;
        
        registry.batchRevokeAll(tokens, tokenSpenders, nfts, tokenIds);
        vm.stopPrank();
        
        // Verify all revoked
        assertEq(token1.allowance(user1, spender1), 0);
        assertEq(token2.allowance(user1, spender2), 0);
        assertEq(nft1.getApproved(1), address(0));
        assertEq(nft1.getApproved(2), address(0));
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //                          EDGE CASES
    // ═══════════════════════════════════════════════════════════════════════════

    function test_RevokeNonExistentApproval() public {
        // Should not revert when revoking non-existent approval
        vm.startPrank(user1);
        
        address[] memory tokens = new address[](1);
        tokens[0] = address(token1);
        address[] memory spenders = new address[](1);
        spenders[0] = spender1;
        
        // No prior approval exists
        registry.batchRevokeERC20(tokens, spenders);
        vm.stopPrank();
        
        // Should still be 0
        assertEq(token1.allowance(user1, spender1), 0);
    }

    function test_RevokeEmptyArrays() public {
        vm.startPrank(user1);
        
        address[] memory empty = new address[](0);
        uint256[] memory emptyIds = new uint256[](0);
        
        // Should not revert
        registry.batchRevokeERC20(empty, empty);
        registry.batchRevokeERC721(empty, emptyIds);
        registry.batchRevokeAll(empty, empty, empty, emptyIds);
        vm.stopPrank();
    }

    function test_RevertOnArrayMismatch_ERC20() public {
        vm.startPrank(user1);
        
        address[] memory tokens = new address[](2);
        tokens[0] = address(token1);
        tokens[1] = address(token2);
        
        address[] memory spenders = new address[](1);
        spenders[0] = spender1;
        
        vm.expectRevert(SentinelRegistry.ArrayLengthMismatch.selector);
        registry.batchRevokeERC20(tokens, spenders);
        vm.stopPrank();
    }

    function test_RevertOnArrayMismatch_ERC721() public {
        vm.startPrank(user1);
        
        address[] memory nfts = new address[](2);
        nfts[0] = address(nft1);
        nfts[1] = address(nft1);
        
        uint256[] memory tokenIds = new uint256[](1);
        tokenIds[0] = 1;
        
        vm.expectRevert(SentinelRegistry.ArrayLengthMismatch.selector);
        registry.batchRevokeERC721(nfts, tokenIds);
        vm.stopPrank();
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //                          GAS OPTIMIZATION TESTS
    // ═══════════════════════════════════════════════════════════════════════════

    function test_GasConsumption_10Approvals() public {
        vm.startPrank(user1);
        
        // Setup 10 approvals
        address[] memory tokens = new address[](10);
        address[] memory spenders = new address[](10);
        
        for (uint i = 0; i < 10; i++) {
            tokens[i] = address(token1);
            spenders[i] = makeAddr(string(abi.encodePacked("spender", i)));
            token1.approve(spenders[i], type(uint256).max);
        }
        
        uint256 gasBefore = gasleft();
        registry.batchRevokeERC20(tokens, spenders);
        uint256 gasUsed = gasBefore - gasleft();
        
        vm.stopPrank();
        
        console2.log("Gas used for 10 revocations:", gasUsed);
        // Should be efficient
        assertLt(gasUsed, 500000);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //                          SECURITY TESTS
    // ═══════════════════════════════════════════════════════════════════════════

    function test_CannotRevokeOthersApprovals() public {
        // User1 approves spender
        vm.prank(user1);
        token1.approve(spender1, type(uint256).max);
        
        // User2 tries to revoke User1's approval
        vm.startPrank(user2);
        address[] memory tokens = new address[](1);
        tokens[0] = address(token1);
        address[] memory spenders = new address[](1);
        spenders[0] = spender1;
        
        registry.batchRevokeERC20(tokens, spenders);
        vm.stopPrank();
        
        // User1's approval should still exist (revoke only affects msg.sender)
        assertEq(token1.allowance(user1, spender1), type(uint256).max);
    }

    function testFuzz_RevokeRandomApprovals(
        uint256 amount1,
        uint256 amount2,
        uint256 amount3
    ) public {
        vm.assume(amount1 > 0 && amount2 > 0 && amount3 > 0);
        
        vm.startPrank(user1);
        token1.approve(spender1, amount1);
        token2.approve(spender2, amount2);
        token3.approve(spender3, amount3);
        
        address[] memory tokens = new address[](3);
        tokens[0] = address(token1);
        tokens[1] = address(token2);
        tokens[2] = address(token3);
        
        address[] memory spenders = new address[](3);
        spenders[0] = spender1;
        spenders[1] = spender2;
        spenders[2] = spender3;
        
        registry.batchRevokeERC20(tokens, spenders);
        vm.stopPrank();
        
        assertEq(token1.allowance(user1, spender1), 0);
        assertEq(token2.allowance(user1, spender2), 0);
        assertEq(token3.allowance(user1, spender3), 0);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //                          EVENT TESTS
    // ═══════════════════════════════════════════════════════════════════════════

    function test_EmitsCorrectEvents() public {
        vm.startPrank(user1);
        token1.approve(spender1, type(uint256).max);
        nft1.approve(spender1, 1);
        
        address[] memory tokens = new address[](1);
        tokens[0] = address(token1);
        address[] memory spenders = new address[](1);
        spenders[0] = spender1;
        address[] memory nfts = new address[](1);
        nfts[0] = address(nft1);
        uint256[] memory tokenIds = new uint256[](1);
        tokenIds[0] = 1;
        
        vm.expectEmit(true, false, false, true);
        emit EmergencyRevoke(user1, 1, 1);
        
        registry.batchRevokeAll(tokens, spenders, nfts, tokenIds);
        vm.stopPrank();
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
//                          MOCK CONTRACTS
// ═══════════════════════════════════════════════════════════════════════════════

contract MockERC20 {
    string public name;
    string public symbol;
    uint8 public decimals = 18;
    uint256 public totalSupply;
    
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    
    constructor(string memory _name, string memory _symbol) {
        name = _name;
        symbol = _symbol;
    }
    
    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
        totalSupply += amount;
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
    
    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}

contract MockERC721 {
    string public name;
    string public symbol;
    
    mapping(uint256 => address) public ownerOf;
    mapping(uint256 => address) internal _approvals;
    mapping(address => mapping(address => bool)) public isApprovedForAll;
    
    constructor(string memory _name, string memory _symbol) {
        name = _name;
        symbol = _symbol;
    }
    
    function mint(address to, uint256 tokenId) external {
        ownerOf[tokenId] = to;
    }
    
    function approve(address to, uint256 tokenId) external {
        require(ownerOf[tokenId] == msg.sender, "Not owner");
        _approvals[tokenId] = to;
    }
    
    function getApproved(uint256 tokenId) external view returns (address) {
        return _approvals[tokenId];
    }
    
    function setApprovalForAll(address operator, bool approved) external {
        isApprovedForAll[msg.sender][operator] = approved;
    }
    
    function transferFrom(address from, address to, uint256 tokenId) external {
        require(ownerOf[tokenId] == from, "Not owner");
        _approvals[tokenId] = address(0);
        ownerOf[tokenId] = to;
    }
}
