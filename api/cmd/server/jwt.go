package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"
)

// ═══════════════════════════════════════════════════════════════════════════════
//                          JWT AUTHENTICATION
// ═══════════════════════════════════════════════════════════════════════════════

// JWTClaims represents the payload of a JWT token.
type JWTClaims struct {
	Sub  string `json:"sub"`            // Subject (user/service identifier)
	Role string `json:"role,omitempty"` // Role: "admin", "reader", etc.
	Exp  int64  `json:"exp"`            // Expiry (Unix timestamp)
	Iat  int64  `json:"iat"`            // Issued-at
	Iss  string `json:"iss"`            // Issuer
}

// jwtSecret holds the HMAC signing key (loaded from JWT_SECRET env var).
var jwtSecret []byte

func initJWT() {
	secret := getEnv("JWT_SECRET", "")
	if secret == "" {
		log.Println("⚠️  JWT_SECRET not set — JWT auth disabled (API-key auth still active)")
		return
	}
	if len(secret) < 32 {
		log.Println("⚠️  JWT_SECRET is shorter than 32 chars — consider using a stronger secret")
	}
	jwtSecret = []byte(secret)
	log.Println("🔑 JWT authentication enabled")
}

// ────────────────────────────── Token creation ──────────────────────────────

// CreateJWT generates an HS256-signed JWT with the given claims.
func CreateJWT(sub, role string, ttl time.Duration) (string, error) {
	if len(jwtSecret) == 0 {
		return "", fmt.Errorf("JWT_SECRET not configured")
	}

	now := time.Now()
	claims := JWTClaims{
		Sub:  sub,
		Role: role,
		Iat:  now.Unix(),
		Exp:  now.Add(ttl).Unix(),
		Iss:  "sentinel-api",
	}

	header := base64URLEncode([]byte(`{"alg":"HS256","typ":"JWT"}`))

	payload, err := json.Marshal(claims)
	if err != nil {
		return "", err
	}
	payloadB64 := base64URLEncode(payload)

	sigInput := header + "." + payloadB64
	sig := signHS256([]byte(sigInput))

	return sigInput + "." + base64URLEncode(sig), nil
}

// ────────────────────────────── Token validation ──────────────────────────────

// ValidateJWT parses and validates a JWT token, returning its claims.
func ValidateJWT(tokenString string) (*JWTClaims, error) {
	if len(jwtSecret) == 0 {
		return nil, fmt.Errorf("JWT_SECRET not configured")
	}

	parts := strings.SplitN(tokenString, ".", 3)
	if len(parts) != 3 {
		return nil, fmt.Errorf("malformed token")
	}

	// Verify signature
	sigInput := parts[0] + "." + parts[1]
	expectedSig := signHS256([]byte(sigInput))
	actualSig, err := base64URLDecode(parts[2])
	if err != nil {
		return nil, fmt.Errorf("invalid signature encoding")
	}
	if !hmac.Equal(expectedSig, actualSig) {
		return nil, fmt.Errorf("invalid signature")
	}

	// Decode claims
	claimsJSON, err := base64URLDecode(parts[1])
	if err != nil {
		return nil, fmt.Errorf("invalid payload encoding")
	}

	var claims JWTClaims
	if err := json.Unmarshal(claimsJSON, &claims); err != nil {
		return nil, fmt.Errorf("invalid claims: %w", err)
	}

	// Check expiry
	if time.Now().Unix() > claims.Exp {
		return nil, fmt.Errorf("token expired")
	}

	return &claims, nil
}

// ────────────────────────────── Middleware ──────────────────────────────

// jwtAuthMiddleware validates JWT or falls through to API-key auth.
// Supports: Authorization: Bearer <jwt> — if JWT_SECRET is set and the token
// is a JWT (3 dot-separated parts), it validates the JWT. Otherwise, it falls
// through to the existing API-key middleware.
func jwtAuthMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// If JWT is not configured, skip straight to next (API-key auth)
		if len(jwtSecret) == 0 {
			next(w, r)
			return
		}

		auth := r.Header.Get("Authorization")
		if !strings.HasPrefix(auth, "Bearer ") {
			// No bearer token — let apiKeyAuthMiddleware handle it
			next(w, r)
			return
		}

		token := strings.TrimPrefix(auth, "Bearer ")

		// If it looks like a JWT (3 parts), validate it
		if strings.Count(token, ".") == 2 {
			claims, err := ValidateJWT(token)
			if err != nil {
				metrics.AuthFailures.Add(1)
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusUnauthorized)
				_ = json.NewEncoder(w).Encode(map[string]string{
					"error": "invalid JWT: " + err.Error(),
				})
				return
			}

			// Attach claims to request context (for downstream handlers)
			r.Header.Set("X-JWT-Sub", claims.Sub)
			r.Header.Set("X-JWT-Role", claims.Role)
			next(w, r)
			return
		}

		// Not a JWT — pass through to API-key auth
		next(w, r)
	}
}

// ────────────────────────────── HTTP handler ──────────────────────────────

// handleTokenCreate handles POST /api/v1/auth/token — issues a new JWT.
// Requires API-key authentication (admin only).
func (s *Server) handleTokenCreate(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	if len(jwtSecret) == 0 {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusServiceUnavailable)
		_ = json.NewEncoder(w).Encode(map[string]string{
			"error": "JWT not configured (set JWT_SECRET env var)",
		})
		return
	}

	var req struct {
		Sub  string `json:"sub"`
		Role string `json:"role"`
		TTL  string `json:"ttl"` // e.g. "24h", "72h"
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		_ = json.NewEncoder(w).Encode(map[string]string{
			"error": "invalid request body: " + err.Error(),
		})
		return
	}

	if req.Sub == "" {
		req.Sub = "api-client"
	}
	if req.Role == "" {
		req.Role = "reader"
	}
	ttl := 24 * time.Hour
	if req.TTL != "" {
		parsed, err := time.ParseDuration(req.TTL)
		if err == nil && parsed > 0 {
			ttl = parsed
		}
	}
	// Cap TTL at 30 days
	if ttl > 30*24*time.Hour {
		ttl = 30 * 24 * time.Hour
	}

	token, err := CreateJWT(req.Sub, req.Role, ttl)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		_ = json.NewEncoder(w).Encode(map[string]string{
			"error": "failed to create token",
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"token":      token,
		"expires_in": int(ttl.Seconds()),
		"token_type": "Bearer",
	})
}

// ────────────────────────────── Helpers ──────────────────────────────

func signHS256(data []byte) []byte {
	mac := hmac.New(sha256.New, jwtSecret)
	mac.Write(data)
	return mac.Sum(nil)
}

func base64URLEncode(data []byte) string {
	return base64.RawURLEncoding.EncodeToString(data)
}

func base64URLDecode(s string) ([]byte, error) {
	return base64.RawURLEncoding.DecodeString(s)
}
