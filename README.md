# 🚀 AI-Based Substation Monitoring System for Predictive Maintenance

> A full-stack **AI-powered IoT monitoring system** that simulates substation sensor data, detects anomalies using Machine Learning (**Isolation Forest**), streams data through **Apache Kafka**, stores results in **Apache Cassandra**, and visualizes real-time insights on a **React dashboard**.

---

## 📌 Table of Contents

- [Overview](#-overview)
- [System Architecture](#️-system-architecture)
- [Tech Stack](#️-tech-stack)
- [Prerequisites](#-prerequisites)
- [Setup & Installation](#-setup--installation)
- [API Endpoints](#-api-endpoints)
- [Running Everything](#️-running-everything)
- [Stopping the System](#-stopping-the-system)
- [Troubleshooting](#-troubleshooting)

---

## 🔍 Overview

This project demonstrates a **complete real-time AI + IoT + distributed systems pipeline**, showcasing a practical implementation of predictive maintenance for power grid substations.

Key capabilities:
- **IoT Simulation** — Generates realistic substation sensor readings
- **Real-time Streaming** — Apache Kafka handles high-throughput event ingestion
- **ML Anomaly Detection** — Isolation Forest classifies severity as `CRITICAL`, `WARNING`, or `NORMAL`
- **Persistent Storage** — Apache Cassandra stores all sensor + inference results
- **Live Dashboard** — React + Chart.js visualizes data and alerts in real time

---

## 🏗️ System Architecture

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
  Severity: CRITICAL / WARNING / NORMAL
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

## 🛠️ Tech Stack

| Layer           | Technology                |
|-----------------|---------------------------|
| IoT Simulation  | Python                    |
| Message Broker  | Apache Kafka + Zookeeper  |
| ML Engine       | Isolation Forest (sklearn)|
| Database        | Apache Cassandra          |
| Backend API     | FastAPI                   |
| Frontend        | React + Chart.js          |
| Infrastructure  | Docker                    |

---

## ⚙️ Prerequisites

Ensure the following are installed before proceeding:

| Tool            | Version  | Download |
|-----------------|----------|----------|
| Docker Desktop  | Latest   | [docker.com](https://www.docker.com/products/docker-desktop) |
| Python          | 3.9+     | [python.org](https://www.python.org/downloads) |
| Node.js + npm   | 18+      | [nodejs.org](https://nodejs.org) |
| Git             | Any      | [git-scm.com](https://git-scm.com) |

> ⚠️ Make sure **Docker Desktop is running** before proceeding.

---

## ⚡ Setup & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/ai-based-substation-monitoring-system.git
cd ai-based-substation-monitoring-system
```

---

### 2. Start Infrastructure (Kafka + Cassandra)

```bash
docker compose up -d
```

This starts:
- Zookeeper
- Apache Kafka (port `9092`)
- Apache Cassandra (port `9042`)

> ⏳ Wait **30–60 seconds** for Cassandra to fully initialize.

Verify containers are running:

```bash
docker ps
```

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

This generates `model.pkl` used by the consumer engine for anomaly detection.

---

### 5. Start the Producer Gateway

```bash
cd services
uvicorn producer_gateway:app --host 0.0.0.0 --port 8000 --reload
```

---

### 6. Start Kafka Consumer + ML Engine

```bash
cd services
python consumer_engine.py
```

---

### 7. Start REST API Server

```bash
cd services
uvicorn api_server:app --host 0.0.0.0 --port 8001 --reload
```

> 📄 Interactive API Docs: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

---

### 8. Start IoT Sensor Simulator

```bash
cd services
python simulator.py
```

---

### 9. Start React Dashboard

```bash
cd frontend
npm install
npm start
```

> 🌐 Dashboard opens at: [http://localhost:3000](http://localhost:3000)

---

## 🌐 API Endpoints

| Endpoint    | Method | Description                    |
|-------------|--------|--------------------------------|
| `/health`   | GET    | API + Cassandra health status  |
| `/latest`   | GET    | Most recent sensor reading     |
| `/history`  | GET    | Last N sensor readings         |
| `/alerts`   | GET    | Anomaly records only           |
| `/stats`    | GET    | Avg / Min / Max sensor values  |
| `/severity` | GET    | Severity level distribution    |

---

## ▶️ Running Everything

You need **5 terminals** open simultaneously:

| Terminal   | Command |
|------------|---------|
| Terminal 1 | `docker compose up -d` |
| Terminal 2 | `uvicorn producer_gateway:app --port 8000 --reload` |
| Terminal 3 | `python consumer_engine.py` |
| Terminal 4 | `uvicorn api_server:app --port 8001 --reload` |
| Terminal 5 | `python simulator.py` |
| Browser    | `npm start` (inside `frontend/`) |

---

## 🛑 Stopping the System

```bash
docker compose down
```

This stops and removes Kafka, Zookeeper, and Cassandra containers.

---

## 🧪 Troubleshooting

| Problem                     | Fix                                         |
|-----------------------------|---------------------------------------------|
| Cassandra not ready         | Wait 60s after `docker compose up`, retry   |
| Kafka connection error      | Wait a moment and restart the service       |
| `model.pkl` not found       | Run `python model_trainer.py` first         |
| No data on React dashboard  | Ensure simulator and API server are running |
| `pip install` fails         | Use a Python virtual environment            |
