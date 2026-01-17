/*
 ═══════════════════════════════════════════════════════════════════════════════
  ██████╗ ███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗
 ██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║
 ███████╗ █████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║
 ╚════██║ ██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║
 ███████║ ███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
 ╚══════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝

  SENTINEL SHIELD - EVM Bytecode Decompiler (Rust)
  
  High-performance bytecode analysis engine that extracts:
  - Function selectors
  - Control flow graphs
  - Dangerous opcodes
  - Reentrancy patterns
  - Hidden fee logic
  
  
 ═══════════════════════════════════════════════════════════════════════════════
*/

use std::collections::{HashMap, HashSet};
use clap::Parser;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use petgraph::graph::{DiGraph, NodeIndex};

mod server;

// ═══════════════════════════════════════════════════════════════════════════════
//                              CLI ARGUMENTS
// ═══════════════════════════════════════════════════════════════════════════════

#[derive(Parser, Debug)]
#[command(name = "sentinel-decompile")]
#[command(author = "SENTINEL Team")]
#[command(version = "1.0.0")]
#[command(about = "EVM bytecode decompiler for security analysis")]
struct Args {
    /// Bytecode hex string (with or without 0x prefix)
    #[arg(short, long)]
    bytecode: Option<String>,
    
    /// Contract address to fetch bytecode from
    #[arg(short, long)]
    address: Option<String>,
    
    /// Chain to query (ethereum, bsc, polygon, etc.)
    #[arg(short, long, default_value = "ethereum")]
    chain: String,
    
    /// Output format: json, text, or graph
    #[arg(short, long, default_value = "json")]
    output: String,
    
    /// Enable verbose logging
    #[arg(short, long)]
    verbose: bool,
    
    /// Run as HTTP server
    #[arg(long)]
    server: bool,
    
    /// Port for HTTP server (default: 3000)
    #[arg(short, long, default_value = "3000")]
    port: u16,
}

// ═══════════════════════════════════════════════════════════════════════════════
//                              ERROR TYPES
// ═══════════════════════════════════════════════════════════════════════════════

#[derive(Error, Debug)]
pub enum DecompilerError {
    #[error("Invalid bytecode: {0}")]
    InvalidBytecode(String),
    
    #[error("Invalid opcode at position {position}: 0x{opcode:02x}")]
    InvalidOpcode { position: usize, opcode: u8 },
    
    #[error("RPC error: {0}")]
    RpcError(String),
    
    #[error("Parse error: {0}")]
    ParseError(String),
}

type Result<T> = std::result::Result<T, DecompilerError>;

// ═══════════════════════════════════════════════════════════════════════════════
//                              EVM OPCODES
// ═══════════════════════════════════════════════════════════════════════════════

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(u8)]
pub enum Opcode {
    // Stop & Arithmetic
    STOP = 0x00,
    ADD = 0x01,
    MUL = 0x02,
    SUB = 0x03,
    DIV = 0x04,
    SDIV = 0x05,
    MOD = 0x06,
    SMOD = 0x07,
    ADDMOD = 0x08,
    MULMOD = 0x09,
    EXP = 0x0A,
    SIGNEXTEND = 0x0B,
    
    // Comparison & Bitwise
    LT = 0x10,
    GT = 0x11,
    SLT = 0x12,
    SGT = 0x13,
    EQ = 0x14,
    ISZERO = 0x15,
    AND = 0x16,
    OR = 0x17,
    XOR = 0x18,
    NOT = 0x19,
    BYTE = 0x1A,
    SHL = 0x1B,
    SHR = 0x1C,
    SAR = 0x1D,
    
    // Keccak256
    SHA3 = 0x20,
    
