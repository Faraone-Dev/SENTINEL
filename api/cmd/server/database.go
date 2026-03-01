package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"time"

	_ "github.com/lib/pq"
)

// ═══════════════════════════════════════════════════════════════════════════════
//                           POSTGRESQL CLIENT
// ═══════════════════════════════════════════════════════════════════════════════

// DB wraps *sql.DB with SENTINEL-specific queries.
type DB struct {
	conn *sql.DB
}

// NewDB opens a connection to PostgreSQL using DATABASE_URL and verifies it with a ping.
// Returns nil (no error) when DATABASE_URL is empty so the server can still run without a database.
func NewDB() (*DB, error) {
	dsn := getEnv("DATABASE_URL", "")
	if dsn == "" {
		log.Println("⚠️  DATABASE_URL not set — running without PostgreSQL")
		return nil, nil
	}

	conn, err := sql.Open("postgres", dsn)
	if err != nil {
		return nil, fmt.Errorf("sql.Open: %w", err)
	}

	// Connection pool tuning
	conn.SetMaxOpenConns(25)
	conn.SetMaxIdleConns(5)
	conn.SetConnMaxLifetime(5 * time.Minute)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := conn.PingContext(ctx); err != nil {
		conn.Close()
		return nil, fmt.Errorf("postgres ping: %w", err)
	}

	log.Println("🗄️  PostgreSQL connected")
	return &DB{conn: conn}, nil
}

// Close shuts down the database connection pool.
func (db *DB) Close() error {
	if db == nil || db.conn == nil {
		return nil
	}
	return db.conn.Close()
}

// ───────────────────────────────────────────────────────────────────────────────
//  Scan History
// ───────────────────────────────────────────────────────────────────────────────

// SaveScanResult persists a wallet scan to scan_history.
func (db *DB) SaveScanResult(ctx context.Context, result *WalletScanResult) error {
	if db == nil {
		return nil
	}

	chains := make([]string, len(result.ChainsScanned))
	for i, c := range result.ChainsScanned {
		chains[i] = string(c)
	}

	resultJSON, err := json.Marshal(result)
	if err != nil {
		return fmt.Errorf("marshal scan result: %w", err)
	}

	_, err = db.conn.ExecContext(ctx,
		`INSERT INTO scan_history
			(wallet_address, chains_scanned, total_approvals, critical_risks, warnings, overall_risk_score, scan_result)
		 VALUES ($1, $2::chain_id[], $3, $4, $5, $6, $7)`,
		result.WalletAddress,
		fmt.Sprintf("{%s}", joinStrings(chains, ",")),
		result.TotalApprovals,
		result.CriticalRisks,
		result.Warnings,
		result.OverallRiskScore,
		resultJSON,
	)
	if err != nil {
		return fmt.Errorf("insert scan_history: %w", err)
	}
	return nil
}

// GetRecentScans returns the last N scans for a wallet.
func (db *DB) GetRecentScans(ctx context.Context, wallet string, limit int) ([]WalletScanResult, error) {
	if db == nil {
		return nil, nil
	}

	rows, err := db.conn.QueryContext(ctx,
		`SELECT scan_result FROM scan_history
		 WHERE wallet_address = $1
		 ORDER BY scanned_at DESC LIMIT $2`,
		wallet, limit,
	)
	if err != nil {
		return nil, fmt.Errorf("query scan_history: %w", err)
	}
	defer rows.Close()

	var results []WalletScanResult
	for rows.Next() {
		var raw []byte
		if err := rows.Scan(&raw); err != nil {
			return nil, err
		}
		var r WalletScanResult
		if err := json.Unmarshal(raw, &r); err != nil {
			return nil, err
		}
		results = append(results, r)
	}
	return results, rows.Err()
}

// ───────────────────────────────────────────────────────────────────────────────
//  Contract Analysis Cache
// ───────────────────────────────────────────────────────────────────────────────

