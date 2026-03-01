// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/*
 ██████╗ ███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗
██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║
███████╗ █████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║
╚════██║ ██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║
███████║ ███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
╚══════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝

 SENTINEL SHIELD - Batch Token Approval Revocation Registry
 
 ╔═══════════════════════════════════════════════════════════════════════════╗
 ║                                                                           ║
 ║  This contract allows users to revoke multiple token approvals in a       ║
 ║  single transaction, saving gas and providing atomic execution.           ║
 ║                                                                           ║
 ║  Features:                                                                ║
 ║  - Batch revoke ERC20 approvals                                           ║
 ║  - Batch revoke ERC721 approvals                                          ║
 ║  - Batch revoke ERC1155 approvals                                         ║
 ║  - Gas-optimized using inline assembly                                    ║
 ║  - No admin keys, fully permissionless                                    ║
 ║                                                                           ║
 ║  Author: SENTINEL Team                                                      ║
 ╚═══════════════════════════════════════════════════════════════════════════╝
*/

/// @title SentinelRegistry - Multi-standard approval revocation
/// @author SENTINEL Team
/// @notice Batch revoke token approvals across ERC20, ERC721, ERC1155
/// @dev Uses inline Yul for gas optimization
contract SentinelRegistry {
    
    // ═══════════════════════════════════════════════════════════════════════
    //                              EVENTS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Emitted when ERC20 approval is revoked
    event ApprovalRevoked(
        address indexed owner,
        address indexed token,
        address indexed spender
    );
    
    /// @notice Emitted when ERC721 approval is revoked
    event NFTApprovalRevoked(
        address indexed owner,
        address indexed collection,
        uint256 indexed tokenId
    );
    
    /// @notice Emitted when ERC721/ERC1155 operator is revoked
    event OperatorRevoked(
        address indexed owner,
        address indexed collection,
        address indexed operator
    );
    
    /// @notice Emitted when batch operation completes
    event BatchRevokeComplete(
        address indexed owner,
        uint256 totalRevoked,
        uint256 gasUsed
    );
    
    // ═══════════════════════════════════════════════════════════════════════
    //                              ERRORS
    // ═══════════════════════════════════════════════════════════════════════
    
    error EmptyArray();
    error ArrayLengthMismatch();
    error RevokeFailed(address token, address spender);
    error InvalidTokenAddress();
    
    // ═══════════════════════════════════════════════════════════════════════
    //                              STRUCTS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Represents an ERC20 approval to revoke
    struct ERC20Revoke {
        address token;
        address spender;
    }
    
    /// @notice Represents an ERC721 token approval to revoke
    struct ERC721Revoke {
        address collection;
        uint256 tokenId;
    }
    
    /// @notice Represents an operator approval to revoke (ERC721/ERC1155)
    /// @dev setApprovalForAll works identically for both standards
    struct OperatorRevoke {
        address collection;
        address operator;
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                         ERC20 FUNCTIONS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Revoke a single ERC20 approval (sets allowance to 0)
    /// @param token The ERC20 token address
    /// @param spender The spender address to revoke
    function revokeERC20(address token, address spender) external {
        _revokeERC20(token, spender);
        emit ApprovalRevoked(msg.sender, token, spender);
    }
    
    /// @notice Batch revoke multiple ERC20 approvals
    /// @param revokes Array of token/spender pairs to revoke
    function batchRevokeERC20(ERC20Revoke[] calldata revokes) external {
        uint256 length = revokes.length;
        if (length == 0) revert EmptyArray();
        
        uint256 gasStart = gasleft();
        
        for (uint256 i = 0; i < length;) {
            _revokeERC20(revokes[i].token, revokes[i].spender);
            emit ApprovalRevoked(msg.sender, revokes[i].token, revokes[i].spender);
            
            unchecked { ++i; }
        }
        
        emit BatchRevokeComplete(msg.sender, length, gasStart - gasleft());
    }
    
    /// @dev Internal ERC20 revoke using Yul for gas optimization
    function _revokeERC20(address token, address spender) internal {
        if (token == address(0)) revert InvalidTokenAddress();
        
        // ERC20 approve(spender, 0) selector: 0x095ea7b3
        // We use inline assembly for maximum gas efficiency
        
        assembly {
            // Allocate memory for the call
            let ptr := mload(0x40)
            
            // Store function selector: approve(address,uint256)
            mstore(ptr, 0x095ea7b300000000000000000000000000000000000000000000000000000000)
            
            // Store spender address (padded to 32 bytes)
            mstore(add(ptr, 4), spender)
            
            // Store amount = 0
            mstore(add(ptr, 36), 0)
            
            // Call the token contract
            // call(gas, to, value, inputOffset, inputSize, outputOffset, outputSize)
            let success := call(
                gas(),      // Forward all gas
                token,      // Token address
                0,          // No ETH
                ptr,        // Input starts at ptr
                68,         // Input size: 4 (selector) + 32 (address) + 32 (amount)
                ptr,        // Store output at ptr
                32          // Output size
            )
            
            // Check success
            // Note: Some tokens don't return a value, so we also check for empty return
            if iszero(success) {
                // Check if it's because the call reverted
                if iszero(returndatasize()) {
                    // Contract doesn't exist or call failed
                    revert(0, 0)
                }
                // If there's return data, it might be an error
                revert(0, 0)
            }
            
            // If there's return data, verify it's true (or empty for non-compliant tokens)
            if gt(returndatasize(), 0) {
                // Load the return value
                let result := mload(ptr)
                if iszero(result) {
                    // Returned false
                    revert(0, 0)
                }
            }
        }
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                         ERC721 FUNCTIONS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Revoke approval for a specific ERC721 token
    /// @param collection The ERC721 collection address
    /// @param tokenId The token ID to revoke approval for
    function revokeERC721(address collection, uint256 tokenId) external {
        _revokeERC721Approval(collection, tokenId);
        emit NFTApprovalRevoked(msg.sender, collection, tokenId);
    }
    
    /// @notice Batch revoke approvals for multiple ERC721 tokens
    /// @param revokes Array of collection/tokenId pairs to revoke
    function batchRevokeERC721(ERC721Revoke[] calldata revokes) external {
        uint256 length = revokes.length;
        if (length == 0) revert EmptyArray();
        
        uint256 gasStart = gasleft();
        
        for (uint256 i = 0; i < length;) {
            _revokeERC721Approval(revokes[i].collection, revokes[i].tokenId);
            emit NFTApprovalRevoked(msg.sender, revokes[i].collection, revokes[i].tokenId);
            
            unchecked { ++i; }
        }
        
        emit BatchRevokeComplete(msg.sender, length, gasStart - gasleft());
    }
    
    /// @dev Internal ERC721 approval revoke using Yul
    function _revokeERC721Approval(address collection, uint256 tokenId) internal {
        if (collection == address(0)) revert InvalidTokenAddress();
        
        // ERC721 approve(address, uint256) selector: 0x095ea7b3
        // We set approved address to address(0) to revoke
        
        assembly {
            let ptr := mload(0x40)
            
            // Store selector: approve(address,uint256)
            mstore(ptr, 0x095ea7b300000000000000000000000000000000000000000000000000000000)
            
            // Store approved address = address(0)
            mstore(add(ptr, 4), 0)
            
            // Store tokenId
            mstore(add(ptr, 36), tokenId)
            
            let success := call(gas(), collection, 0, ptr, 68, ptr, 32)
            
            // ERC721 approve doesn't return a value, so just check call success
            if iszero(success) {
                revert(0, 0)
            }
        }
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                       OPERATOR FUNCTIONS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Revoke operator approval (ERC721 setApprovalForAll or ERC1155)
    /// @param collection The collection address
    /// @param operator The operator address to revoke
    /// @dev Uses setApprovalForAll(operator, false) which works for both ERC721 and ERC1155
    function revokeOperator(address collection, address operator) external {
        _revokeOperator(collection, operator);
        emit OperatorRevoked(msg.sender, collection, operator);
    }
    
    /// @notice Batch revoke multiple operator approvals
    /// @param revokes Array of collection/operator pairs to revoke
    function batchRevokeOperators(OperatorRevoke[] calldata revokes) external {
        uint256 length = revokes.length;
        if (length == 0) revert EmptyArray();
        
        uint256 gasStart = gasleft();
        
        for (uint256 i = 0; i < length;) {
            _revokeOperator(revokes[i].collection, revokes[i].operator);
            emit OperatorRevoked(msg.sender, revokes[i].collection, revokes[i].operator);
            
            unchecked { ++i; }
        }
        
        emit BatchRevokeComplete(msg.sender, length, gasStart - gasleft());
    }
    
    /// @dev Internal operator revoke using Yul
    function _revokeOperator(address collection, address operator) internal {
        if (collection == address(0)) revert InvalidTokenAddress();
        
        // setApprovalForAll(address,bool) selector: 0xa22cb465
        
        assembly {
            let ptr := mload(0x40)
            
            // Store selector: setApprovalForAll(address,bool)
            mstore(ptr, 0xa22cb46500000000000000000000000000000000000000000000000000000000)
            
            // Store operator address
            mstore(add(ptr, 4), operator)
            
            // Store approved = false (0)
            mstore(add(ptr, 36), 0)
            
            let success := call(gas(), collection, 0, ptr, 68, ptr, 32)
            
            if iszero(success) {
                revert(0, 0)
            }
        }
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                         UNIVERSAL BATCH
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Universal batch revoke for all token types in one transaction
    /// @param erc20Revokes Array of ERC20 approvals to revoke
    /// @param erc721Revokes Array of ERC721 token approvals to revoke  
    /// @param operatorRevokes Array of operator approvals to revoke
    function batchRevokeAll(
        ERC20Revoke[] calldata erc20Revokes,
        ERC721Revoke[] calldata erc721Revokes,
        OperatorRevoke[] calldata operatorRevokes
    ) external {
        uint256 gasStart = gasleft();
        uint256 totalRevoked = 0;
        
        // Process ERC20 revokes
        for (uint256 i = 0; i < erc20Revokes.length;) {
            _revokeERC20(erc20Revokes[i].token, erc20Revokes[i].spender);
            emit ApprovalRevoked(msg.sender, erc20Revokes[i].token, erc20Revokes[i].spender);
            unchecked { ++i; ++totalRevoked; }
        }
        
        // Process ERC721 revokes
        for (uint256 i = 0; i < erc721Revokes.length;) {
            _revokeERC721Approval(erc721Revokes[i].collection, erc721Revokes[i].tokenId);
            emit NFTApprovalRevoked(msg.sender, erc721Revokes[i].collection, erc721Revokes[i].tokenId);
            unchecked { ++i; ++totalRevoked; }
        }
        
        // Process operator revokes
        for (uint256 i = 0; i < operatorRevokes.length;) {
            _revokeOperator(operatorRevokes[i].collection, operatorRevokes[i].operator);
            emit OperatorRevoked(msg.sender, operatorRevokes[i].collection, operatorRevokes[i].operator);
            unchecked { ++i; ++totalRevoked; }
        }
        
        emit BatchRevokeComplete(msg.sender, totalRevoked, gasStart - gasleft());
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //                         VIEW FUNCTIONS
    // ═══════════════════════════════════════════════════════════════════════
    
    /// @notice Get the current allowance for an ERC20 token
    /// @param token The ERC20 token address
    /// @param owner The token owner
    /// @param spender The spender address
    /// @return The current allowance
    function getAllowance(
        address token,
        address owner,
        address spender
    ) external view returns (uint256) {
        // allowance(address,address) selector: 0xdd62ed3e
        uint256 allowance;

        assembly {
            // Allocate memory
            let ptr := mload(0x40)

            // Store selector
            mstore(ptr, 0xdd62ed3e00000000000000000000000000000000000000000000000000000000)
            mstore(add(ptr, 4), owner)
            mstore(add(ptr, 36), spender)

            // Static call
            let success := staticcall(gas(), token, ptr, 68, ptr, 32)

            if success {
                allowance := mload(ptr)
            }
        }

        return allowance;
    }
    
    /// @notice Check if an operator is approved
    /// @param collection The collection address
    /// @param owner The token owner
    /// @param operator The operator address
    /// @return Whether the operator is approved
    function isOperatorApproved(
        address collection,
        address owner,
        address operator
    ) external view returns (bool) {
        // isApprovedForAll(address,address) selector: 0xe985e9c5
        
        bool approved;
        
        assembly {
            let ptr := mload(0x40)
            
            mstore(ptr, 0xe985e9c500000000000000000000000000000000000000000000000000000000)
            mstore(add(ptr, 4), owner)
            mstore(add(ptr, 36), operator)
            
            let success := staticcall(gas(), collection, ptr, 68, ptr, 32)
            
            if success {
                approved := mload(ptr)
            }
        }
        
        return approved;
    }
}
