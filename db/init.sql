-- ═══════════════════════════════════════════════════════════════════════════════
--  SENTINEL SHIELD - Database Schema
--  PostgreSQL initialization script
--  Author: SENTINEL Team
-- ═══════════════════════════════════════════════════════════════════════════════

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ═══════════════════════════════════════════════════════════════════════════════
--                              ENUMS
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TYPE risk_level AS ENUM ('safe', 'low', 'medium', 'high', 'critical');
CREATE TYPE chain_id AS ENUM (
    'ethereum', 'bsc', 'polygon', 'arbitrum', 'optimism', 
    'base', 'avalanche', 'fantom', 'zksync'
);

-- ═══════════════════════════════════════════════════════════════════════════════
--                          VULNERABILITY PATTERNS
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE vulnerability_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    pattern_type VARCHAR(100) NOT NULL,
    bytecode_pattern BYTEA,
    selector VARCHAR(10),
    severity risk_level NOT NULL DEFAULT 'medium',
    confidence DECIMAL(3,2) DEFAULT 0.50,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed with known patterns
INSERT INTO vulnerability_patterns (name, description, pattern_type, selector, severity, confidence) VALUES
    ('Unlimited Mint', 'Owner can mint unlimited tokens', 'function', '0x40c10f19', 'high', 0.95),
    ('Pause Function', 'Owner can pause all transfers', 'function', '0x8456cb59', 'high', 0.90),
    ('Blacklist', 'Owner can blacklist addresses', 'function', '0x44337ea1', 'high', 0.85),
    ('Self-destruct', 'Contract can be destroyed', 'opcode', NULL, 'critical', 1.00),
    ('Delegatecall', 'Uses delegatecall for upgrades', 'opcode', NULL, 'medium', 0.70),
    ('Hidden Fee', 'Dynamic fee manipulation', 'pattern', NULL, 'high', 0.80);

-- ═══════════════════════════════════════════════════════════════════════════════
--                          CONTRACT ANALYSIS CACHE
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE contract_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    address VARCHAR(42) NOT NULL,
    chain chain_id NOT NULL,
    bytecode_hash VARCHAR(66) NOT NULL,
    is_verified BOOLEAN DEFAULT false,
    is_proxy BOOLEAN DEFAULT false,
    name VARCHAR(255),
    risk_score INTEGER DEFAULT 0 CHECK (risk_score >= 0 AND risk_score <= 100),
    risk_level risk_level DEFAULT 'safe',
    analysis_result JSONB,
    function_selectors TEXT[],
    vulnerabilities TEXT[],
    analyzed_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days',
    
    UNIQUE(address, chain)
);

CREATE INDEX idx_contract_address ON contract_analysis(address);
CREATE INDEX idx_contract_chain ON contract_analysis(chain);
CREATE INDEX idx_contract_risk ON contract_analysis(risk_level);
CREATE INDEX idx_contract_bytecode_hash ON contract_analysis(bytecode_hash);

-- ═══════════════════════════════════════════════════════════════════════════════
--                              SCAN HISTORY
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE scan_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_address VARCHAR(42) NOT NULL,
    chains_scanned chain_id[] NOT NULL,
    total_approvals INTEGER DEFAULT 0,
    critical_risks INTEGER DEFAULT 0,
    warnings INTEGER DEFAULT 0,
    overall_risk_score INTEGER DEFAULT 0,
    scan_result JSONB,
    scanned_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scan_wallet ON scan_history(wallet_address);
CREATE INDEX idx_scan_date ON scan_history(scanned_at DESC);

-- ═══════════════════════════════════════════════════════════════════════════════
--                              KNOWN SPENDERS
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE known_spenders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    address VARCHAR(42) NOT NULL,
    chain chain_id NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    is_verified BOOLEAN DEFAULT false,
    is_trusted BOOLEAN DEFAULT false,
    website VARCHAR(255),
    logo_url VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(address, chain)
);

-- Seed with known protocols
INSERT INTO known_spenders (address, chain, name, category, is_verified, is_trusted) VALUES
    ('0x7a250d5630b4cf539739df2c5dacb4c659f2488d', 'ethereum', 'Uniswap V2 Router', 'DEX', true, true),
    ('0xe592427a0aece92de3edee1f18e0157c05861564', 'ethereum', 'Uniswap V3 Router', 'DEX', true, true),
    ('0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f', 'ethereum', 'SushiSwap Router', 'DEX', true, true),
    ('0x1111111254fb6c44bac0bed2854e76f90643097d', 'ethereum', '1inch Router', 'DEX Aggregator', true, true),
    ('0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45', 'ethereum', 'Uniswap Universal Router', 'DEX', true, true),
    ('0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad', 'ethereum', 'Uniswap Permit2', 'DEX', true, true),
    ('0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9', 'ethereum', 'Aave V2 Lending Pool', 'Lending', true, true),
    ('0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2', 'ethereum', 'Aave V3 Pool', 'Lending', true, true);

CREATE INDEX idx_spender_address ON known_spenders(address);
CREATE INDEX idx_spender_chain ON known_spenders(chain);

-- ═══════════════════════════════════════════════════════════════════════════════
--                              BLACKLISTED CONTRACTS
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE blacklisted_contracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    address VARCHAR(42) NOT NULL,
    chain chain_id NOT NULL,
    reason TEXT NOT NULL,
    severity risk_level DEFAULT 'critical',
    reported_by VARCHAR(255),
    reported_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(address, chain)
);

CREATE INDEX idx_blacklist_address ON blacklisted_contracts(address);

-- ═══════════════════════════════════════════════════════════════════════════════
--                              API METRICS
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE api_metrics (
    id BIGSERIAL PRIMARY KEY,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_metrics_endpoint ON api_metrics(endpoint);
CREATE INDEX idx_metrics_date ON api_metrics(created_at DESC);

-- Partition by month for better performance
-- (For production, consider using pg_partman)

-- ═══════════════════════════════════════════════════════════════════════════════
--                              FUNCTIONS
-- ═══════════════════════════════════════════════════════════════════════════════

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_vulnerability_patterns_updated_at
    BEFORE UPDATE ON vulnerability_patterns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Cleanup expired cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM contract_analysis WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- ═══════════════════════════════════════════════════════════════════════════════
--                              VIEWS
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE VIEW v_high_risk_contracts AS
SELECT 
    address,
    chain,
    name,
    risk_score,
    risk_level,
    vulnerabilities,
    analyzed_at
FROM contract_analysis
WHERE risk_level IN ('high', 'critical')
ORDER BY risk_score DESC;

CREATE VIEW v_scan_stats AS
SELECT 
    DATE(scanned_at) as scan_date,
    COUNT(*) as total_scans,
    AVG(total_approvals) as avg_approvals,
    AVG(critical_risks) as avg_critical,
    AVG(overall_risk_score) as avg_risk_score
FROM scan_history
GROUP BY DATE(scanned_at)
ORDER BY scan_date DESC;

-- ═══════════════════════════════════════════════════════════════════════════════
--                              GRANTS
-- ═══════════════════════════════════════════════════════════════════════════════

-- Grant permissions (adjust for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sentinel;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sentinel;