// GetCachedAnalysis checks if a contract has been recently analyzed.
func (db *DB) GetCachedAnalysis(ctx context.Context, address string, chain ChainID) (*ContractAnalysisResult, error) {
	if db == nil {
		return nil, nil
	}

	var raw []byte
	err := db.conn.QueryRowContext(ctx,
		`SELECT analysis_result FROM contract_analysis
		 WHERE address = $1 AND chain = $2 AND expires_at > NOW()`,
		address, string(chain),
	).Scan(&raw)

	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("query contract_analysis: %w", err)
	}

	var result ContractAnalysisResult
	if err := json.Unmarshal(raw, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// SaveAnalysis caches a contract analysis result (default 7 day TTL from init.sql).
func (db *DB) SaveAnalysis(ctx context.Context, result *ContractAnalysisResult) error {
	if db == nil {
		return nil
	}

	resultJSON, err := json.Marshal(result)
	if err != nil {
		return fmt.Errorf("marshal analysis: %w", err)
	}

	_, err = db.conn.ExecContext(ctx,
		`INSERT INTO contract_analysis
			(address, chain, bytecode_hash, risk_score, risk_level, analysis_result)
		 VALUES ($1, $2, $3, $4, $5, $6)
		 ON CONFLICT (address, chain) DO UPDATE SET
			risk_score = EXCLUDED.risk_score,
			risk_level = EXCLUDED.risk_level,
			analysis_result = EXCLUDED.analysis_result,
			analyzed_at = NOW(),
			expires_at = NOW() + INTERVAL '7 days'`,
		result.Address,
		string(result.Chain),
		"0x", // placeholder — could hash actual bytecode
		result.OverallRisk,
		riskLevelFromScore(result.OverallRisk),
		resultJSON,
	)
	if err != nil {
		return fmt.Errorf("upsert contract_analysis: %w", err)
	}
	return nil
}

// ───────────────────────────────────────────────────────────────────────────────
//  Blacklist Lookup
// ───────────────────────────────────────────────────────────────────────────────

// IsBlacklisted checks if an address is in the blacklisted_contracts table.
func (db *DB) IsBlacklisted(ctx context.Context, address string, chain ChainID) (bool, string, error) {
	if db == nil {
		return false, "", nil
	}

	var reason string
	err := db.conn.QueryRowContext(ctx,
		`SELECT reason FROM blacklisted_contracts
		 WHERE address = $1 AND chain = $2`,
		address, string(chain),
	).Scan(&reason)

	if err == sql.ErrNoRows {
		return false, "", nil
	}
	if err != nil {
		return false, "", err
	}
	return true, reason, nil
}

// ───────────────────────────────────────────────────────────────────────────────
//  API Metrics
// ───────────────────────────────────────────────────────────────────────────────

// RecordMetric logs an API request to the api_metrics table.
func (db *DB) RecordMetric(ctx context.Context, endpoint, method string, statusCode int, responseTimeMs int, ip string) {
	if db == nil {
		return
	}
	// Fire and forget — don't block request handling
	go func() {
		bgCtx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()
		_, _ = db.conn.ExecContext(bgCtx,
			`INSERT INTO api_metrics (endpoint, method, status_code, response_time_ms, ip_address)
			 VALUES ($1, $2, $3, $4, $5::inet)`,
			endpoint, method, statusCode, responseTimeMs, ip,
		)
	}()
}

// ───────────────────────────────────────────────────────────────────────────────
//  Helpers
// ───────────────────────────────────────────────────────────────────────────────

func joinStrings(ss []string, sep string) string {
	out := ""
	for i, s := range ss {
		if i > 0 {
			out += sep
		}
		out += s
	}
	return out
}

// riskLevelFromScore converts a 0-100 risk score to a PostgreSQL risk_level enum value.
func riskLevelFromScore(score int) string {
	switch {
	case score >= 80:
		return "critical"
	case score >= 60:
		return "high"
	case score >= 40:
		return "medium"
	case score >= 20:
		return "low"
	default:
		return "safe"
	}
}
