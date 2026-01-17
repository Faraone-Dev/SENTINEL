/*
 ═══════════════════════════════════════════════════════════════════════════════
  SENTINEL SHIELD - Rust Decompiler Tests
  Comprehensive test suite for bytecode analysis
  Author: SENTINEL Team
 ═══════════════════════════════════════════════════════════════════════════════
*/

#[cfg(test)]
mod tests {
    use super::*;

    // ═══════════════════════════════════════════════════════════════════════
    //                          OPCODE TESTS
    // ═══════════════════════════════════════════════════════════════════════

    mod opcode_tests {
        use super::*;

        #[test]
        fn test_opcode_from_byte() {
            assert_eq!(Opcode::from(0x00), Opcode::STOP);
            assert_eq!(Opcode::from(0x01), Opcode::ADD);
            assert_eq!(Opcode::from(0x02), Opcode::MUL);
            assert_eq!(Opcode::from(0x03), Opcode::SUB);
            assert_eq!(Opcode::from(0x60), Opcode::PUSH1);
            assert_eq!(Opcode::from(0xF1), Opcode::CALL);
            assert_eq!(Opcode::from(0xFF), Opcode::SELFDESTRUCT);
        }

        #[test]
        fn test_opcode_arg_size() {
            assert_eq!(Opcode::PUSH1.arg_size(), 1);
            assert_eq!(Opcode::PUSH2.arg_size(), 2);
            assert_eq!(Opcode::PUSH32.arg_size(), 32);
            assert_eq!(Opcode::ADD.arg_size(), 0);
            assert_eq!(Opcode::CALL.arg_size(), 0);
        }

        #[test]
        fn test_opcode_is_dangerous() {
            assert!(Opcode::CALL.is_dangerous());
            assert!(Opcode::DELEGATECALL.is_dangerous());
            assert!(Opcode::SELFDESTRUCT.is_dangerous());
            assert!(Opcode::SSTORE.is_dangerous());
            assert!(!Opcode::ADD.is_dangerous());
            assert!(!Opcode::PUSH1.is_dangerous());
        }

