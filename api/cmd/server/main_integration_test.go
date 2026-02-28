package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

type mockScanner struct {
	result     *WalletScanResult
	err        error
	called     bool
	lastWallet string
	lastChains []ChainID
}

func newMockScanner(result *WalletScanResult, err error) *mockScanner {
	return &mockScanner{result: result, err: err}
}

func (m *mockScanner) ScanWallet(_ context.Context, walletAddress string, chains []ChainID) (*WalletScanResult, error) {
	m.called = true
	m.lastWallet = walletAddress
	clone := append([]ChainID(nil), chains...)
	m.lastChains = clone

	if m.err != nil {
		return nil, m.err
	}

	if m.result != nil {
		copy := *m.result
		copy.WalletAddress = walletAddress
		copy.ChainsScanned = clone
		return &copy, nil
	}

	return &WalletScanResult{
		WalletAddress: walletAddress,
		ChainsScanned: clone,
	}, nil
}

func TestHandleScanFiltersChains(t *testing.T) {
	mock := newMockScanner(&WalletScanResult{}, nil)
	server := NewServerWithScanner(mock)
	ts := httptest.NewServer(http.HandlerFunc(server.handleScan))
	defer ts.Close()

	resp, err := http.Get(ts.URL + "?wallet=0x1234567890123456789012345678901234567890&chains=ethereum,polygon,polygon")
	if err != nil {
		t.Fatalf("unexpected request error: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected status 200, got %d", resp.StatusCode)
	}

	var payload WalletScanResult
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		t.Fatalf("decode response: %v", err)
	}

	if !mock.called {
		t.Fatal("expected scanner to be invoked")
	}

	if len(mock.lastChains) != 2 {
		t.Fatalf("expected 2 chains passed to scanner, got %d", len(mock.lastChains))
	}

	if mock.lastChains[0] != Ethereum || mock.lastChains[1] != Polygon {
		t.Fatalf("unexpected chain order: %#v", mock.lastChains)
	}

	if len(payload.ChainsScanned) != 2 {
		t.Fatalf("expected 2 chains in response, got %d", len(payload.ChainsScanned))
	}
}

func TestHandleScanRejectsInvalidChains(t *testing.T) {
	mock := newMockScanner(&WalletScanResult{}, nil)
	server := NewServerWithScanner(mock)
	ts := httptest.NewServer(http.HandlerFunc(server.handleScan))
	defer ts.Close()

	resp, err := http.Get(ts.URL + "?wallet=0x1234567890123456789012345678901234567890&chains=ethereum,unknown")
	if err != nil {
		t.Fatalf("unexpected request error: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("expected status 400, got %d", resp.StatusCode)
	}

	if mock.called {
		t.Fatal("scanner should not run when chains are invalid")
	}
}
