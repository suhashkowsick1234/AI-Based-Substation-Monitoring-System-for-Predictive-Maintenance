"""
api_server.py
--------------
FastAPI REST API that serves sensor data stored in Apache Cassandra.

Endpoints:
  GET /health    → Server + Cassandra health check
  GET /latest    → Most recent sensor reading
  GET /history   → Last N readings  (query param: limit, default 50)
  GET /alerts    → Only anomalous rows (query param: limit, default 20)
  GET /stats     → Aggregate stats (avg / min / max) for all parameters
  GET /severity  → Count of CRITICAL / WARNING / NORMAL from last 100 rows

Run:
    uvicorn api_server:app --host 0.0.0.0 --port 8001 --reload
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from cassandra.cluster import Cluster
from cassandra import ReadTimeout
import time
import datetime

DEVICE_ID = "substation-1"

# ─────────────────────────────────────────────
# App Init
# ─────────────────────────────────────────────
app = FastAPI(
    title="Substation Monitoring API",
    description="Real-time sensor data, anomaly alerts, and statistics for substation equipment.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Cassandra Connection (with retry)
# ─────────────────────────────────────────────
connected = False
while not connected:
    try:
        cluster = Cluster(["127.0.0.1"])
        session = cluster.connect("substation")
        connected = True
        print("✅  Connected to Cassandra")
    except Exception:
        print("   Waiting for Cassandra …")
        time.sleep(5)

# ─────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────
def row_to_dict(r) -> dict:
    """Convert a Cassandra Row to a JSON-serialisable dict."""
    d = dict(r._asdict())
    # Convert cassandra Datetime → ISO string so JSON can serialize it
    if "ts" in d and d["ts"] is not None:
        if isinstance(d["ts"], datetime.datetime):
            d["ts"] = d["ts"].isoformat() + "Z"
    return d


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@app.get("/health", tags=["Meta"])
def health():
    """Returns API and Cassandra connectivity status."""
    try:
        session.execute("SELECT now() FROM system.local")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"
    return {
        "api": "online",
        "cassandra": db_status,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }


@app.get("/latest", tags=["Sensor Data"])
def latest():
    """Returns the single most recent sensor reading."""
    rows = session.execute(
        "SELECT * FROM sensor_data WHERE device_id = %s LIMIT 1",
        (DEVICE_ID,)
    )
    for r in rows:
        return row_to_dict(r)
    return {"msg": "no data yet"}


@app.get("/history", tags=["Sensor Data"])
def history(limit: int = Query(default=50, ge=1, le=200, description="Number of rows to return")):
    """Returns the last N sensor readings (default 50, max 200)."""
    rows = session.execute(
        "SELECT * FROM sensor_data WHERE device_id = %s LIMIT %s",
        (DEVICE_ID, limit)
    )
    return [row_to_dict(r) for r in rows]


@app.get("/alerts", tags=["Alerts"])
def alerts(limit: int = Query(default=20, ge=1, le=100, description="Number of alert rows to return")):
    """Returns only anomalous readings (anomaly=true), most recent first."""
    rows = session.execute(
        "SELECT * FROM sensor_data WHERE device_id = %s LIMIT 200",
        (DEVICE_ID,)
    )
    anomalies = [row_to_dict(r) for r in rows if r.anomaly]
    return anomalies[:limit]


@app.get("/stats", tags=["Analytics"])
def stats():
    """Returns aggregate statistics (avg, min, max) across all stored readings."""
    rows = session.execute(
        "SELECT temperature, humidity, vibration, voltage FROM sensor_data WHERE device_id = %s LIMIT 1000",
        (DEVICE_ID,)
    )
    data = list(rows)

    if not data:
        return {"msg": "no data yet"}

    def agg(field):
        vals = [getattr(r, field) for r in data if getattr(r, field) is not None]
        if not vals:
            return {"avg": None, "min": None, "max": None, "count": 0}
        return {
            "avg": round(sum(vals) / len(vals), 2),
            "min": round(min(vals), 2),
            "max": round(max(vals), 2),
            "count": len(vals),
        }

    return {
        "sample_size": len(data),
        "temperature":  agg("temperature"),
        "humidity":     agg("humidity"),
        "vibration":    agg("vibration"),
        "voltage":      agg("voltage"),
        "computed_at":  datetime.datetime.utcnow().isoformat() + "Z",
    }


@app.get("/severity", tags=["Analytics"])
def severity_summary():
    """Returns a count breakdown of CRITICAL / WARNING / NORMAL from the last 100 rows."""
    rows = session.execute(
        "SELECT severity, anomaly FROM sensor_data WHERE device_id = %s LIMIT 100",
        (DEVICE_ID,)
    )
    counts = {"CRITICAL": 0, "WARNING": 0, "NORMAL": 0}
    total = 0
    for r in rows:
        sev = r.severity if r.severity in counts else "NORMAL"
        counts[sev] += 1
        total += 1

    return {
        "total_sampled": total,
        "CRITICAL": counts["CRITICAL"],
        "WARNING":  counts["WARNING"],
        "NORMAL":   counts["NORMAL"],
        "anomaly_rate_pct": round(
            (counts["CRITICAL"] + counts["WARNING"]) / total * 100, 1
        ) if total else 0,
    }