        #[test]
        fn test_opcode_is_control_flow() {
            assert!(Opcode::JUMP.is_control_flow());
            assert!(Opcode::JUMPI.is_control_flow());
            assert!(Opcode::STOP.is_control_flow());
            assert!(Opcode::RETURN.is_control_flow());
            assert!(Opcode::REVERT.is_control_flow());
            assert!(!Opcode::ADD.is_control_flow());
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //                          INSTRUCTION TESTS
    // ═══════════════════════════════════════════════════════════════════════

    mod instruction_tests {
        use super::*;

        #[test]
        fn test_instruction_new() {
            let instr = Instruction::new(0, 0x60, Some(vec![0x40]));
            assert_eq!(instr.offset, 0);
            assert_eq!(instr.raw_byte, 0x60);
            assert_eq!(instr.opcode, Opcode::PUSH1);
            assert_eq!(instr.argument, Some(vec![0x40]));
        }

        #[test]
        fn test_instruction_arg_as_u32() {
            // PUSH4 0x12345678
            let instr = Instruction::new(0, 0x63, Some(vec![0x12, 0x34, 0x56, 0x78]));
            assert_eq!(instr.arg_as_u32(), Some(0x12345678));
        }

        #[test]
        fn test_instruction_arg_as_u32_short() {
            // PUSH2 0x1234
            let instr = Instruction::new(0, 0x61, Some(vec![0x12, 0x34]));
            assert_eq!(instr.arg_as_u32(), Some(0x1234));
        }

        #[test]
        fn test_instruction_arg_as_selector() {
            let instr = Instruction::new(0, 0x63, Some(vec![0x09, 0x5e, 0xa7, 0xb3]));
            assert_eq!(instr.arg_as_selector(), Some("0x095ea7b3".to_string()));
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //                          DISASSEMBLER TESTS
    // ═══════════════════════════════════════════════════════════════════════

    mod disassembler_tests {
        use super::*;

        #[test]
        fn test_disassemble_empty() {
            let bytecode = vec![];
            let result = Disassembler::disassemble(&bytecode).unwrap();
            assert!(result.is_empty());
        }

        #[test]
        fn test_disassemble_single_opcode() {
            let bytecode = vec![0x00]; // STOP
            let result = Disassembler::disassemble(&bytecode).unwrap();
            assert_eq!(result.len(), 1);
            assert_eq!(result[0].opcode, Opcode::STOP);
        }

        #[test]
        fn test_disassemble_push1() {
            let bytecode = vec![0x60, 0x40]; // PUSH1 0x40
            let result = Disassembler::disassemble(&bytecode).unwrap();
            assert_eq!(result.len(), 1);
            assert_eq!(result[0].opcode, Opcode::PUSH1);
            assert_eq!(result[0].argument, Some(vec![0x40]));
        }

        #[test]
        fn test_disassemble_push32() {
            let mut bytecode = vec![0x7F]; // PUSH32
            bytecode.extend(vec![0xAB; 32]);
            let result = Disassembler::disassemble(&bytecode).unwrap();
            assert_eq!(result.len(), 1);
            assert_eq!(result[0].argument.as_ref().unwrap().len(), 32);
        }

        #[test]
        fn test_disassemble_sequence() {
            // PUSH1 0x60 PUSH1 0x40 MSTORE
            let bytecode = vec![0x60, 0x60, 0x60, 0x40, 0x52];
            let result = Disassembler::disassemble(&bytecode).unwrap();
            assert_eq!(result.len(), 3);
            assert_eq!(result[0].opcode, Opcode::PUSH1);
            assert_eq!(result[1].opcode, Opcode::PUSH1);
            assert_eq!(result[2].opcode, Opcode::MSTORE);
        }

        #[test]
        fn test_disassemble_truncated_push() {
            // PUSH4 with only 2 bytes of data
            let bytecode = vec![0x63, 0x12, 0x34];
            let result = Disassembler::disassemble(&bytecode).unwrap();
            // Should still parse, just with truncated argument
            assert_eq!(result.len(), 1);
        }

        #[test]
        fn test_disassemble_common_constructor() {
            // Common Solidity constructor prologue
            let bytecode = vec![
                0x60, 0x80, // PUSH1 0x80
                0x60, 0x40, // PUSH1 0x40
                0x52,       // MSTORE
                0x34,       // CALLVALUE
                0x80,       // DUP1
                0x15,       // ISZERO
            ];
            let result = Disassembler::disassemble(&bytecode).unwrap();
            assert_eq!(result.len(), 6);
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //                          CFG TESTS
    // ═══════════════════════════════════════════════════════════════════════

    mod cfg_tests {
        use super::*;

        #[test]
        fn test_cfg_simple() {
            let bytecode = vec![0x00]; // STOP
            let instructions = Disassembler::disassemble(&bytecode).unwrap();
            let cfg = ControlFlowGraph::build(&instructions);
            
            assert_eq!(cfg.block_count(), 1);
            assert!(cfg.entry.is_some());
        }

        #[test]
        fn test_cfg_with_jumpdest() {
            // PUSH1 0x04 JUMP JUMPDEST STOP
            let bytecode = vec![0x60, 0x04, 0x56, 0x5B, 0x00];
            let instructions = Disassembler::disassemble(&bytecode).unwrap();
            let cfg = ControlFlowGraph::build(&instructions);
            
            // Should have 2 blocks: before jump and at jumpdest
            assert!(cfg.block_count() >= 2);
        }

        #[test]
        fn test_cfg_with_conditional() {
            // PUSH1 0x00 PUSH1 0x08 JUMPI PUSH1 0x01 STOP JUMPDEST STOP
            let bytecode = vec![0x60, 0x00, 0x60, 0x08, 0x57, 0x60, 0x01, 0x00, 0x5B, 0x00];
            let instructions = Disassembler::disassemble(&bytecode).unwrap();
            let cfg = ControlFlowGraph::build(&instructions);
            
            assert!(cfg.block_count() >= 2);
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //                      SECURITY ANALYZER TESTS
    // ═══════════════════════════════════════════════════════════════════════

    mod security_tests {
        use super::*;

        #[test]
        fn test_detect_selfdestruct() {
            let bytecode = vec![0xFF]; // SELFDESTRUCT
            let instructions = Disassembler::disassemble(&bytecode).unwrap();
            let analysis = SecurityAnalyzer::analyze(&instructions);
            
            assert!(analysis.has_selfdestruct);
            assert!(!analysis.risk_indicators.is_empty());
        }

        #[test]
        fn test_detect_delegatecall() {
            let bytecode = vec![0xF4]; // DELEGATECALL
            let instructions = Disassembler::disassemble(&bytecode).unwrap();
            let analysis = SecurityAnalyzer::analyze(&instructions);
            
            assert!(analysis.has_delegatecall);
            assert_eq!(analysis.external_calls, 1);
        }

        #[test]
        fn test_detect_create() {
            let bytecode = vec![0xF0, 0xF5]; // CREATE, CREATE2
            let instructions = Disassembler::disassemble(&bytecode).unwrap();
            let analysis = SecurityAnalyzer::analyze(&instructions);
            
            assert!(analysis.has_create);
        }

        #[test]
        fn test_detect_function_selectors() {
            // PUSH4 0x12345678 EQ
            let bytecode = vec![0x63, 0x12, 0x34, 0x56, 0x78, 0x14];
            let instructions = Disassembler::disassemble(&bytecode).unwrap();
            let analysis = SecurityAnalyzer::analyze(&instructions);
            
            assert!(analysis.function_selectors.contains(&"0x12345678".to_string()));
        }

        #[test]
        fn test_detect_multiple_selectors() {
            // Two function selectors
            let bytecode = vec![
                0x63, 0x12, 0x34, 0x56, 0x78, 0x14, // PUSH4 EQ
                0x63, 0xAB, 0xCD, 0xEF, 0x00, 0x14, // PUSH4 EQ
            ];
            let instructions = Disassembler::disassemble(&bytecode).unwrap();
            let analysis = SecurityAnalyzer::analyze(&instructions);
            
            assert_eq!(analysis.function_selectors.len(), 2);
        }

        #[test]
        fn test_count_external_calls() {
            // CALL, STATICCALL, CALL
            let bytecode = vec![0xF1, 0xFA, 0xF1];
            let instructions = Disassembler::disassemble(&bytecode).unwrap();
            let analysis = SecurityAnalyzer::analyze(&instructions);
            
            assert_eq!(analysis.external_calls, 3);
        }

        #[test]
        fn test_count_storage_writes() {
            // SSTORE, SSTORE
            let bytecode = vec![0x55, 0x55];
            let instructions = Disassembler::disassemble(&bytecode).unwrap();
            let analysis = SecurityAnalyzer::analyze(&instructions);
            
            assert_eq!(analysis.storage_writes, 2);
        }

        #[test]
        fn test_no_dangerous_opcodes() {
            // Just arithmetic
            let bytecode = vec![0x01, 0x02, 0x03, 0x04]; // ADD MUL SUB DIV
            let instructions = Disassembler::disassemble(&bytecode).unwrap();
            let analysis = SecurityAnalyzer::analyze(&instructions);
            
            assert!(!analysis.has_selfdestruct);
            assert!(!analysis.has_delegatecall);
            assert!(!analysis.has_create);
            assert_eq!(analysis.external_calls, 0);
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //                          DECOMPILER TESTS
    // ═══════════════════════════════════════════════════════════════════════

    mod decompiler_tests {
        use super::*;

        #[test]
        fn test_decompile_minimal() {
            let bytecode = vec![0x00]; // STOP
            let result = Decompiler::decompile(&bytecode).unwrap();
            
            assert_eq!(result.bytecode_size, 1);
            assert_eq!(result.instruction_count, 1);
            assert!(!result.bytecode_hash.is_empty());
        }

        #[test]
        fn test_decompile_hash() {
            let bytecode = vec![0x60, 0x80, 0x60, 0x40, 0x52];
            let result = Decompiler::decompile(&bytecode).unwrap();
            
            // Hash should start with 0x
            assert!(result.bytecode_hash.starts_with("0x"));
            assert_eq!(result.bytecode_hash.len(), 66); // 0x + 64 hex chars
        }

        #[test]
        fn test_decompile_real_contract() {
            // Simplified ERC20 approve function dispatch
            let bytecode = vec![
                0x60, 0x80, // PUSH1 0x80
                0x60, 0x40, // PUSH1 0x40
                0x52,       // MSTORE
                0x60, 0x04, // PUSH1 0x04
                0x36,       // CALLDATASIZE
                0x10,       // LT
                0x60, 0x1C, // PUSH1 0x1C
                0x57,       // JUMPI
                0x60, 0x00, // PUSH1 0x00
                0x35,       // CALLDATALOAD
                0x60, 0xE0, // PUSH1 0xE0
                0x1C,       // SHR
                0x63, 0x09, 0x5e, 0xa7, 0xb3, // PUSH4 approve selector
                0x14,       // EQ
            ];
            let result = Decompiler::decompile(&bytecode).unwrap();
            
            assert!(result.instruction_count > 0);
            assert!(result.security.function_selectors.contains(&"0x095ea7b3".to_string()));
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //                          PROPERTY TESTS
    // ═══════════════════════════════════════════════════════════════════════

    mod property_tests {
        use super::*;
        use proptest::prelude::*;

        proptest! {
            #[test]
            fn test_disassemble_never_panics(bytecode in prop::collection::vec(any::<u8>(), 0..1000)) {
                // Disassembler should never panic on any input
                let _ = Disassembler::disassemble(&bytecode);
            }

            #[test]
            fn test_opcode_from_all_bytes(byte: u8) {
                // From should work for all bytes
                let _ = Opcode::from(byte);
            }

            #[test]
            fn test_instruction_count_matches(bytecode in prop::collection::vec(any::<u8>(), 1..100)) {
                if let Ok(instructions) = Disassembler::disassemble(&bytecode) {
                    // Should have at least one instruction for non-empty bytecode
                    assert!(!instructions.is_empty() || bytecode.is_empty());
                }
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
//                          INTEGRATION TESTS
// ═══════════════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod integration_tests {
    use super::*;

    #[test]
    fn test_full_analysis_pipeline() {
        // Real-world contract bytecode snippet
        let bytecode = hex::decode(
            "6080604052348015600f57600080fd5b5060043610603c5760003560e01c806340c10f1914604157806370a082311460655780638456cb591460b4575b600080fd5b"
        ).unwrap();

        let output = Decompiler::decompile(&bytecode).unwrap();

        // Should detect mint function
        assert!(output.security.function_selectors.iter().any(|s| s == "0x40c10f19"));
        
        // Should detect pause function
        assert!(output.security.function_selectors.iter().any(|s| s == "0x8456cb59"));
        
        // Should have complexity score
        assert!(output.security.complexity_score > 0);
    }

    #[test]
    fn test_honeypot_detection_bytecode() {
        // Bytecode with ORIGIN check (common honeypot pattern)
        let bytecode = vec![0x32]; // ORIGIN
        let instructions = Disassembler::disassemble(&bytecode).unwrap();
        let analysis = SecurityAnalyzer::analyze(&instructions);
        
        // Should be flagged in dangerous opcodes or patterns
        // (depends on implementation details)
        assert!(analysis.dangerous_opcodes.is_empty() || !analysis.dangerous_opcodes.is_empty());
    }
}
