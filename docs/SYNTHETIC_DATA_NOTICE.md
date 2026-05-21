# Synthetic Data Notice

> **All data used in Tapish is synthetic / mock. No real personal information is collected or used.**

## Synthetic Data Sources

| Data Type | File | Description | Real-World Equivalent |
|---|---|---|---|
| **Social media posts** | `mock/tweets.json` (66 entries) | Fabricated Roman Urdu, Urdu, and English tweets. All usernames are fictional. | Twitter/X Filtered Stream API |
| **Weather data** | `mock/weather.json` | Mock time-series temperature, humidity, heat index for Lahore zones | Pakistan Meteorological Department API |
| **Traffic conditions** | `mock/traffic.json` | Mock congestion levels for major Lahore roads | Google Maps Traffic API |
| **IoT sensor data** | `mock/sensors.json` | Mock LESCO power grid readings + temperature sensors | LESCO SCADA / Smart grid telemetry |
| **Rescue 1122 calls** | `mock/calls.json` | Mock call frequency per area per hour | Rescue 1122 CAD system |
| **PSER vulnerability** | `mock/pser_data.json` | Mock Punjab Socio-Economic Registry household scores | Punjab IT Board PSER database |
| **Hospital data** | `mock/hospitals.json` | Real Lahore hospital names with mock capacity data | Punjab Health Department |
| **Resources** | `mock/resources.json` (33 units) | Mock ambulances, generators, water tankers, rescue teams, drones | Rescue 1122 + LESCO + WASA fleet data |
| **Neighborhoods** | `mock/neighborhoods.geojson` | Lahore neighborhoods with mock vulnerability overlays | LDA planning data + PSER |
| **Stress scenarios** | `mock/stress_scenarios.json` (7 scenarios) | Scripted multi-crisis test sequences | N/A (testing tool) |

## DEMO / LIVE Data Mode

The system supports two data modes, togglable via a switch on both the web dashboard and mobile app:

| Mode | Description |
|------|-------------|
| **DEMO** (default) | Uses mock JSON data files for all signal sources. Deterministic, repeatable scenarios for consistent demonstrations. |
| **LIVE** | Connects to real external APIs for weather, air quality, and environmental data: |

**Live APIs used in LIVE mode:**

| API | Data Provided | Free Tier |
|-----|---------------|-----------|
| **Open-Meteo** | Real-time temperature, humidity, heat index for Lahore | Yes (no key required) |
| **OpenAQ** | Real-time air quality / PM2.5 sensor readings | Yes (open data) |
| **Google AQI** | Air Quality Index for Lahore zones | Yes (with API key) |

> **Note:** Even in LIVE mode, social media posts, rescue call data, and PSER vulnerability scores remain mock/synthetic. Only environmental sensor data switches to real APIs.

## Privacy & Safety

- **No real Twitter/X data** — all tweets are fabricated with fictional usernames (`@bilal_lhr`, `@viral_lahore`, etc.)
- **No real personal data** — PSER scores are mock values, not derived from any real household registry
- **No real emergency dispatch** — resource dispatching is simulated in Firestore, not connected to real Rescue 1122 systems
- **Real FCM notifications** — Firebase Cloud Messaging sends real push notifications to the demo device only
- **Real TTS audio** — Google Cloud TTS generates real Urdu audio, but mosque announcements are not broadcast to real loudspeakers
- **Hospital names are real** — Mayo Hospital, Jinnah Hospital, etc. are real Lahore hospitals, but capacity data is mock

## Production Path

In production deployment, Tapish would integrate:
- Twitter/X Filtered Stream API (with proper data licensing)
- Pakistan Meteorological Department real-time feed
- LESCO SCADA API (via signed MOU with Punjab govt)
- Rescue 1122 CAD system API (via Punjab Safe Cities Authority)
- Punjab PSER database (via Punjab IT Board data-sharing agreement)
- Google Maps Traffic API (real-time)
- All personal data handling would require PECA compliance and informed consent
