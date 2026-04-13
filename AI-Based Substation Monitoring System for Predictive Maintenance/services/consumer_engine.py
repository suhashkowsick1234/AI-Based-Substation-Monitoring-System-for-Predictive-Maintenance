"""
consumer_engine.py
-------------------
Kafka consumer that:
  1. Reads sensor data from the 'sensor-topic' Kafka topic
  2. Runs IsolationForest anomaly detection (model.pkl)
  3. Classifies severity: CRITICAL / WARNING / NORMAL
  4. Persists results to Apache Cassandra (substation.sensor_data)

Run AFTER starting Docker services and model_trainer.py:
    python consumer_engine.py
"""

from kafka import KafkaConsumer
import json
import time
import datetime
from cassandra.cluster import Cluster
import numpy as np
import joblib

DEVICE_ID = "substation-1"   # logical device name used as partition key

# ─────────────────────────────────────────────
# Thresholds for rule-based severity override
# (IsolationForest catches statistical outliers;
#  rule-based catches domain-specific extremes)
# ─────────────────────────────────────────────
THRESHOLDS = {
    "temperature": {"warning": 85,  "critical": 95},
    "vibration":   {"warning": 3.5, "critical": 4.5},
    "voltage_low": {"warning": 208, "critical": 205},
    "voltage_high":{"warning": 242, "critical": 246},
    "humidity":    {"warning": 80,  "critical": 88},
}

def classify_severity(d: dict, is_anomaly: bool) -> str:
    """
    Returns 'CRITICAL', 'WARNING', or 'NORMAL'.
    Rule-based thresholds take priority over the ML prediction.
    """
    temp  = d["temperature"]
    vib   = d["vibration"]
    volt  = d["voltage"]
    humid = d["humidity"]

    # Critical rules
    if (temp  >= THRESHOLDS["temperature"]["critical"]  or
        vib   >= THRESHOLDS["vibration"]["critical"]    or
        volt  <= THRESHOLDS["voltage_low"]["critical"]  or
        volt  >= THRESHOLDS["voltage_high"]["critical"] or
        humid >= THRESHOLDS["humidity"]["critical"]):
        return "CRITICAL"

    # Warning rules
    if (temp  >= THRESHOLDS["temperature"]["warning"]  or
        vib   >= THRESHOLDS["vibration"]["warning"]    or
        volt  <= THRESHOLDS["voltage_low"]["warning"]  or
        volt  >= THRESHOLDS["voltage_high"]["warning"] or
        humid >= THRESHOLDS["humidity"]["warning"]):
        return "WARNING"

    # ML anomaly without breaching hard thresholds → soft warning
    if is_anomaly:
        return "WARNING"

    return "NORMAL"


# ─────────────────────────────────────────────
# Cassandra Connection
# ─────────────────────────────────────────────
print("Connecting to Cassandra …")
while True:
    try:
        cluster = Cluster(["127.0.0.1"])
        session = cluster.connect()
        break
    except Exception:
        print("  Waiting for Cassandra …")
        time.sleep(5)

session.execute("""
    CREATE KEYSPACE IF NOT EXISTS substation
    WITH replication = {'class':'SimpleStrategy','replication_factor':1};
""")
session.set_keyspace("substation")

# ── Schema migration: drop old UUID-keyed table if it exists ──────────────
# The old table had no ordering, so LIMIT 1 never returned the newest row.
# New schema: (device_id, ts) composite key with CLUSTERING ORDER BY ts DESC
# so that LIMIT 1 always gives the most recent reading.
session.execute("DROP TABLE IF EXISTS sensor_data;")

session.execute("""
    CREATE TABLE sensor_data (
        device_id   text,
        ts          timestamp,
        temperature float,
        humidity    float,
        vibration   float,
        voltage     float,
        anomaly     boolean,
        severity    text,
        PRIMARY KEY (device_id, ts)
    ) WITH CLUSTERING ORDER BY (ts DESC);
""")
print("✅  Cassandra ready (schema v2 — ordered by ts DESC).")

# ─────────────────────────────────────────────
# Load ML Model
# ─────────────────────────────────────────────
try:
    model = joblib.load("model.pkl")
    print("✅  ML model loaded from model.pkl")
except FileNotFoundError:
    print("⚠  model.pkl not found — run model_trainer.py first!")
    raise

# ─────────────────────────────────────────────
# Kafka Consumer
# ─────────────────────────────────────────────
consumer = KafkaConsumer(
    "sensor-topic",
    bootstrap_servers="localhost:9092",
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    auto_offset_reset="latest",
    enable_auto_commit=True,
)

print("🚀  Consumer running … (Ctrl-C to stop)")
print("-" * 60)

for msg in consumer:
    d = msg.value

    # ── ML Prediction ──────────────────────────────────────────
    X = [[
        d["temperature"],
        d["humidity"],
        d["vibration"],
        d["voltage"],
    ]]
    pred    = model.predict(X)[0]
    score   = round(float(model.score_samples(X)[0]), 4)  # anomaly score
    anomaly = pred == -1

    # ── Severity Classification ────────────────────────────────
    severity = classify_severity(d, anomaly)

    # ── Timestamp ─────────────────────────────────────────────
    ts_now = datetime.datetime.utcnow()

    # ── Persist to Cassandra ───────────────────────────────────
    session.execute("""
        INSERT INTO sensor_data
            (device_id, ts, temperature, humidity, vibration, voltage, anomaly, severity)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        DEVICE_ID,
        ts_now,
        d["temperature"],
        d["humidity"],
        d["vibration"],
        d["voltage"],
        anomaly,
        severity,
    ))

    # ── Console Log ────────────────────────────────────────────
    flag = "🔴 CRITICAL" if severity == "CRITICAL" else ("🟡 WARNING" if severity == "WARNING" else "🟢 NORMAL")
    print(
        f"[{ts_now.strftime('%H:%M:%S')}] {flag}  "
        f"T={d['temperature']:.1f}°C  "
        f"V={d['vibration']:.2f}mm/s  "
        f"V={d['voltage']:.1f}V  "
        f"H={d['humidity']:.1f}%  "
        f"score={score}"
    )
