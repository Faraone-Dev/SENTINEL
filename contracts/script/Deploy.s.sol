// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {SentinelRegistry} from "../src/SentinelRegistry.sol";

/**
 * @title DeployScript
 * @author SENTINEL Team
 * @notice Deployment script for SENTINEL SHIELD contracts
 */
contract DeployScript is Script {
    
    function setUp() public {}

    function run() public {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);
        
        console.log("Deploying SENTINEL SHIELD contracts...");
        console.log("Deployer:", deployer);
        console.log("Chain ID:", block.chainid);
        console.log("Balance:", deployer.balance);
        
        vm.startBroadcast(deployerPrivateKey);
        
        // Deploy SentinelRegistry
        SentinelRegistry registry = new SentinelRegistry();
        console.log("SentinelRegistry deployed at:", address(registry));
        
        // Deploy pure Yul contract (BatchRevokeYul)
        // Note: Yul contracts need to be compiled separately
        // bytes memory yulBytecode = vm.getCode("BatchRevokeYul.yul");
        // address batchRevoke;
        // assembly {
        //     batchRevoke := create(0, add(yulBytecode, 0x20), mload(yulBytecode))
        // }
        // console.log("BatchRevokeYul deployed at:", batchRevoke);
        
        vm.stopBroadcast();
        
        // Log deployment summary
        console.log("");
        console.log("═══════════════════════════════════════════════════════════════");
        console.log("                    DEPLOYMENT SUMMARY");
        console.log("═══════════════════════════════════════════════════════════════");
        console.log("Network:", _getNetworkName(block.chainid));
        console.log("SentinelRegistry:", address(registry));
        console.log("═══════════════════════════════════════════════════════════════");
    }
    
    function _getNetworkName(uint256 chainId) internal pure returns (string memory) {
        if (chainId == 1) return "Ethereum Mainnet";
        if (chainId == 11155111) return "Sepolia Testnet";
        if (chainId == 137) return "Polygon";
        if (chainId == 42161) return "Arbitrum One";
        if (chainId == 10) return "Optimism";
        if (chainId == 8453) return "Base";
        if (chainId == 56) return "BNB Smart Chain";
        if (chainId == 43114) return "Avalanche C-Chain";
        if (chainId == 250) return "Fantom";
        if (chainId == 324) return "zkSync Era";
        return "Unknown";
    }
}
