package main

import (
	"fmt"
	"net/http"
	"sort"
	"sync"
	"sync/atomic"
	"time"
)

// ═══════════════════════════════════════════════════════════════════════════════
//                         PROMETHEUS METRICS
// ═══════════════════════════════════════════════════════════════════════════════

// Metrics collects Prometheus-compatible counters and histograms.
type Metrics struct {
	// Request counters by endpoint + status code
	requestCounts sync.Map // key: "endpoint:method:statusCode" → *int64

	// Latency tracking per endpoint (histogram buckets: 10ms, 50ms, 100ms, 250ms, 500ms, 1s, 2.5s, 5s, 10s)
	latencyBuckets []float64
	latencies      sync.Map // key: "endpoint:method" → *latencyHistogram

	// Business counters
	ScansTotal      atomic.Int64
	AnalyzesTotal   atomic.Int64
	RateLimitBlocks atomic.Int64
	AuthFailures    atomic.Int64

	// Uptime
	startTime time.Time
}

type latencyHistogram struct {
	mu      sync.Mutex
	buckets []float64 // upper bounds
	counts  []int64   // count per bucket
	sum     float64   // total latency
	count   int64     // total observations
}

func newLatencyHistogram(buckets []float64) *latencyHistogram {
	return &latencyHistogram{
		buckets: buckets,
		counts:  make([]int64, len(buckets)+1), // +1 for +Inf
	}
}

func (h *latencyHistogram) Observe(seconds float64) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.sum += seconds
	h.count++
	for i, bound := range h.buckets {
		if seconds <= bound {
			h.counts[i]++
			return
		}
	}
	h.counts[len(h.buckets)]++ // +Inf bucket
}

// Global metrics instance
var metrics *Metrics

func initMetrics() {
	metrics = &Metrics{
		latencyBuckets: []float64{0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0},
		startTime:      time.Now(),
	}
}

// RecordRequest records an HTTP request metric.
func (m *Metrics) RecordRequest(endpoint, method string, statusCode int, duration time.Duration) {
	// Increment counter
	key := fmt.Sprintf("%s:%s:%d", endpoint, method, statusCode)
	val, _ := m.requestCounts.LoadOrStore(key, new(int64))
	atomic.AddInt64(val.(*int64), 1)

	// Record latency
	latKey := fmt.Sprintf("%s:%s", endpoint, method)
	hist, _ := m.latencies.LoadOrStore(latKey, newLatencyHistogram(m.latencyBuckets))
	hist.(*latencyHistogram).Observe(duration.Seconds())
}

// metricsMiddleware wraps a handler to record request metrics.
func metricsMiddleware(endpoint string, next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rw := &responseWriter{ResponseWriter: w, statusCode: http.StatusOK}
		next(rw, r)
		metrics.RecordRequest(endpoint, r.Method, rw.statusCode, time.Since(start))
	}
}

// responseWriter captures the status code for metrics.
type responseWriter struct {
	http.ResponseWriter
	statusCode int
}

func (rw *responseWriter) WriteHeader(code int) {
	rw.statusCode = code
	rw.ResponseWriter.WriteHeader(code)
}

