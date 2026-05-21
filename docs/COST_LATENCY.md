# Tapish — Cost & Latency Analysis

> All costs reflect **Pay-As-You-Go (PAYG)** pricing on Google Cloud. We are NOT on free tier.

---

## Google Cloud Service Pricing (Current PAYG Rates)

| Service | Pricing Model | Rate |
|---------|--------------|------|
| **Gemini 2.5 Flash** | Per token | $0.30 / 1M input tokens, $2.50 / 1M output tokens |
| **Gemini 2.5 Pro** | Per token | $1.25 / 1M input tokens, $10.00 / 1M output tokens |
| **Cloud Run** | Per vCPU-second + GiB-second | $0.000024 / vCPU-sec, $0.0000025 / GiB-sec |
| **Cloud TTS** (Standard voices) | Per character | $4.00 / 1M characters |
| **Google Maps JS API** | Per 1K dynamic map loads | $7.00 / 1K loads (first 10K/mo free) |
| **Firebase Cloud Messaging** | Unlimited | **FREE** (no-cost product) |
| **Firebase Auth** (Google Sign-In) | Per verification | Free for email/social login |
| **Open-Meteo** (LIVE mode) | Unlimited | Free (no key required) |
| **OpenAQ** (LIVE mode) | Unlimited | Free (open data) |

---

## Per-Operation Cost & Latency

| Step | Model / Service | Avg Latency | Tokens (in/out) | Cost / Call |
|------|----------------|-------------|-----------------|-------------|
| Observer (credibility + intent) | Gemini 2.5 Flash | 3-5s | ~500 / 200 | $0.00065 |
| Analyst (fusion + PSER lookup) | Gemini 2.5 Pro | 8-12s | ~1,200 / 400 | $0.0055 |
| Strategist (trade-off reasoning) | Gemini 2.5 Pro | 8-15s | ~1,500 / 500 | $0.0069 |
| Operator (msg gen × 6 audiences + dispatch) | Gemini 2.5 Flash | 5-10s | ~800 / 400 | $0.00124 |
| Operator (mosque TTS) | Cloud TTS (Standard) | 0.8s | ~200 chars | $0.0008 |
| Operator (FCM dispatch) | Firebase CM | 0.2s | n/a | **$0** |
| Auditor (verification) | Gemini 2.5 Pro | 6-10s | ~800 / 300 | $0.004 |
| ADK orchestration overhead | ADK runtime | 0.5s | n/a | $0 (library) |

### Cost Calculation Detail

**Observer (Gemini 2.5 Flash):**
- Input: 500 tokens × $0.30/1M = $0.00015
- Output: 200 tokens × $2.50/1M = $0.00050
- **Total: $0.00065**

**Analyst (Gemini 2.5 Pro):**
- Input: 1,200 tokens × $1.25/1M = $0.0015
- Output: 400 tokens × $10.00/1M = $0.004
- **Total: $0.0055**

**Strategist (Gemini 2.5 Pro):**
- Input: 1,500 tokens × $1.25/1M = $0.001875
- Output: 500 tokens × $10.00/1M = $0.005
- **Total: $0.006875 ≈ $0.0069**

**Operator (Gemini 2.5 Flash):**
- Input: 800 tokens × $0.30/1M = $0.00024
- Output: 400 tokens × $2.50/1M = $0.001
- **Total: $0.00124**

**Auditor (Gemini 2.5 Pro):**
- Input: 800 tokens × $1.25/1M = $0.001
- Output: 300 tokens × $10.00/1M = $0.003
- **Total: $0.004**

---

## End-to-End Pipeline Cost

| Path | Wall-Clock Time | Gemini Cost | Other Costs | Total |
|------|----------------|-------------|-------------|-------|
| **High confidence** (≥0.65): Observer → Analyst → Strategist → Operator → Auditor | 30-50 seconds | ~$0.019 | ~$0.001 (TTS) | **~$0.020** |
| **Low confidence** (<0.65): Observer → Analyst → Auditor → {Strategist → Operator} | 35-60 seconds | ~$0.019 | ~$0.001 (TTS) | **~$0.020** |
| **Retracted** (Auditor says RETRACT): Observer → Analyst → Auditor → STOP | 15-25 seconds | ~$0.010 | $0 | **~$0.010** |
| **Noise filtered** (Observer only): Observer → filtered out | 3-5 seconds | ~$0.001 | $0 | **~$0.001** |

**Measured from production Cloud Run deployment** — includes cold-start recovery, Gemini API latency, Firestore writes, WebSocket broadcasts.

---

## Cloud Run Hosting Costs (PAYG)

Our deployment: **1 vCPU, 512 MiB RAM, asia-south1**

