package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/redis/go-redis/v9"
)

// ═══════════════════════════════════════════════════════════════════════════════
//                             REDIS CLIENT
// ═══════════════════════════════════════════════════════════════════════════════

// RedisCache wraps go-redis for scan result and analysis caching.
type RedisCache struct {
	client *redis.Client
}

// NewRedisCache connects to Redis using REDIS_URL.
// Returns nil (no error) when REDIS_URL is empty so the server can run without Redis.
func NewRedisCache() (*RedisCache, error) {
	url := getEnv("REDIS_URL", "")
	if url == "" {
		log.Println("⚠️  REDIS_URL not set — running without Redis cache")
		return nil, nil
	}

	opts, err := redis.ParseURL(url)
	if err != nil {
		return nil, fmt.Errorf("redis parse URL: %w", err)
	}

	opts.PoolSize = 20
	opts.MinIdleConns = 5
	opts.DialTimeout = 5 * time.Second
	opts.ReadTimeout = 3 * time.Second
	opts.WriteTimeout = 3 * time.Second

	client := redis.NewClient(opts)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := client.Ping(ctx).Err(); err != nil {
		_ = client.Close()
		return nil, fmt.Errorf("redis ping: %w", err)
	}

	log.Println("🔴 Redis connected")
	return &RedisCache{client: client}, nil
}

// Close shuts down the Redis connection.
func (rc *RedisCache) Close() error {
	if rc == nil || rc.client == nil {
		return nil
	}
	return rc.client.Close()
}

// ───────────────────────────────────────────────────────────────────────────────
//  Scan Cache
// ───────────────────────────────────────────────────────────────────────────────

func scanCacheKey(wallet string, chains []ChainID) string {
	key := "scan:" + wallet
	for _, c := range chains {
		key += ":" + string(c)
	}
	return key
}

// GetScanCache returns a cached scan result if available.
func (rc *RedisCache) GetScanCache(ctx context.Context, wallet string, chains []ChainID) (*WalletScanResult, error) {
	if rc == nil {
		return nil, nil
	}

	data, err := rc.client.Get(ctx, scanCacheKey(wallet, chains)).Bytes()
	if err == redis.Nil {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	var result WalletScanResult
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// SetScanCache stores a scan result in Redis with a TTL.
func (rc *RedisCache) SetScanCache(ctx context.Context, wallet string, chains []ChainID, result *WalletScanResult, ttl time.Duration) error {
	if rc == nil {
		return nil
	}

	data, err := json.Marshal(result)
	if err != nil {
		return err
	}

	return rc.client.Set(ctx, scanCacheKey(wallet, chains), data, ttl).Err()
}

// ───────────────────────────────────────────────────────────────────────────────
//  Analysis Cache
// ───────────────────────────────────────────────────────────────────────────────

func analysisCacheKey(address string, chain ChainID) string {
	return fmt.Sprintf("analysis:%s:%s", address, chain)
}

// GetAnalysisCache returns a cached contract analysis if available.
func (rc *RedisCache) GetAnalysisCache(ctx context.Context, address string, chain ChainID) (*ContractAnalysisResult, error) {
	if rc == nil {
		return nil, nil
	}

	data, err := rc.client.Get(ctx, analysisCacheKey(address, chain)).Bytes()
	if err == redis.Nil {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	var result ContractAnalysisResult
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// SetAnalysisCache stores an analysis result in Redis with a 1-hour TTL.
func (rc *RedisCache) SetAnalysisCache(ctx context.Context, address string, chain ChainID, result *ContractAnalysisResult) error {
	if rc == nil {
		return nil
	}

	data, err := json.Marshal(result)
	if err != nil {
		return err
	}

	return rc.client.Set(ctx, analysisCacheKey(address, chain), data, 1*time.Hour).Err()
}

// ───────────────────────────────────────────────────────────────────────────────
//  Rate Limit (distributed)
// ───────────────────────────────────────────────────────────────────────────────

// CheckRateLimit implements a sliding-window rate limiter in Redis.
// Returns true if the request is allowed.
func (rc *RedisCache) CheckRateLimit(ctx context.Context, ip string, rpm int) (bool, error) {
	if rc == nil {
		return true, nil // fallback to in-memory limiter
	}

	key := "ratelimit:" + ip
	pipe := rc.client.Pipeline()
	pipe.Incr(ctx, key)
	pipe.Expire(ctx, key, 1*time.Minute)
	cmds, err := pipe.Exec(ctx)
	if err != nil {
		return true, err // allow on error, fallback to in-memory
	}

	count := cmds[0].(*redis.IntCmd).Val()
	return count <= int64(rpm), nil
}
