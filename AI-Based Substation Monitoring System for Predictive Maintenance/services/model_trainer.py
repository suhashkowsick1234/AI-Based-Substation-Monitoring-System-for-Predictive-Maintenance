"""
model_trainer.py
-----------------
Trains an IsolationForest anomaly detection model on realistic synthetic
substation sensor data and saves it to model.pkl.

Sensor parameter normal operating ranges (based on IEEE/IEC substation specs):
  - temperature  : 20 – 85 °C   (anomaly threshold > 90 °C)
  - vibration    : 0.1 – 3.0 mm/s (anomaly threshold > 3.8 mm/s)
  - voltage      : 210 – 240 V   (anomaly threshold < 205 V or > 245 V)
  - humidity     : 25 – 75 %RH   (anomaly threshold > 85 %RH)

Run this script once before starting the consumer:
    python model_trainer.py
"""

import numpy as np
import joblib
from sklearn.ensemble import IsolationForest

RANDOM_SEED = 42
N_NORMAL    = 4000   # normal operating samples
N_ANOMALY   = 200    # realistic anomalous samples (5 %)

np.random.seed(RANDOM_SEED)

# ─────────────────────────────────────────────
# 1. Generate NORMAL operating data
# ─────────────────────────────────────────────
normal_temperature = np.random.normal(loc=55,  scale=12,  size=N_NORMAL).clip(20,  85)
normal_vibration   = np.random.normal(loc=1.2, scale=0.5, size=N_NORMAL).clip(0.1,  3.0)
normal_voltage     = np.random.normal(loc=225, scale=8,   size=N_NORMAL).clip(210, 240)
normal_humidity    = np.random.normal(loc=50,  scale=12,  size=N_NORMAL).clip(25,  75)

normal_data = np.column_stack([
    normal_temperature,
    normal_vibration,
    normal_voltage,
    normal_humidity,
])

# ─────────────────────────────────────────────
# 2. Generate ANOMALOUS data (overheating, vibration spike, voltage sag/surge, high humidity)
# ─────────────────────────────────────────────
n_each = N_ANOMALY // 4

# Overheating transformer
anom_temp = np.column_stack([
    np.random.uniform(92, 130, n_each),          # temp spike
    np.random.uniform(0.1,  3.0, n_each),
    np.random.uniform(210,  240, n_each),
    np.random.uniform(25,    75, n_each),
])

# Mechanical vibration fault
anom_vib = np.column_stack([
    np.random.uniform(20,  85,  n_each),
    np.random.uniform(4.0, 8.0, n_each),         # vibration spike
    np.random.uniform(210, 240, n_each),
    np.random.uniform(25,   75, n_each),
])

# Voltage sag / surge
anom_volt = np.column_stack([
    np.random.uniform(20,   85, n_each),
    np.random.uniform(0.1,  3.0, n_each),
    np.concatenate([
        np.random.uniform(180, 204, n_each // 2),   # sag
        np.random.uniform(246, 260, n_each // 2),   # surge
    ]),
    np.random.uniform(25, 75, n_each),
])

# High humidity (moisture ingress)
anom_hum = np.column_stack([
    np.random.uniform(20,   85, n_each),
    np.random.uniform(0.1,  3.0, n_each),
    np.random.uniform(210,  240, n_each),
    np.random.uniform(87,   100, n_each),           # humidity spike
])

anomaly_data = np.vstack([anom_temp, anom_vib, anom_volt, anom_hum])

# ─────────────────────────────────────────────
# 3. Combine and train IsolationForest
# ─────────────────────────────────────────────
training_data = np.vstack([normal_data, anomaly_data])

model = IsolationForest(
    n_estimators=200,
    contamination=0.05,   # ~5 % anomalies in real substations
    random_state=RANDOM_SEED,
    max_samples="auto",
)

print("Training IsolationForest on", len(training_data), "samples …")
model.fit(training_data)

joblib.dump(model, "model.pkl")
print("✅  Model saved to model.pkl")

# ─────────────────────────────────────────────
# 4. Quick sanity check
# ─────────────────────────────────────────────
normal_preds  = model.predict(normal_data)
anomaly_preds = model.predict(anomaly_data)

normal_acc  = (normal_preds  == 1).mean() * 100
anomaly_acc = (anomaly_preds == -1).mean() * 100

print(f"   Normal correctly classified  : {normal_acc:.1f}%")
print(f"   Anomaly correctly classified : {anomaly_acc:.1f}%")
