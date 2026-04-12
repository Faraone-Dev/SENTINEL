"""
 ██████╗ ███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗
██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║
███████╗ █████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║
╚════██║ ██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║
███████║ ███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
╚══════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝

SENTINEL SHIELD - Analyzer HTTP Server
FastAPI server exposing the vulnerability analyzer for integration with Go API

Author: Faraone-Dev
"""

import os
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Import analyzer
try:
    from analyzer import AnalyzerService
except ImportError:
    from .analyzer import AnalyzerService

# ═══════════════════════════════════════════════════════════════════════════════
#                              LOGGING SETUP
# ═══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("sentinel.server")

# ═══════════════════════════════════════════════════════════════════════════════
#                              REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class AnalyzeRequest(BaseModel):
    """Request model for contract analysis"""
    address: str = Field(..., description="Contract address")
    chain: str = Field(default="ethereum", description="Blockchain network")
    bytecode: str = Field(..., description="Contract bytecode (hex string)")
    decompiler_result: Optional[Dict[str, Any]] = Field(default=None, description="Pre-computed decompiler output")

class VulnerabilityResponse(BaseModel):
    """Vulnerability information"""
    id: str
    name: str
    severity: str
    description: str
    location: Optional[str] = None

class PatternResponse(BaseModel):
    """Pattern match information"""
    pattern: str
    description: str
    is_malicious: bool

class AnalyzeResponse(BaseModel):
    """Response model for contract analysis"""
    address: str
    chain: str
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: str
    vulnerabilities: List[VulnerabilityResponse]
    patterns: List[PatternResponse]
    recommendations: List[str]
    bytecode_hash: str
    is_proxy: bool = False
    is_verified: bool = False

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str

# ═══════════════════════════════════════════════════════════════════════════════
#                              FASTAPI APP
# ═══════════════════════════════════════════════════════════════════════════════

# Global analyzer service
analyzer_service: Optional[AnalyzerService] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global analyzer_service
    logger.info("🚀 Initializing SENTINEL Analyzer Service...")
    analyzer_service = AnalyzerService()
    logger.info("✅ Analyzer Service ready")
    
    yield
    
    logger.info("👋 Shutting down Analyzer Service...")

app = FastAPI(
    title="SENTINEL Analyzer API",
    description="Heuristic vulnerability pattern analyzer for smart contracts",
    version="1.0.0",
    lifespan=lifespan
)

# Internal API key for service-to-service auth
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")

async def verify_internal_auth(request: Request):
    """Verify internal service API key if configured"""
    if INTERNAL_API_KEY:
        api_key = request.headers.get("X-API-Key", "")
        if api_key != INTERNAL_API_KEY:
            raise HTTPException(status_code=401, detail="Unauthorized")

# Global exception handler - sanitize errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "internal server error"}
    )

# CORS middleware with configurable origins
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins != ["*"] else ["*"],
    allow_credentials=False if cors_origins == ["*"] else True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)

# ═══════════════════════════════════════════════════════════════════════════════
#                              ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="sentinel-analyzer",
        version="1.0.0"
    )

@app.post("/api/analyze", response_model=AnalyzeResponse, dependencies=[Depends(verify_internal_auth)])
async def analyze_contract(request: AnalyzeRequest):
    """
    Analyze a smart contract for vulnerabilities
    
    - **address**: Contract address (0x...)
    - **chain**: Blockchain network (ethereum, bsc, polygon, etc.)
    - **bytecode**: Contract bytecode in hex format
    - **decompiler_result**: Optional pre-computed decompiler output
    """
    if analyzer_service is None:
        raise HTTPException(status_code=503, detail="Analyzer service not initialized")
    
    try:
        logger.info(f"📊 Analyzing contract {request.address} on {request.chain}")
        
        # Build request for analyzer
        analysis_request = {
            "address": request.address,
            "chain": request.chain,
            "bytecode": request.bytecode,
            "decompiler_result": request.decompiler_result
        }
        
        # Run analysis
        result = await analyzer_service.analyze(analysis_request)
        
        # Convert vulnerabilities to response format
        vulnerabilities = []
        for vuln in result.get("vulnerabilities", []):
            vulnerabilities.append(VulnerabilityResponse(
                id=vuln.get("type", "unknown"),
                name=vuln.get("title", "Unknown"),
                severity=vuln.get("severity", "low"),
                description=vuln.get("description", ""),
                location=vuln.get("location")
            ))
        
        # Generate patterns from function selectors
        patterns = []
        for selector in result.get("function_selectors", []):
            patterns.append(PatternResponse(
                pattern=selector,
                description=f"Function selector {selector}",
                is_malicious=False  # Would need deeper analysis
            ))
        
        # Generate recommendations based on findings
        recommendations = []
        if result.get("risk_score", 0) > 50:
            recommendations.append("⚠️ High risk contract - exercise caution")
        if any(v.get("type") == "honeypot" for v in result.get("vulnerabilities", [])):
            recommendations.append("🚨 Possible honeypot - avoid interacting")
        if any(v.get("type") == "rug_pull" for v in result.get("vulnerabilities", [])):
            recommendations.append("🚨 Rug pull patterns detected - high risk")
        if result.get("is_proxy"):
            recommendations.append("📋 Proxy contract - implementation could change")
        if not recommendations:
            recommendations.append("✅ No critical issues detected")
        
        logger.info(f"✅ Analysis complete: risk_score={result.get('risk_score', 0)}")
        
        return AnalyzeResponse(
            address=result.get("address", request.address),
            chain=result.get("chain", request.chain),
            risk_score=result.get("risk_score", 0),
            risk_level=result.get("risk_level", "safe"),
            vulnerabilities=vulnerabilities,
            patterns=patterns,
            recommendations=recommendations,
            bytecode_hash=result.get("bytecode_hash", ""),
            is_proxy=result.get("is_proxy", False),
            is_verified=result.get("is_verified", False)
        )
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail="analysis failed, please try again")

@app.get("/api/stats")
async def get_stats():
    """Get analyzer statistics"""
    return {
        "service": "sentinel-analyzer",
        "version": "1.0.0",
        "supported_chains": [
            "ethereum", "bsc", "polygon", "arbitrum", 
            "optimism", "base", "avalanche", "fantom", "zksync"
        ],
        "vulnerability_types": [
            "honeypot", "rug_pull", "hidden_fee", "reentrancy",
            "mint_function", "burn_function", "blacklist", "pause",
            "proxy_upgrade", "selfdestruct", "approval_exploit"
        ]
    }

# ═══════════════════════════════════════════════════════════════════════════════
#                              MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Run the FastAPI server"""
    print("""
 ═══════════════════════════════════════════════════════════════════════════════
  ██████╗ ███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗
 ██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║
 ███████╗ █████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║
 ╚════██║ ██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║
 ███████║ ███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
 ╚══════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝

  SENTINEL SHIELD - Heuristic Vulnerability Analyzer Server v1.0.0

  Endpoints:
    GET  /health       - Health check
    POST /api/analyze  - Analyze contract
    GET  /api/stats    - Get analyzer stats
 ═══════════════════════════════════════════════════════════════════════════════
    """)
    
    port = int(os.getenv("PORT", "5000"))
    host = os.getenv("HOST", "0.0.0.0")
    workers = int(os.getenv("WORKERS", "2"))
    
    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        workers=workers,
        reload=False,
        log_level="info",
    )

if __name__ == "__main__":
    main()
