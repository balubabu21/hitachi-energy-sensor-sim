# Grid Sensor Simulator

A web app that catalogues **Hitachi Energy product families**, lists the **sensors** each could carry,
documents every **field** (data type, unit, range, nominal value) and generates **realistic mock JSON**
— with a code panel showing the exact Python that produced it.

> Unofficial. Product names and descriptions are paraphrased from
> [hitachienergy.com/products-and-solutions](https://www.hitachienergy.com/products-and-solutions).
> Sensors, fields and ranges are engineering assumptions for simulation, not Hitachi Energy specifications.

| Layer | Tech |
|---|---|
| Backend | Python 3.12 · FastAPI · Pydantic |
| Frontend | TypeScript · Next.js 16 (App Router) · React 19 |
| Containers | Docker (multi-stage), `docker-compose` for local |
| Cloud | Azure Container Apps · Azure Container Registry · Log Analytics |
| IaC | Terraform (azurerm 4.x) |

## Architecture

```
Browser ──HTTPS──▶ Container App "web" (Next.js, public ingress)
                       │  /api/*  route handler proxies at runtime (BACKEND_URL)
                       ▼
                  Container App "api" (FastAPI, internal ingress only)
Images pulled from ACR with a user-assigned managed identity (AcrPull) — no registry passwords.
```

## Project layout

```
backend/
  app/catalog.py     products → sensors → fields (the knowledge base — edit here)
  app/generator.py   stdlib-only mock generator (shown verbatim in the UI code panel)
  app/models.py      Pydantic models + DSL helpers (num, integer, counter, flag, enum, phases)
  app/main.py        FastAPI routes
  tests/             pytest suite (ranges, determinism, standalone script runs)
frontend/
  app/page.tsx       catalogue UI
  app/api/[...path]/route.ts   runtime proxy to the backend
  components/        FieldsTable, JsonPanel, CodePanel, CodeBlock
infra/terraform/     RG, ACR, identity, Log Analytics, Container Apps env + 2 apps
scripts/deploy.sh    terraform → az acr build → terraform (one command deploy)
docker-compose.yml
```

## Run locally

### Requirements

- Python 3.12
- Node.js 22 and npm
- Or Docker with the Docker Compose plugin (to use the container option below)

No database, API keys, or `.env` file are required for local development.

### Run with Docker

From the project root:

```bash
docker compose up --build
```

Open http://localhost:3000. The API is also available at http://localhost:8000/docs.
Stop both containers with `Ctrl+C`; to remove the stopped containers, run `docker compose down`.

### Run without Docker

Install the backend dependencies and start the API:

```bash
# Terminal 1, from the project root
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

In a second terminal, install the frontend dependencies and start the web app:

```bash
# Terminal 2, from the project root
cd frontend
npm ci
BACKEND_URL=http://localhost:8000 npm run dev
```

Open http://localhost:3000. The frontend proxies `/api/*` requests to the backend; keep both
servers running while using the app. Stop each server with `Ctrl+C` in its terminal.

To run the backend tests, from the `backend/` directory with its virtual environment activated:

```bash
pytest -q
```

## Deploy to Azure

Prereqs: Azure CLI (`az login`), Terraform ≥ 1.6, and an Azure subscription with permission to
create resources and assign the `AcrPull` role. Docker is not needed — images are built in ACR.

```bash
cp infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars   # set subscription_id
az account set --subscription <subscription_id>   # use the same subscription as terraform.tfvars
./scripts/deploy.sh          # prints the public URL at the end
./scripts/destroy.sh         # remove everything
```

`deploy.sh` registers the Azure Container Apps resource provider, first applies only the registry +
identity (`-target`), builds both images with `az acr build`, then applies the full stack with the
new `image_tag`. Re-run it to ship changes. Keep the Azure CLI's active subscription aligned with
`subscription_id` in `terraform.tfvars`.
Apps scale to zero by default (`min_replicas = 0`), so the first request after idle takes a few seconds.

## API

| Method | Path | Description |
|---|---|---|
| GET | `/api/products` | Product summaries |
| GET | `/api/products/{product}` | Product with sensors, fields and envelope fields |
| GET | `/api/products/{product}/sensors/{sensor}/mock` | Mock readings. Query: `count` (1–1000), `seed`, `anomaly_rate` (0–1), `interval_s`, `asset_id` |
| GET | `/api/products/{product}/sensors/{sensor}/code` | Generator source (standalone script, API route, curl) |
| GET | `/api/health` | Liveness |

Example reading:
```json
{
  "timestamp": "2026-10-29T10:31:57Z",
  "asset_id": "HE-PT-0001",
  "sensor_id": "thermal-monitor",
  "sequence": 0,
  "quality": "GOOD",
  "values": {
    "top_oil_temp": 60.2,
    "bottom_oil_temp": 42.3,
    "winding_hotspot_temp": { "L1": 70.2, "L2": 79.1, "L3": 77.1 },
    "ambient_temp": 17.9,
    "ageing_rate": 0.449
  }
}
```

### How values are generated

| dtype | JSON | Behaviour |
|---|---|---|
| `float` / `integer` | number / integer | Mean-reverting random walk around `nominal`, clipped to `[min, max]` |
| `float_array` | object `{L1, L2, L3}` | Independent walk per phase/label |
| `counter` | integer | Monotonic, +0…`step` per sample |
| `boolean` | boolean | `true` with probability `p_true` |
| `enum` | string | Weighted choice, sticky between samples |

`anomaly_rate` pushes one field per affected reading to 80–100 % of the way to its limit (or the rarest
enum state / `true`), marks `quality: UNCERTAIN` and adds `"anomaly": {"field": ...}`. `seed` makes the values reproducible.

## Catalogue (23 product families, 42 sensors; field count in brackets)

| Product | Sensors |
|---|---|
| Power Transformers | Dissolved Gas Analysis (DGA) monitor (10)<br>Moisture-in-oil sensor (3)<br>Thermal / fibre-optic hot-spot monitor (5)<br>Bushing monitor (3)<br>On-load tap-changer (OLTC) monitor (6)<br>UHF / acoustic partial-discharge sensor (4)<br>Cooling system sensor set (5)<br>Mechanical protection devices (6)<br>Load measurement (CT/VT) (7)<br>Tank vibration sensor (3) |
| Distribution Transformers | Smart transformer monitor (9) |
| Dry-type Transformers | Winding temperature controller (6)<br>Partial-discharge sensor (2) |
| Insulation & Components (Bushings, Tap-changers) | Bushing test-tap sensor (5) |
| Instrument Transformers | Instrument transformer health monitor (7) |
| High-Voltage Switchgear & Breakers | Gas density monitor (6)<br>Circuit-breaker operating mechanism monitor (9)<br>GIS UHF partial-discharge sensor (3)<br>Busbar / contact temperature sensor (3) |
| Generator Circuit-Breakers (GCB) | GCB condition monitor (8) |
| Disconnectors | Disconnector drive & contact monitor (6) |
| Surge Arresters | Surge arrester monitor (EXCOUNT type) (5) |
| Capacitors and Filters | Capacitor bank unbalance & thermal monitor (7) |
| Flexible AC Transmission Systems (FACTS) | FACTS control & measurement (6)<br>Valve thermal & cooling sensors (4) |
| High-Voltage Direct Current (HVDC) | Converter station measurement (8)<br>Valve hall & valve monitoring (6)<br>DC line / cable monitor (4) |
| Cooling Systems | Pure-water cooling loop sensors (9)<br>Outdoor cooler sensors (3) |
| Energy Storage (BESS) | Battery management system (rack level) (10)<br>Container environment & safety (7) |
| Power Conversion Solutions | Inverter / PCS telemetry (8) |
| Static Frequency Converters | SFC converter telemetry (5) |
| Power Semiconductors | IGBT module condition sensors (7) |
| Substation Automation, Protection & Control | Protection relay (IED) measurements (7)<br>IED / merging unit self-supervision (6) |
| Communication Networks | Network node telemetry (7) |
| Cable Accessories | Cable joint / termination monitor (5) |
| Substations & Electrification | Substation environment & auxiliary supply (7) |
| Grid-eMotion® (EV fleet charging) | Charging point telemetry (6) |
| Power Quality | Power-quality analyser (IEC 61000-4-30 Class A) (7) |

Excluded: software/service offerings (Asset & Work Management, Energy Portfolio Management,
Network Control, Cybersecurity, Digitalization, Consulting) — they consume sensor data rather than produce it.

## Adding a product or sensor

Append to `PRODUCTS` in `backend/app/catalog.py`, e.g.

```python
SensorSpec(id="my-sensor", name="My sensor", description="...", principle="...", protocol="Modbus TCP",
           sample_interval_s=60,
           fields=[num("temperature", "°C", -40, 120, 55, "Oil temperature", 1),
                   enum("state", {"OK": 0.98, "ALARM": 0.02}, "Status")])
```
The UI, mock endpoint and code panel pick it up automatically; `pytest` checks the ranges.
