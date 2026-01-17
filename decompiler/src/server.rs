/*
 ═══════════════════════════════════════════════════════════════════════════════
  SENTINEL SHIELD - Decompiler HTTP Server
  
  Exposes the decompiler functionality via REST API for integration with
  the Go API server.
 ═══════════════════════════════════════════════════════════════════════════════
*/

use axum::{
    extract::Json,
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
    Router,
};
use serde::{Deserialize, Serialize};
use tower_http::cors::{Any, CorsLayer};
use std::net::SocketAddr;

use crate::{Disassembler, SecurityAnalyzer, ControlFlowGraph};

// ═══════════════════════════════════════════════════════════════════════════════
//                              REQUEST/RESPONSE TYPES
// ═══════════════════════════════════════════════════════════════════════════════

#[derive(Debug, Deserialize)]
pub struct AnalyzeRequest {
    pub bytecode: String,
}

#[derive(Debug, Serialize)]
pub struct AnalyzeResponse {
    pub success: bool,
    pub opcodes: Vec<String>,
    pub functions: Vec<String>,
    pub selectors: Vec<String>,
    pub is_proxy: bool,
    pub has_sstore: bool,
    pub has_call: bool,
    pub has_delegatecall: bool,
    pub has_selfdestruct: bool,
    pub complexity: i32,
    pub warnings: Vec<String>,
    pub risk_indicators: Vec<RiskIndicator>,
    pub instruction_count: usize,
    pub block_count: usize,
}

#[derive(Debug, Serialize)]
pub struct RiskIndicator {
    pub name: String,
    pub severity: String,
    pub description: String,
}

#[derive(Debug, Serialize)]
pub struct HealthResponse {
    pub status: String,
    pub service: String,
    pub version: String,
}

#[derive(Debug, Serialize)]
pub struct ErrorResponse {
    pub error: String,
    pub details: Option<String>,
}

// ═══════════════════════════════════════════════════════════════════════════════
//                              HANDLERS
// ═══════════════════════════════════════════════════════════════════════════════

async fn health_handler() -> impl IntoResponse {
    Json(HealthResponse {
        status: "healthy".to_string(),
        service: "sentinel-decompiler".to_string(),
        version: "1.0.0".to_string(),
    })
}

async fn analyze_handler(Json(payload): Json<AnalyzeRequest>) -> impl IntoResponse {
    // Parse bytecode
    let bytecode_str = payload.bytecode.trim_start_matches("0x");
    
    let bytecode = match hex::decode(bytecode_str) {
        Ok(b) => b,
        Err(e) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse {
                    error: "Invalid bytecode".to_string(),
                    details: Some(e.to_string()),
                }),
            ).into_response();
        }
    };

    if bytecode.is_empty() {
        return (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: "Empty bytecode".to_string(),
                details: None,
            }),
        ).into_response();
    }

    // Disassemble
    let instructions = match Disassembler::disassemble(&bytecode) {
        Ok(i) => i,
        Err(e) => {
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Disassembly failed".to_string(),
                    details: Some(e.to_string()),
                }),
            ).into_response();
        }
    };

    // Build CFG
    let cfg = ControlFlowGraph::build(&instructions);
    
    // Security analysis
    let security = SecurityAnalyzer::analyze(&instructions);

    // Convert risk indicators
    let risk_indicators: Vec<RiskIndicator> = security.risk_indicators
        .iter()
        .map(|r| RiskIndicator {
            name: r.name.clone(),
            severity: r.severity.clone(),
            description: r.description.clone(),
        })
        .collect();

    // Extract opcodes used
    let mut opcodes: Vec<String> = instructions
        .iter()
        .map(|i| format!("{:?}", i.opcode))
        .collect::<std::collections::HashSet<_>>()
        .into_iter()
        .collect();
    opcodes.sort();

    // Generate warnings
    let mut warnings = Vec::new();
    if security.has_selfdestruct {
        warnings.push("Contract contains SELFDESTRUCT - can be destroyed".to_string());
    }
    if security.has_delegatecall {
        warnings.push("Contract uses DELEGATECALL - potential proxy or upgrade pattern".to_string());
    }
    if security.has_callcode {
        warnings.push("Contract uses deprecated CALLCODE opcode".to_string());
    }

    let response = AnalyzeResponse {
        success: true,
        opcodes,
        functions: vec![], // TODO: Extract function boundaries
        selectors: security.function_selectors.clone(),
        is_proxy: security.has_delegatecall,
        has_sstore: security.has_sstore,
        has_call: security.has_external_call,
        has_delegatecall: security.has_delegatecall,
        has_selfdestruct: security.has_selfdestruct,
        complexity: security.complexity_score,
        warnings,
        risk_indicators,
        instruction_count: instructions.len(),
        block_count: cfg.graph.node_count(),
    };

    Json(response).into_response()
}

// ═══════════════════════════════════════════════════════════════════════════════
//                              SERVER
// ═══════════════════════════════════════════════════════════════════════════════

pub async fn run_server(port: u16) -> Result<(), Box<dyn std::error::Error>> {
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    let app = Router::new()
        .route("/health", get(health_handler))
        .route("/analyze", post(analyze_handler))
        .layer(cors);

    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    
    println!(r#"
 ═══════════════════════════════════════════════════════════════════════════════
  ██████╗ ███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗
 ██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║
 ███████╗ █████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║
 ╚════██║ ██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║
 ███████║ ███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
 ╚══════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝

  SENTINEL SHIELD - EVM Bytecode Decompiler Server v1.0.0

  Endpoints:
    GET  /health   - Health check
    POST /analyze  - Analyze bytecode

  Listening on http://{}
 ═══════════════════════════════════════════════════════════════════════════════
"#, addr);

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;
    
    Ok(())
}
