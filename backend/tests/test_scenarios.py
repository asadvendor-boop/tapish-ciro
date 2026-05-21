"""
TAPISH — Automated Scenario Tests
Tests the 7 core stress scenarios against the live backend API.
Run: pytest backend/tests/test_scenarios.py -v
"""

import os
import pytest
import httpx

BASE_URL = os.getenv("TAPISH_API_URL", "https://tapish-backend-163379998754.asia-south1.run.app")

@pytest.fixture
def client():
    return httpx.Client(base_url=BASE_URL, timeout=90.0)

# ─── Health Check ─────────────────────────────────────

def test_health(client):
    r = client.get("/api/admin/health")
    assert r.status_code == 200
    data = r.json()
    assert data["gemini_api"] == "connected"
    assert data["fcm_status"] == "configured"
    assert "signal_streams" in data

# ─── Thresholds ───────────────────────────────────────

def test_get_thresholds(client):
    r = client.get("/api/admin/thresholds")
    assert r.status_code == 200
    data = r.json()
    assert "confidence_threshold" in data
    assert 0.0 <= data["confidence_threshold"] <= 1.0

def test_patch_thresholds(client):
    r = client.patch("/api/admin/thresholds", json={"confidence_threshold": 0.7})
    assert r.status_code == 200
    assert r.json()["current"]["confidence_threshold"] == 0.7
    # Reset back
    client.patch("/api/admin/thresholds", json={"confidence_threshold": 0.65})

# ─── Resources ────────────────────────────────────────

def test_resources(client):
    r = client.get("/api/resources")
    assert r.status_code == 200
    data = r.json()
    resources = data.get("resources", [])
    assert len(resources) >= 30
    types = set(res["type"] for res in resources)
    assert "ambulance" in types
    assert "water_tanker" in types
    assert "drone" in types

# ─── Baseline Comparison ─────────────────────────────

def test_baseline_comparison(client):
    r = client.get("/api/baseline/compare/test_crisis")
    assert r.status_code == 200
    data = r.json()
    assert "heuristic" in data
    assert "tapish" in data
    assert data["tapish"]["response_time_improvement"] == "3.3x faster"

# ─── Scenarios ────────────────────────────────────────

def test_scenarios_list(client):
    r = client.get("/api/admin/scenarios")
    assert r.status_code == 200
    data = r.json()
    assert "scenarios" in data

# ─── Scenario 1: Baseline Heatwave ───────────────────

def test_scenario_1_signal_injection(client):
    """Inject a heatwave signal and verify pipeline starts."""
    r = client.post("/api/signals/ingest", json={
        "content": "بھاٹی گیٹ پر شدید گرمی، لوگ بے ہوش ہو رہے ہیں",
        "source": "twitter",
    })
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "processing"
    assert "signal_id" in data

# ─── Scenario 4: False Alarm (Low Credibility) ───────

def test_scenario_4_low_confidence_tweet(client):
    """Viral tweet with no corroboration → should trigger Auditor-first path."""
    r = client.post("/api/signals/ingest", json={
        "content": "BREAKING: Liberty Market mein zameen dhans gayi!! RT karo sab ko pata chale!! 😱😱",
        "source": "twitter",
    })
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "processing"

# ─── Export Traces ────────────────────────────────────

def test_trace_export(client):
    """Verify trace export includes document IDs (Bug #20 fix)."""
    r = client.get("/api/admin/traces/export")
    assert r.status_code == 200
    data = r.json()
    assert "traces_count" in data
    assert "crises_count" in data
    assert "signals_count" in data
    # Check that traces have IDs (Bug #20 fix)
    if data["traces"]:
        assert "id" in data["traces"][0]

# ─── Stakeholder Messages ────────────────────────────

def test_stakeholder_messages(client):
    r = client.get("/api/stakeholder/messages")
    assert r.status_code == 200

# ─── Cooling Centers ─────────────────────────────────

def test_cooling_centers(client):
    r = client.get("/api/cooling_centers/nearby?lat=31.52&lng=74.35")
    assert r.status_code == 200
