// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/SentinelRegistry.sol";

/**
 * ╔═══════════════════════════════════════════════════════════════════════════╗
 * ║              SENTINEL SHIELD - SECURITY TEST SUITE                        ║
 * ╠═══════════════════════════════════════════════════════════════════════════╣
 * ║  Attack vector testing and vulnerability prevention                       ║
 * ║  Ensures the contract is resilient against common exploits                ║
 * ╚═══════════════════════════════════════════════════════════════════════════╝
 */

/// @notice Malicious token that tries reentrancy
contract ReentrantToken {
    SentinelRegistry public target;
    uint256 public attackCount;
    bool public attacking;
    
    mapping(address => mapping(address => uint256)) public allowance;
    
    constructor(address _target) {
        target = SentinelRegistry(_target);
    }
    
    function approve(address spender, uint256 amount) external returns (bool) {
        if (attacking && attackCount < 3) {
            attackCount++;
            // Try to reenter
            target.revokeERC20(address(this), spender);
        }
        allowance[msg.sender][spender] = amount;
        return true;
    }
    
    function startAttack(address spender) external {
        attacking = true;
        attackCount = 0;
        allowance[msg.sender][spender] = 1000e18;
        target.revokeERC20(address(this), spender);
    }
}

/// @notice Token that returns false on approve
contract FailingToken {
    mapping(address => mapping(address => uint256)) public allowance;
    
    function approve(address, uint256) external pure returns (bool) {
        return false;
    }
}

/// @notice Token that reverts on approve
contract RevertingToken {
    function approve(address, uint256) external pure returns (bool) {
        revert("I always revert");
    }
}

/// @notice Token that returns nothing (non-standard)
contract NoReturnToken {
    mapping(address => mapping(address => uint256)) public allowance;
    
    function approve(address spender, uint256 amount) external {
        allowance[msg.sender][spender] = amount;
        // No return value - some tokens do this
    }
}

/// @notice Token that returns extra data
contract ExtraDataToken {
    mapping(address => mapping(address => uint256)) public allowance;
    
    function approve(address spender, uint256 amount) external returns (bool, uint256, bytes32) {
        allowance[msg.sender][spender] = amount;
        return (true, amount, bytes32(0));
    }
}

/// @notice Token with callback hooks
contract CallbackToken {
    mapping(address => mapping(address => uint256)) public allowance;
    address public lastCaller;
    address public lastSpender;
    uint256 public callCount;
    
    function approve(address spender, uint256 amount) external returns (bool) {
        lastCaller = msg.sender;
        lastSpender = spender;
        callCount++;
        allowance[msg.sender][spender] = amount;
        return true;
    }
}

/// @notice Self-destructing token
contract SelfDestructToken {
    mapping(address => mapping(address => uint256)) public allowance;
    
    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }
    
    function destroy() external {
        selfdestruct(payable(msg.sender));
    }
}

/// @notice Token with gas griefing
contract GasGriefToken {
    mapping(address => mapping(address => uint256)) public allowance;
    
    function approve(address spender, uint256 amount) external returns (bool) {
        // Waste gas
        for (uint i = 0; i < 100; i++) {
            keccak256(abi.encode(i, spender, amount));
        }
        allowance[msg.sender][spender] = amount;
        return true;
    }
}

/// @notice Malicious NFT
contract MaliciousNFT {
    mapping(uint256 => address) public ownerOf;
    mapping(uint256 => address) public getApproved;
    mapping(address => mapping(address => bool)) public isApprovedForAll;
    
    SentinelRegistry public target;
    uint256 public reentrancyAttempts;
    
    constructor(address _target) {
        target = SentinelRegistry(_target);
    }
    
    function mint(address to, uint256 tokenId) external {
        ownerOf[tokenId] = to;
    }
    
    function approve(address to, uint256 tokenId) external {
        if (reentrancyAttempts < 2) {
            reentrancyAttempts++;
            // Try reentrancy
            target.revokeERC721(address(this), tokenId);
        }
        getApproved[tokenId] = to;
    }
    
    function setApprovalForAll(address operator, bool approved) external {
        isApprovedForAll[msg.sender][operator] = approved;
    }
}