    // Environment
    ADDRESS = 0x30,
    BALANCE = 0x31,
    ORIGIN = 0x32,
    CALLER = 0x33,
    CALLVALUE = 0x34,
    CALLDATALOAD = 0x35,
    CALLDATASIZE = 0x36,
    CALLDATACOPY = 0x37,
    CODESIZE = 0x38,
    CODECOPY = 0x39,
    GASPRICE = 0x3A,
    EXTCODESIZE = 0x3B,
    EXTCODECOPY = 0x3C,
    RETURNDATASIZE = 0x3D,
    RETURNDATACOPY = 0x3E,
    EXTCODEHASH = 0x3F,
    
    // Block info
    BLOCKHASH = 0x40,
    COINBASE = 0x41,
    TIMESTAMP = 0x42,
    NUMBER = 0x43,
    DIFFICULTY = 0x44,
    GASLIMIT = 0x45,
    CHAINID = 0x46,
    SELFBALANCE = 0x47,
    BASEFEE = 0x48,
    
    // Stack, Memory, Storage
    POP = 0x50,
    MLOAD = 0x51,
    MSTORE = 0x52,
    MSTORE8 = 0x53,
    SLOAD = 0x54,
    SSTORE = 0x55,
    JUMP = 0x56,
    JUMPI = 0x57,
    PC = 0x58,
    MSIZE = 0x59,
    GAS = 0x5A,
    JUMPDEST = 0x5B,
    
    // Push operations (PUSH1 to PUSH32)
    PUSH1 = 0x60,
    PUSH2 = 0x61,
    PUSH3 = 0x62,
    PUSH4 = 0x63,
    PUSH32 = 0x7F,
    
    // Dup operations
    DUP1 = 0x80,
    DUP16 = 0x8F,
    
    // Swap operations
    SWAP1 = 0x90,
    SWAP16 = 0x9F,
    
    // Log operations
    LOG0 = 0xA0,
    LOG4 = 0xA4,
    
    // System operations
    CREATE = 0xF0,
    CALL = 0xF1,
    CALLCODE = 0xF2,
    RETURN = 0xF3,
    DELEGATECALL = 0xF4,
    CREATE2 = 0xF5,
    STATICCALL = 0xFA,
    REVERT = 0xFD,
    INVALID = 0xFE,
    SELFDESTRUCT = 0xFF,
    
    UNKNOWN = 0xFE,
}

impl From<u8> for Opcode {
    fn from(byte: u8) -> Self {
        match byte {
            0x00 => Opcode::STOP,
            0x01 => Opcode::ADD,
            0x02 => Opcode::MUL,
            0x03 => Opcode::SUB,
            0x04 => Opcode::DIV,
            0x20 => Opcode::SHA3,
            0x31 => Opcode::BALANCE,
            0x32 => Opcode::ORIGIN,
            0x33 => Opcode::CALLER,
            0x34 => Opcode::CALLVALUE,
            0x35 => Opcode::CALLDATALOAD,
            0x54 => Opcode::SLOAD,
            0x55 => Opcode::SSTORE,
            0x56 => Opcode::JUMP,
            0x57 => Opcode::JUMPI,
            0x5B => Opcode::JUMPDEST,
            // PUSH operations - return PUSH1 and handle arg size separately
            0x60..=0x7F => Opcode::PUSH1,  // Safe: all PUSHn map to PUSH1
            // DUP operations
            0x80..=0x8F => Opcode::DUP1,   // Safe: all DUPn map to DUP1
            // SWAP operations 
            0x90..=0x9F => Opcode::SWAP1,  // Safe: all SWAPn map to SWAP1
            0xF0 => Opcode::CREATE,
            0xF1 => Opcode::CALL,
            0xF2 => Opcode::CALLCODE,
            0xF3 => Opcode::RETURN,
            0xF4 => Opcode::DELEGATECALL,
            0xF5 => Opcode::CREATE2,
            0xFA => Opcode::STATICCALL,
            0xFD => Opcode::REVERT,
            0xFF => Opcode::SELFDESTRUCT,
            _ => Opcode::UNKNOWN,
        }
    }
}

