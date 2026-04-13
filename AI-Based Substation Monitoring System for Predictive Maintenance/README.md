# Real-time Substation Condition Monitoring System for Predictive Maintenance in Power Grids

# Team Name : Byte Hogs
# Team ID : 26E4249
### Predictive Maintenance in Power Grids

A full-stack IoT monitoring system that simulates substation sensor data, detects anomalies using Machine Learning (IsolationForest), stores results in Apache Cassandra via Kafka, and displays live readings on a React dashboard.

--

### System Architecture

```
[simulator.py]
  IoT Sensor Simulator
       │
       │  HTTP POST /data
       ▼
[producer_gateway.py]          ← FastAPI on :8000
  Kafka Producer Gateway
       │
       │  Kafka Topic: sensor-topic
       ▼
[Apache Kafka :9092]
       │
       ▼
[consumer_engine.py]
  ML Anomaly Detection           ← IsolationForest (model.pkl)
  Severity: CRITICAL/WARNING/NORMAL
       │
       │  INSERT
       ▼
[Apache Cassandra :9042]
  substation.sensor_data
       │
       ▼
[api_server.py]                 ← FastAPI on :8001
  REST API
       │
       │  HTTP GET
       ▼
[React Dashboard :3000]
  Live Charts + Alert Panel
```

---

## Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| **Docker Desktop** | Latest | https://www.docker.com/products/docker-desktop |
| **Python** | 3.9 + | https://www.python.org/downloads |
| **Node.js + npm** | 18 + | https://nodejs.org |
| **Git** | Any | https://git-scm.com |

> Make sure Docker Desktop is **running** before you proceed.

---

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Hushh72s/Real-time-Substation-Condition-Monitoring-System-for-Predictive-Maintenance-in-Power-Grids.git
cd Real-time-Substation-Condition-Monitoring-System-for-Predictive-Maintenance-in-Power-Grids
```

---

### 2. Start Infrastructure (Kafka + Cassandra)

```bash
docker compose up -d
```

This starts:
- **Zookeeper** (Kafka dependency)
- **Apache Kafka** on port `9092`
- **Apache Cassandra** on port `9042`

Wait ~30–60 seconds for Cassandra to fully initialize before the next step.

**Verify containers are running:**
```bash
docker ps
```
You should see 3 containers: `zookeeper`, `kafka`, `cassandra`.

---

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Train the ML Model

```bash
cd services
python model_trainer.py
```

Expected output:
```
Training IsolationForest on 4200 samples …
✅  Model saved to model.pkl
   Normal correctly classified  : 99.3%
   Anomaly correctly classified : 91.0%
```

---

### 5. Start the Producer Gateway

Open a **new terminal** inside the `services/` folder:

```bash
cd services
uvicorn producer_gateway:app --host 0.0.0.0 --port 8000 --reload
```

Runs at: http://127.0.0.1:8000

---

### 6. Start the Kafka Consumer + ML Engine

Open another **new terminal** inside `services/`:

```bash
cd services
python consumer_engine.py
```

Expected output:
```
Connecting to Cassandra …
✅  Cassandra ready.
✅  ML model loaded from model.pkl
🚀  Consumer running … (Ctrl-C to stop)
```

---

### 7. Start the REST API Server

Open another **new terminal** inside `services/`:

```bash
cd services
uvicorn api_server:app --host 0.0.0.0 --port 8001 --reload
```

Runs at: http://127.0.0.1:8001

**API Docs (Swagger UI):** http://127.0.0.1:8001/docs

---

### 8. Start the IoT Simulator

Open another **new terminal** inside `services/`:

```bash
cd services
python simulator.py
```

This sends a sensor reading every 2 seconds and injects an anomaly every 20th reading.

Expected output:
```
[15:20:01] #0001  🟢 NORMAL               T=58.3°C  Vib=1.14  V=228.4V  H=47.2%
[15:20:03] #0002  🟢 NORMAL               T=61.7°C  Vib=0.98  V=224.1V  H=52.1%
...
[15:20:41] #0020  🔴 ANOMALY (OVERHEAT  ) T=113.2°C  Vib=1.22  V=226.3V  H=49.8%
```

**Options:**
```bash
python simulator.py --interval 1       # send every 1 second
python simulator.py --count 50         # send only 50 readings then stop
python simulator.py --interval 0.5 --count 100
```

---

### 9. Start the React Dashboard

Open a **new terminal** inside the `frontend/` folder:

```bash
cd frontend
npm install
npm start
```

Opens automatically at: **http://localhost:3000**

---

## API Endpoints

Base URL: `http://127.0.0.1:8001`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | API + Cassandra health status |
| `/latest` | GET | Most recent sensor reading |
| `/history?limit=50` | GET | Last N readings (max 200) |
| `/alerts?limit=20` | GET | Only anomalous rows, newest first |
| `/stats` | GET | Avg / Min / Max for all parameters |
| `/severity` | GET | Count of CRITICAL / WARNING / NORMAL |

Full interactive docs: http://127.0.0.1:8001/docs

---

## Running everything

You need **5 terminals** open simultaneously:

```
Terminal 1  →  docker compose up -d           (run once, stays in background)
Terminal 2  →  uvicorn producer_gateway:app --port 8000 --reload
Terminal 3  →  python consumer_engine.py
Terminal 4  →  uvicorn api_server:app --port 8001 --reload
Terminal 5  →  python simulator.py
+ Browser   →  npm start  (from frontend/)
```

---

## Stopping Everything

```bash
# Stop Python services: Ctrl+C in each terminal

# Stop Docker containers
docker compose down
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Waiting for Cassandra …` loops forever | Wait 60s after `docker compose up -d`, then restart consumer |
| `Connection refused` on port 9092 | Kafka not ready yet — wait 30s and retry |
| `model.pkl not found` | Run `python model_trainer.py` first |
| React shows no data | Make sure simulator and api_server are both running |
| `pip install` fails | Use `pip install -r requirements.txt --user` or create a venv |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| IoT Simulation | Python (`simulator.py`) |
| Message Broker | Apache Kafka + Zookeeper |
| ML / Anomaly Detection | scikit-learn IsolationForest |
| Database | Apache Cassandra |
| Backend API | FastAPI + Uvicorn |
| Frontend | React + Chart.js |
| Infrastructure | Docker Compose |