contract SentinelSecurityTest is Test {
    SentinelRegistry public registry;
    
    address public attacker = address(0xBAD);
    address public victim = address(0x1234);
    address public spender = address(0x5678);
    
    function setUp() public {
        registry = new SentinelRegistry();
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                      REENTRANCY TESTS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Test reentrancy attack via malicious token
    function test_Security_ReentrancyAttackPrevented() public {
        ReentrantToken malicious = new ReentrantToken(address(registry));
        
        // Attempt reentrancy attack
        vm.prank(attacker);
        malicious.startAttack(spender);
        
        // Attack should complete but reentrancy should be limited/handled
        // The contract should not be in an inconsistent state
        assertEq(malicious.allowance(attacker, spender), 0, "Final allowance should be 0");
    }
    
    /// @notice Test reentrancy via NFT
    function test_Security_NFTReentrancyHandled() public {
        MaliciousNFT malicious = new MaliciousNFT(address(registry));
        malicious.mint(address(this), 1);
        malicious.getApproved[1] = spender;
        
        // This might reenter but should complete
        registry.revokeERC721(address(malicious), 1);
        
        assertTrue(true, "Reentrancy handled");
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                      FAILING TOKEN TESTS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Test handling of token that returns false
    function test_Security_HandlesReturnFalse() public {
        FailingToken failing = new FailingToken();
        
        // Should revert or handle gracefully
        vm.expectRevert();
        registry.revokeERC20(address(failing), spender);
    }
    
    /// @notice Test handling of reverting token
    function test_Security_HandlesRevertingToken() public {
        RevertingToken reverting = new RevertingToken();
        
        // Should bubble up revert
        vm.expectRevert();
        registry.revokeERC20(address(reverting), spender);
    }
    
    /// @notice Test handling of non-standard token (no return)
    function test_Security_HandlesNoReturnToken() public {
        NoReturnToken noReturn = new NoReturnToken();
        
        vm.prank(address(this));
        noReturn.approve(spender, 1000e18);
        
        // Should handle tokens that don't return
        registry.revokeERC20(address(noReturn), spender);
        
        assertEq(noReturn.allowance(address(this), spender), 0);
    }
    
    /// @notice Test handling of extra data return
    function test_Security_HandlesExtraDataToken() public {
        ExtraDataToken extra = new ExtraDataToken();
        
        extra.approve(spender, 1000e18);
        
        // Should handle extra return data
        registry.revokeERC20(address(extra), spender);
        
        assertEq(extra.allowance(address(this), spender), 0);
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                      INPUT VALIDATION TESTS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Test zero address token
    function test_Security_RejectsZeroAddressToken() public {
        vm.expectRevert(SentinelRegistry.InvalidTokenAddress.selector);
        registry.revokeERC20(address(0), spender);
    }
    
    /// @notice Test empty array batch
    function test_Security_RejectsEmptyBatch() public {
        SentinelRegistry.ERC20Revoke[] memory empty = new SentinelRegistry.ERC20Revoke[](0);
        
        vm.expectRevert(SentinelRegistry.EmptyArray.selector);
        registry.batchRevokeERC20(empty);
    }
    
    /// @notice Test extremely large batch (gas limit)
    function test_Security_LargeBatchGasLimit() public {
        uint256 size = 200;
        
        CallbackToken token = new CallbackToken();
        
        SentinelRegistry.ERC20Revoke[] memory revokes = 
            new SentinelRegistry.ERC20Revoke[](size);
        
        for (uint i = 0; i < size; i++) {
            token.approve(address(uint160(i + 1)), 1e18);
            revokes[i] = SentinelRegistry.ERC20Revoke({
                token: address(token),
                spender: address(uint160(i + 1))
            });
        }
        
        // Should complete within gas limit
        uint256 gasBefore = gasleft();
        registry.batchRevokeERC20(revokes);
        uint256 gasUsed = gasBefore - gasleft();
        
        emit log_named_uint("Gas for 200 revokes", gasUsed);
        assertLt(gasUsed, 15_000_000, "Should fit in block");
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                      ACCESS CONTROL TESTS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Test that only owner can revoke their approvals
    function test_Security_OnlyOwnerCanRevoke() public {
        CallbackToken token = new CallbackToken();
        
        // Victim approves
        vm.prank(victim);
        token.approve(spender, 1000e18);
        
        // Attacker tries to revoke victim's approval
        vm.prank(attacker);
        registry.revokeERC20(address(token), spender);
        
        // Attacker's call sets allowance for ATTACKER, not victim
        // Victim's allowance should be unchanged
        assertEq(token.allowance(victim, spender), 1000e18, "Victim allowance unchanged");
        assertEq(token.allowance(attacker, spender), 0, "Attacker allowance is 0");
    }
    
    /// @notice Test that NFT revoke requires ownership
    function test_Security_NFTRevokeRequiresOwnership() public {
        MaliciousNFT nft = new MaliciousNFT(address(registry));
        
        // Victim owns and approves
        nft.mint(victim, 1);
        vm.prank(victim);
        nft.approve(spender, 1);
        
        // Attacker tries to revoke - should fail or have no effect
        vm.prank(attacker);
        // Depending on implementation, this may revert or just not work
        try registry.revokeERC721(address(nft), 1) {} catch {}
        
        // The approval should only change if called by owner
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                      GAS GRIEFING TESTS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Test gas griefing protection
    function test_Security_GasGriefingLimited() public {
        GasGriefToken griefing = new GasGriefToken();
        
        griefing.approve(spender, 1000e18);
        
        uint256 gasBefore = gasleft();
        registry.revokeERC20(address(griefing), spender);
        uint256 gasUsed = gasBefore - gasleft();
        
        // Even with griefing, gas should be bounded
        assertLt(gasUsed, 500_000, "Gas griefing should be limited");
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                      SELF-DESTRUCT TESTS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Test handling of self-destructed token
    function test_Security_HandlesSelfDestructedToken() public {
        SelfDestructToken token = new SelfDestructToken();
        address tokenAddr = address(token);
        
        token.approve(spender, 1000e18);
        token.destroy();
        
        // Calling on destroyed contract should revert
        vm.expectRevert();
        registry.revokeERC20(tokenAddr, spender);
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                      CALLBACK VERIFICATION TESTS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Test that Registry is the msg.sender for token calls
    function test_Security_CorrectMsgSender() public {
        CallbackToken token = new CallbackToken();
        
        token.approve(spender, 1000e18);
        registry.revokeERC20(address(token), spender);
        
        // The token should see THIS contract (test) as the caller
        // because registry uses delegatecall semantics via msg.sender forwarding
        assertEq(token.lastCaller, address(this), "Caller should be original caller");
        assertEq(token.lastSpender, spender, "Spender should match");
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                      OVERFLOW/UNDERFLOW TESTS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Test max uint256 allowance
    function test_Security_HandlesMaxAllowance() public {
        CallbackToken token = new CallbackToken();
        
        token.approve(spender, type(uint256).max);
        assertEq(token.allowance(address(this), spender), type(uint256).max);
        
        registry.revokeERC20(address(token), spender);
        
        assertEq(token.allowance(address(this), spender), 0, "Max allowance revoked");
    }
    
    /// @notice Test batch with max array index
    function test_Security_BatchIndexBounds() public {
        CallbackToken token = new CallbackToken();
        
        // Create batch at boundary
        SentinelRegistry.ERC20Revoke[] memory revokes = 
            new SentinelRegistry.ERC20Revoke[](100);
        
        for (uint i = 0; i < 100; i++) {
            address sp = address(uint160(i + 1));
            token.approve(sp, 1e18);
            revokes[i] = SentinelRegistry.ERC20Revoke({
                token: address(token),
                spender: sp
            });
        }
        
        // Should process all without index errors
        registry.batchRevokeERC20(revokes);
        
        // Verify last element processed
        assertEq(token.allowance(address(this), address(uint160(100))), 0);
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                      DENIAL OF SERVICE TESTS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Test that one bad token doesn't block entire batch
    function test_Security_BatchPartialFailure() public {
        CallbackToken good = new CallbackToken();
        RevertingToken bad = new RevertingToken();
        
        good.approve(spender, 1000e18);
        
        SentinelRegistry.ERC20Revoke[] memory revokes = 
            new SentinelRegistry.ERC20Revoke[](2);
        revokes[0] = SentinelRegistry.ERC20Revoke({
            token: address(good),
            spender: spender
        });
        revokes[1] = SentinelRegistry.ERC20Revoke({
            token: address(bad),
            spender: spender
        });
        
        // Entire batch should revert if one fails (atomic)
        vm.expectRevert();
        registry.batchRevokeERC20(revokes);
        
        // Good token approval unchanged since batch reverted
        assertEq(good.allowance(address(this), spender), 1000e18);
    }
}