// handleMetrics serves Prometheus-compatible /metrics endpoint.
func handleMetrics(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain; version=0.0.4; charset=utf-8")

	// ── Uptime ──
	fmt.Fprintf(w, "# HELP sentinel_uptime_seconds Time since server start.\n")
	fmt.Fprintf(w, "# TYPE sentinel_uptime_seconds gauge\n")
	fmt.Fprintf(w, "sentinel_uptime_seconds %.2f\n\n", time.Since(metrics.startTime).Seconds())

	// ── HTTP request counters ──
	fmt.Fprintf(w, "# HELP sentinel_http_requests_total Total HTTP requests by endpoint, method, and status.\n")
	fmt.Fprintf(w, "# TYPE sentinel_http_requests_total counter\n")

	type entry struct {
		key   string
		count int64
	}
	var entries []entry
	metrics.requestCounts.Range(func(k, v interface{}) bool {
		entries = append(entries, entry{k.(string), atomic.LoadInt64(v.(*int64))})
		return true
	})
	sort.Slice(entries, func(i, j int) bool { return entries[i].key < entries[j].key })

	for _, e := range entries {
		// Parse "endpoint:method:status" back into labels
		parts := splitMetricKey(e.key)
		if len(parts) == 3 {
			fmt.Fprintf(w, "sentinel_http_requests_total{endpoint=%q,method=%q,status=%q} %d\n",
				parts[0], parts[1], parts[2], e.count)
		}
	}
	fmt.Fprintln(w)

	// ── Latency histograms ──
	fmt.Fprintf(w, "# HELP sentinel_http_request_duration_seconds HTTP request latency.\n")
	fmt.Fprintf(w, "# TYPE sentinel_http_request_duration_seconds histogram\n")

	var latKeys []string
	metrics.latencies.Range(func(k, _ interface{}) bool {
		latKeys = append(latKeys, k.(string))
		return true
	})
	sort.Strings(latKeys)

	for _, lk := range latKeys {
		v, _ := metrics.latencies.Load(lk)
		h := v.(*latencyHistogram)
		h.mu.Lock()

		parts := splitLatencyKey(lk)
		ep, method := parts[0], parts[1]

		var cumulative int64
		for i, bound := range h.buckets {
			cumulative += h.counts[i]
			fmt.Fprintf(w, "sentinel_http_request_duration_seconds_bucket{endpoint=%q,method=%q,le=\"%.3f\"} %d\n",
				ep, method, bound, cumulative)
		}
		cumulative += h.counts[len(h.buckets)] // +Inf
		fmt.Fprintf(w, "sentinel_http_request_duration_seconds_bucket{endpoint=%q,method=%q,le=\"+Inf\"} %d\n",
			ep, method, cumulative)
		fmt.Fprintf(w, "sentinel_http_request_duration_seconds_sum{endpoint=%q,method=%q} %.6f\n",
			ep, method, h.sum)
		fmt.Fprintf(w, "sentinel_http_request_duration_seconds_count{endpoint=%q,method=%q} %d\n",
			ep, method, h.count)

		h.mu.Unlock()
	}
	fmt.Fprintln(w)

	// ── Business counters ──
	fmt.Fprintf(w, "# HELP sentinel_scans_total Total wallet scans performed.\n")
	fmt.Fprintf(w, "# TYPE sentinel_scans_total counter\n")
	fmt.Fprintf(w, "sentinel_scans_total %d\n\n", metrics.ScansTotal.Load())

	fmt.Fprintf(w, "# HELP sentinel_analyzes_total Total contract analyses performed.\n")
	fmt.Fprintf(w, "# TYPE sentinel_analyzes_total counter\n")
	fmt.Fprintf(w, "sentinel_analyzes_total %d\n\n", metrics.AnalyzesTotal.Load())

	fmt.Fprintf(w, "# HELP sentinel_rate_limit_blocks_total Requests blocked by rate limiter.\n")
	fmt.Fprintf(w, "# TYPE sentinel_rate_limit_blocks_total counter\n")
	fmt.Fprintf(w, "sentinel_rate_limit_blocks_total %d\n\n", metrics.RateLimitBlocks.Load())

	fmt.Fprintf(w, "# HELP sentinel_auth_failures_total Authentication failures.\n")
	fmt.Fprintf(w, "# TYPE sentinel_auth_failures_total counter\n")
	fmt.Fprintf(w, "sentinel_auth_failures_total %d\n\n", metrics.AuthFailures.Load())

	// ── Go runtime info ──
	fmt.Fprintf(w, "# HELP sentinel_info Server build info.\n")
	fmt.Fprintf(w, "# TYPE sentinel_info gauge\n")
	fmt.Fprintf(w, "sentinel_info{version=\"1.0.0\",go_version=\"1.22\"} 1\n")
}

// splitMetricKey splits "endpoint:method:status" → [endpoint, method, status].
func splitMetricKey(key string) []string {
	parts := make([]string, 0, 3)
	for i, last := 0, 0; i <= len(key); i++ {
		if i == len(key) || key[i] == ':' {
			parts = append(parts, key[last:i])
			last = i + 1
			if len(parts) == 3 {
				return parts
			}
		}
	}
	return parts
}

// splitLatencyKey splits "endpoint:method" → [endpoint, method].
func splitLatencyKey(key string) [2]string {
	for i := len(key) - 1; i >= 0; i-- {
		if key[i] == ':' {
			return [2]string{key[:i], key[i+1:]}
		}
	}
	return [2]string{key, ""}
}