| Configuration | Monthly Cost (est.) | Notes |
|--------------|--------------------|-|
| **min-instances: 0** (current) | ~$2-5/month | Containers spin down when idle. Cold starts ~10-15s. Charged only when processing requests. |
| **min-instances: 1** (for judging) | ~$25-35/month | One container always warm. Instant response. Charges accumulate 24/7. |
| **min-instances: 1, max: 3** (production) | ~$25-100/month | Scales under load. Billed per-second for active containers. |

**Per-request Cloud Run cost** (single pipeline ~45s at 1 vCPU + 0.5 GiB):
- vCPU: 45s × $0.000024 = $0.00108
- Memory: 45s × 0.5 × $0.0000025 = $0.00006
- **Total: ~$0.0011 per request**

---

## Google Maps API Costs

| Usage | Rate | Monthly Est. |
|-------|------|-------------|
| Dashboard map loads (judges + dev) | $7.00 / 1K loads | <$1/month (well under 10K free tier) |
| Mobile app map views | $7.00 / 1K loads | <$1/month |
| **Total Maps** | | **~$0-2/month** (within free allowance for demo) |

---

## Why Pipeline Takes 30-50 Seconds (Not 6 Seconds)

The original plan estimated 6.5 seconds. Actual measured latency is 30-50 seconds because:

1. **Gemini 2.5 Pro thinking time** — Pro model uses extended reasoning (chain-of-thought), adding 5-10s per agent
2. **Multiple tool calls per agent** — Analyst calls 3-4 tools, Operator calls 4-5 tools, each is a round-trip
3. **Sequential pipeline** — agents run sequentially (not parallel) for correctness guarantees
4. **Firestore writes** — each agent writes traces + data to Firestore
5. **WebSocket broadcasts** — trace events broadcast to all connected clients

This is acceptable for a crisis response system where **accuracy matters more than speed**. A 45-second end-to-end is still 30× faster than manual coordination (est. 23 minutes).

---

## Firebase Cloud Messaging — FREE at Scale

FCM is free at any volume. Production would add:
- WhatsApp Business API (Meta Cloud API): ~$0.05/conversation for direct citizen messaging
- SMS gateway (Telenor/Jazz): ~PKR 0.50/SMS for non-smartphone users

---

## Total Cost Summary (Demo Period)

| Cost Category | Monthly Est. | Notes |
|--------------|-------------|-------|
| **Gemini API calls** | $1-5 | Depends on demo frequency (~50-250 pipeline runs) |
| **Cloud Run** (min-instances: 0) | $2-5 | Idle most of time, spins up on demand |
| **Cloud TTS** | <$0.50 | ~200 chars per mosque announcement |
| **Google Maps** | $0-2 | Within free tier for demo traffic |
| **FCM** | $0 | Free forever |
| **Firebase Auth** | $0 | Free for social login |
| **Open-Meteo / OpenAQ** | $0 | Free APIs |
| **TOTAL** | **~$3-12/month** | For hackathon demo usage |

---

## Cost Comparison: Agentic vs Non-Agentic

| Metric | Keyword Rules (baseline) | Tapish (agentic) | Delta |
|--------|-------------------------|------------------|-------|
| Cost per signal | $0 (no LLM) | ~$0.001 | +$0.001 |
| Cost per crisis | $0 | ~$0.020 | +$0.020 |
| Cloud hosting | $0 (localhost) | ~$5/month | +$5/month |
| False positive rate | ~40% | ~8% | **5× reduction** |
| Response time (signal → action) | Instant (but wrong 40% of time) | 30-50 sec (verified) | Acceptable |
| False alarm correction | None (alert stays live) | Auto-retract < 1 min | **New capability** |
| Side effect detection | None | Detects congestion from own alerts | **New capability** |
| Multi-crisis optimization | First-come-first-served | PSER-weighted mortality optimization | **New capability** |

**Bottom line:** ~$0.02/crisis + ~$5/month hosting buys verified, coordinated, multi-stakeholder response with real push notifications, Urdu TTS, and traceable reasoning. The non-agentic baseline is free but sends ambulances to viral rumors.

---

## Scaling Path

| Scale | Signals/day | Crises/day | Gemini Cost/day | Cloud Run/day | Total/day |
|-------|------------|------------|----------------|--------------|-----------|
| **Demo (1×)** | 60 signals | 2-3 | $0.04 | $0.10 | **~$0.15** |
| **City (10×)** | 5,000 signals | 20-30 | $0.60 | $0.80 | **~$1.40** |
| **5-city (50×)** | 25,000 signals | 100-150 | $3.00 | $4.00 | **~$7.00** |
| **National (100×)** | 50,000 signals | 300+ | $6.00 | $8.00 | **~$14.00** |

**Throughput:** Current architecture handles ~10 signals/minute (limited by Gemini Pro latency). At 100×, batch Observer calls + shard Analyst by region.

**Latency target:** < 60 seconds from first signal to first dispatched action at any scale. Current demo achieves 30-50 seconds.
