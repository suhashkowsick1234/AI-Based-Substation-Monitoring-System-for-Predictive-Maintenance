

# ✅ STEP 1 - Make Sure All Core Services Are Running

## 1️⃣ Check Docker Containers

Run:

```bash
docker ps
```

You must see:

* substationproject-kafka-1
* substationproject-zookeeper-1
* substationproject-cassandra-1

If yes → infrastructure OK.

---

### 2️⃣ Check Consumer Engine

Make sure this is running in another terminal:

```bash
python consumer_engine.py
```

You should see:

```
Consumer running...
```

Leave it running.

---

### 3️⃣ Check Producer Gateway

In another terminal:

```bash
uvicorn producer_gateway:app --reload
```

This runs on:

```
http://127.0.0.1:8000
```

Leave it running.

---

# ✅ STEP 2 — Send Test Sensor Data

Open a new terminal.

Run:

```bash
curl -X POST http://127.0.0.1:8000/data ^
-H "Content-Type: application/json" ^
-d "{\"temperature\":35,\"humidity\":60,\"vibration\":1.5,\"voltage\":230,\"timestamp\":123456}"
```

Expected response:

```json
{"status":"sent to kafka"}
```

Now look at your consumer terminal.

You should see something like:

```
Stored: {...} Anomaly: False
```

If you see that → data successfully reached Cassandra.

---

# ✅ STEP 3 — Start API Server

Open another terminal:

```bash
uvicorn api_server:app --reload
```

It runs at:

```
http://127.0.0.1:8001
```

⚠ Important:
If producer is using port 8000, API cannot also use 8000.

If needed run API like this:

```bash
uvicorn api_server:app --reload --port 8001
```

---

# ✅ STEP 4 — Check /latest Endpoint

Open browser:

```
http://127.0.0.1:8001/latest
```

You should see JSON like:

```json
{
  "temperature": 35.0,
  "humidity": 60.0,
  "vibration": 1.5,
  "voltage": 230.0,
  "anomaly": false
}
```

If you see this → FULL BACKEND PIPELINE VERIFIED.

---

# 🔎 If It Shows

| Case           | Meaning                                |
| -------------- | -------------------------------------- |
| "no data"      | Cassandra empty → send test data again |
| Error 500      | DB connection issue                    |
| Empty response | Consumer not storing                   |

---

# 🧠 Quick Architecture Debug Logic

If `/latest` doesn’t show data, check in this order:

1. Producer sending?
2. Kafka receiving?
3. Consumer printing "Stored"?
4. Cassandra storing?
5. API querying correct keyspace?

Distributed systems are always debugged layer by layer.