impl Opcode {
    /// Returns how many bytes this opcode's argument takes
    pub fn arg_size(&self) -> usize {
        let byte = *self as u8;
        if byte >= 0x60 && byte <= 0x7F {
            (byte - 0x5F) as usize
        } else {
            0
        }
    }
    
    /// Check if this opcode is dangerous for security
    pub fn is_dangerous(&self) -> bool {
        matches!(self, 
            Opcode::CALL | 
            Opcode::CALLCODE | 
            Opcode::DELEGATECALL |
            Opcode::SELFDESTRUCT |
            Opcode::CREATE |
            Opcode::CREATE2 |
            Opcode::SSTORE
        )
    }
    
    /// Check if this is a control flow opcode
    pub fn is_control_flow(&self) -> bool {
        matches!(self,
            Opcode::JUMP |
            Opcode::JUMPI |
            Opcode::STOP |
            Opcode::RETURN |
            Opcode::REVERT |
            Opcode::SELFDESTRUCT
        )
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
//                              INSTRUCTION
// ═══════════════════════════════════════════════════════════════════════════════

#[derive(Debug, Clone)]
pub struct Instruction {
    pub offset: usize,
    pub opcode: Opcode,
    pub raw_byte: u8,
    pub argument: Option<Vec<u8>>,
}

impl Instruction {
    pub fn new(offset: usize, raw_byte: u8, argument: Option<Vec<u8>>) -> Self {
        Self {
            offset,
            opcode: Opcode::from(raw_byte),
            raw_byte,
            argument,
        }
    }
    
    /// Get the PUSH argument as u32 (for function selectors)
    pub fn arg_as_u32(&self) -> Option<u32> {
        self.argument.as_ref().and_then(|bytes| {
            if bytes.len() <= 4 {
                let mut arr = [0u8; 4];
                let start = 4 - bytes.len();
                arr[start..].copy_from_slice(bytes);
                Some(u32::from_be_bytes(arr))
            } else {
                None
            }
        })
    }
    
    /// Get selector hex string
    pub fn arg_as_selector(&self) -> Option<String> {
        self.arg_as_u32().map(|v| format!("0x{:08x}", v))
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
//                          DISASSEMBLER
// ═══════════════════════════════════════════════════════════════════════════════

pub struct Disassembler;

impl Disassembler {
    /// Parse bytecode into instructions
    pub fn disassemble(bytecode: &[u8]) -> Result<Vec<Instruction>> {
        let mut instructions = Vec::new();
        let mut i = 0;
        
        while i < bytecode.len() {
            let raw_byte = bytecode[i];
            let opcode = Opcode::from(raw_byte);
            let arg_size = opcode.arg_size();
            
            let argument = if arg_size > 0 && i + arg_size < bytecode.len() {
                Some(bytecode[i + 1..i + 1 + arg_size].to_vec())
            } else if arg_size > 0 {
                // Truncated PUSH - still valid, just pad with zeros
                let remaining = bytecode.len() - i - 1;
                if remaining > 0 {
                    Some(bytecode[i + 1..].to_vec())
                } else {
                    None
                }
            } else {
                None
            };
            
            instructions.push(Instruction::new(i, raw_byte, argument));
            i += 1 + arg_size;
        }
        
        Ok(instructions)
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
//                          CONTROL FLOW GRAPH
// ═══════════════════════════════════════════════════════════════════════════════

#[derive(Debug, Clone)]
pub struct BasicBlock {
    pub start_offset: usize,
    pub end_offset: usize,
    pub instructions: Vec<Instruction>,
    pub is_entry: bool,
    pub is_revert: bool,
    pub is_return: bool,
}

pub struct ControlFlowGraph {
    pub graph: DiGraph<BasicBlock, ()>,
    pub entry: Option<NodeIndex>,
    pub blocks: HashMap<usize, NodeIndex>,
}

impl ControlFlowGraph {
    pub fn build(instructions: &[Instruction]) -> Self {
        let mut cfg = ControlFlowGraph {
            graph: DiGraph::new(),
            entry: None,
            blocks: HashMap::new(),
        };
        
        // Find all basic block leaders (JUMPDEST, after JUMP/JUMPI/STOP/etc)
        let mut leaders: HashSet<usize> = HashSet::new();
        leaders.insert(0); // First instruction is always a leader
        
        for (idx, instr) in instructions.iter().enumerate() {
            match instr.opcode {
                Opcode::JUMPDEST => {
                    leaders.insert(idx);
                }
                Opcode::JUMP | Opcode::JUMPI => {
                    if idx + 1 < instructions.len() {
                        leaders.insert(idx + 1);
                    }
                }
                Opcode::STOP | Opcode::RETURN | Opcode::REVERT | Opcode::SELFDESTRUCT => {
                    if idx + 1 < instructions.len() {
                        leaders.insert(idx + 1);
                    }
                }
                _ => {}
            }
        }
        
        // Build basic blocks
        let mut sorted_leaders: Vec<_> = leaders.into_iter().collect();
        sorted_leaders.sort();
        
        for (i, &start) in sorted_leaders.iter().enumerate() {
            let end = if i + 1 < sorted_leaders.len() {
                sorted_leaders[i + 1]
            } else {
                instructions.len()
            };
            
            let block_instructions: Vec<_> = instructions[start..end].to_vec();
            let last_opcode = block_instructions.last().map(|i| i.opcode);
            
            let block = BasicBlock {
                start_offset: instructions[start].offset,
                end_offset: block_instructions.last().map(|i| i.offset).unwrap_or(0),
                instructions: block_instructions,
                is_entry: start == 0,
                is_revert: matches!(last_opcode, Some(Opcode::REVERT)),
                is_return: matches!(last_opcode, Some(Opcode::RETURN) | Some(Opcode::STOP)),
            };
            
            let node = cfg.graph.add_node(block);
            cfg.blocks.insert(instructions[start].offset, node);
            
            if start == 0 {
                cfg.entry = Some(node);
            }
        }
        
        cfg
    }
    
    pub fn block_count(&self) -> usize {
        self.graph.node_count()
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
//                          SECURITY ANALYZER
// ═══════════════════════════════════════════════════════════════════════════════

#[derive(Debug, Serialize, Deserialize)]
pub struct SecurityAnalysis {
    pub function_selectors: Vec<String>,
    pub dangerous_opcodes: Vec<DangerousOpcode>,
    pub external_calls: usize,
    pub storage_writes: usize,
    pub has_selfdestruct: bool,
    pub has_delegatecall: bool,
    pub has_create: bool,
    pub complexity_score: u32,
    pub risk_indicators: Vec<RiskIndicator>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DangerousOpcode {
    pub offset: usize,
    pub opcode: String,
    pub risk: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct RiskIndicator {
    pub name: String,
    pub severity: String, // "critical", "high", "medium", "low"
    pub description: String,
}

pub struct SecurityAnalyzer;

impl SecurityAnalyzer {
    pub fn analyze(instructions: &[Instruction]) -> SecurityAnalysis {
        let mut selectors = Vec::new();
        let mut dangerous = Vec::new();
        let mut external_calls = 0;
        let mut storage_writes = 0;
        let mut has_selfdestruct = false;
        let mut has_delegatecall = false;
        let mut has_create = false;
        let mut risks = Vec::new();
        
        // Look for function selectors (PUSH4 followed by EQ)
        for window in instructions.windows(2) {
            if let (instr, next) = (&window[0], &window[1]) {
                if instr.raw_byte == 0x63 { // PUSH4
                    if next.raw_byte == 0x14 { // EQ
                        if let Some(selector) = instr.arg_as_selector() {
                            selectors.push(selector);
                        }
                    }
                }
            }
        }
        
        // Analyze each instruction
        for instr in instructions {
            match instr.opcode {
                Opcode::CALL | Opcode::CALLCODE | Opcode::STATICCALL => {
                    external_calls += 1;
                    dangerous.push(DangerousOpcode {
                        offset: instr.offset,
                        opcode: format!("{:?}", instr.opcode),
                        risk: "External call - potential reentrancy".to_string(),
                    });
                }
                Opcode::DELEGATECALL => {
                    has_delegatecall = true;
                    external_calls += 1;
                    dangerous.push(DangerousOpcode {
                        offset: instr.offset,
                        opcode: "DELEGATECALL".to_string(),
                        risk: "Delegatecall - storage manipulation risk".to_string(),
                    });
                }
                Opcode::SSTORE => {
                    storage_writes += 1;
                }
                Opcode::SELFDESTRUCT => {
                    has_selfdestruct = true;
                    dangerous.push(DangerousOpcode {
                        offset: instr.offset,
                        opcode: "SELFDESTRUCT".to_string(),
                        risk: "Contract can be destroyed".to_string(),
                    });
                    risks.push(RiskIndicator {
                        name: "Self-destruct capability".to_string(),
                        severity: "critical".to_string(),
                        description: "Contract can be destroyed, all funds sent to owner".to_string(),
                    });
                }
                Opcode::CREATE | Opcode::CREATE2 => {
                    has_create = true;
                    dangerous.push(DangerousOpcode {
                        offset: instr.offset,
                        opcode: format!("{:?}", instr.opcode),
                        risk: "Creates new contract".to_string(),
                    });
                }
                _ => {}
            }
        }
        
        // Calculate complexity
        let cfg = ControlFlowGraph::build(instructions);
        let complexity = (cfg.block_count() as u32 * 10) 
            + (external_calls as u32 * 20)
            + (storage_writes as u32 * 5);
        
        // Add risk indicators based on patterns
        if has_delegatecall {
            risks.push(RiskIndicator {
                name: "Delegatecall usage".to_string(),
                severity: "high".to_string(),
                description: "Contract uses delegatecall - verify upgrade mechanism".to_string(),
            });
        }
        
        if external_calls > 5 {
            risks.push(RiskIndicator {
                name: "Multiple external calls".to_string(),
                severity: "medium".to_string(),
                description: format!("{} external calls - check for reentrancy", external_calls),
            });
        }
        
        SecurityAnalysis {
            function_selectors: selectors,
            dangerous_opcodes: dangerous,
            external_calls,
            storage_writes,
            has_selfdestruct,
            has_delegatecall,
            has_create,
            complexity_score: complexity,
            risk_indicators: risks,
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
//                          DECOMPILER OUTPUT
// ═══════════════════════════════════════════════════════════════════════════════

#[derive(Debug, Serialize, Deserialize)]
pub struct DecompilerOutput {
    pub bytecode_hash: String,
    pub bytecode_size: usize,
    pub instruction_count: usize,
    pub block_count: usize,
    pub security: SecurityAnalysis,
}

pub struct Decompiler;

impl Decompiler {
    pub fn decompile(bytecode: &[u8]) -> Result<DecompilerOutput> {
        // Hash the bytecode
        use sha3::{Digest, Keccak256};
        let mut hasher = Keccak256::new();
        hasher.update(bytecode);
        let hash = format!("0x{}", hex::encode(hasher.finalize()));
        
        // Disassemble
        let instructions = Disassembler::disassemble(bytecode)?;
        
        // Build CFG
        let cfg = ControlFlowGraph::build(&instructions);
        
        // Security analysis
        let security = SecurityAnalyzer::analyze(&instructions);
        
        Ok(DecompilerOutput {
            bytecode_hash: hash,
            bytecode_size: bytecode.len(),
            instruction_count: instructions.len(),
            block_count: cfg.block_count(),
            security,
        })
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
//                                  MAIN
// ═══════════════════════════════════════════════════════════════════════════════

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args = Args::parse();
    
    // Initialize logging
    if args.verbose {
        tracing_subscriber::fmt()
            .with_env_filter("debug")
            .init();
    }
    
    // Server mode
    if args.server {
        server::run_server(args.port).await?;
        return Ok(());
    }
    
    // CLI mode
    println!(r#"
 ██████╗ ███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗
██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║
███████╗ █████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║
╚════██║ ██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║
███████║ ███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
╚══════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝

            EVM Bytecode Decompiler v1.0.0
            
  Usage:
    CLI:    sentinel-decompile --bytecode 0x...
    Server: sentinel-decompile --server --port 3000
"#);
    
    // Get bytecode
    let bytecode = if let Some(hex_str) = &args.bytecode {
        let clean = hex_str.strip_prefix("0x").unwrap_or(hex_str);
        hex::decode(clean).map_err(|e| DecompilerError::InvalidBytecode(e.to_string()))?
    } else if let Some(_address) = &args.address {
        // TODO: Fetch from RPC
        eprintln!("⚠️  Address fetching not yet implemented");
        return Ok(());
    } else {
        eprintln!("❌ Provide --bytecode or --address, or use --server mode");
        return Ok(());
    };
    
    println!("📊 Analyzing {} bytes of bytecode...\n", bytecode.len());
    
    // Decompile
    let output = Decompiler::decompile(&bytecode)?;
    
    match args.output.as_str() {
        "json" => {
            println!("{}", serde_json::to_string_pretty(&output)?);
        }
        "text" => {
            println!("═══════════════════════════════════════════════════════════════");
            println!("                    DECOMPILATION RESULTS");
            println!("═══════════════════════════════════════════════════════════════\n");
            
            println!("📋 Bytecode Hash: {}", output.bytecode_hash);
            println!("📏 Size: {} bytes", output.bytecode_size);
            println!("🔢 Instructions: {}", output.instruction_count);
            println!("🧱 Basic Blocks: {}", output.block_count);
            println!("📈 Complexity Score: {}", output.security.complexity_score);
            
            println!("\n🎯 Function Selectors:");
            for sel in &output.security.function_selectors {
                println!("   {}", sel);
            }
            
            println!("\n⚠️  Risk Indicators:");
            for risk in &output.security.risk_indicators {
                let icon = match risk.severity.as_str() {
                    "critical" => "🔴",
                    "high" => "🟠",
                    "medium" => "🟡",
                    _ => "🟢",
                };
                println!("   {} [{}] {}: {}", icon, risk.severity, risk.name, risk.description);
            }
            
            if output.security.has_selfdestruct {
                println!("\n🚨 CRITICAL: Contract has SELFDESTRUCT capability!");
            }
        }
        _ => {
            eprintln!("Unknown output format: {}", args.output);
        }
    }
    
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_disassemble_simple() {
        // PUSH1 0x60 PUSH1 0x40 MSTORE
        let bytecode = vec![0x60, 0x60, 0x60, 0x40, 0x52];
        let instructions = Disassembler::disassemble(&bytecode).unwrap();
        
        assert_eq!(instructions.len(), 3);
        assert_eq!(instructions[0].raw_byte, 0x60);
        assert_eq!(instructions[0].argument, Some(vec![0x60]));
    }
    
    #[test]
    fn test_function_selector_detection() {
        // PUSH4 0x12345678 EQ
        let bytecode = vec![0x63, 0x12, 0x34, 0x56, 0x78, 0x14];
        let instructions = Disassembler::disassemble(&bytecode).unwrap();
        let analysis = SecurityAnalyzer::analyze(&instructions);
        
        assert!(analysis.function_selectors.contains(&"0x12345678".to_string()));
    }
    
    #[test]
    fn test_dangerous_opcode_detection() {
        // SELFDESTRUCT
        let bytecode = vec![0xFF];
        let instructions = Disassembler::disassemble(&bytecode).unwrap();
        let analysis = SecurityAnalyzer::analyze(&instructions);
        
        assert!(analysis.has_selfdestruct);
        assert!(!analysis.risk_indicators.is_empty());
    }
}

// Include extended test module
#[cfg(test)]
mod extended_tests;

#[cfg(test)]
use extended_tests as tests;
