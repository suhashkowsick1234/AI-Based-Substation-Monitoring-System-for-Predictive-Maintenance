"""
simulator.py
-------------
IoT Sensor Data Simulator for Substation Monitoring System.

Sends realistic sensor readings to the Producer Gateway every 2 seconds.
Periodically injects artificial anomalies to test the anomaly detection pipeline.

Anomaly injection schedule (every 20th reading):
  - Cycle 1 : Overheating transformer  (temperature spike)
  - Cycle 2 : Voltage surge             (voltage out of range)
  - Cycle 3 : Vibration fault           (vibration spike)
  - Cycle 4 : Humidity ingress          (humidity spike)
  - Cycle 5 : Combined fault            (temperature + voltage)

Usage:
    python simulator.py                          # default: infinite loop, 2s interval
    python simulator.py --interval 1 --count 100 # 100 readings, 1s apart
"""

import requests
import time
import random
import math
import argparse
import datetime

# ─────────────────────────────────────────
# Config
# ─────────────────────────────────────────
PRODUCER_URL   = "http://127.0.0.1:8000/data"
ANOMALY_EVERY  = 20          # inject an anomaly every N readings
RETRY_DELAY    = 3           # seconds to wait if producer is unreachable


# ─────────────────────────────────────────
# Normal operating ranges (IEEE substation specs)
# ─────────────────────────────────────────
NORMAL = {
    "temperature": {"mean": 55,   "std": 10,  "low": 20,   "high": 85},
    "vibration":   {"mean": 1.2,  "std": 0.4, "low": 0.1,  "high": 3.0},
    "voltage":     {"mean": 225,  "std": 7,   "low": 210,  "high": 240},
    "humidity":    {"mean": 50,   "std": 10,  "low": 25,   "high": 75},
}


def normal_reading(tick: int) -> dict:
    """Generate one realistic normal sensor reading with slight sinusoidal drift."""
    # Add gentle time-of-day drift to make time-series graphs look realistic
    temp_drift  = 5 * math.sin(tick * 0.1)         # ±5 °C slow oscillation
    volt_drift  = 3 * math.cos(tick * 0.07)         # ±3 V slow oscillation

    return {
        "temperature": round(random.gauss(NORMAL["temperature"]["mean"] + temp_drift, NORMAL["temperature"]["std"]), 2),
        "vibration":   round(abs(random.gauss(NORMAL["vibration"]["mean"],  NORMAL["vibration"]["std"])), 3),
        "voltage":     round(random.gauss(NORMAL["voltage"]["mean"] + volt_drift, NORMAL["voltage"]["std"]), 2),
        "humidity":    round(random.gauss(NORMAL["humidity"]["mean"],  NORMAL["humidity"]["std"]), 2),
        "timestamp":   time.time(),
    }


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def apply_clamps(d: dict) -> dict:
    """Clamp normal readings to realistic physical limits."""
    d["temperature"] = clamp(d["temperature"], 18,  90)
    d["vibration"]   = clamp(d["vibration"],   0.05, 3.2)
    d["voltage"]     = clamp(d["voltage"],      205, 242)
    d["humidity"]    = clamp(d["humidity"],      20,  78)
    return d


# ─────────────────────────────────────────
# Anomaly injection modes
# ─────────────────────────────────────────
def anomaly_reading(cycle: int, tick: int) -> dict:
    """Inject a specific type of anomaly based on the cycle counter."""
    base = apply_clamps(normal_reading(tick))

    kind = cycle % 5

    if kind == 0:
        # Overheating transformer
        base["temperature"] = round(random.uniform(96, 130), 2)
        label = "OVERHEAT"
    elif kind == 1:
        # Voltage surge
        base["voltage"] = round(random.uniform(247, 265), 2)
        label = "VOLT_SURGE"
    elif kind == 2:
        # Vibration fault (bearing wear)
        base["vibration"] = round(random.uniform(4.0, 8.5), 3)
        label = "VIB_FAULT"
    elif kind == 3:
        # Moisture/humidity ingress
        base["humidity"] = round(random.uniform(88, 98), 2)
        label = "MOISTURE"
    else:
        # Combined: overheat + voltage sag (worst case)
        base["temperature"] = round(random.uniform(98, 120), 2)
        base["voltage"]     = round(random.uniform(180, 204), 2)
        label = "COMBINED"

    return base, label


# ─────────────────────────────────────────
# Sender
# ─────────────────────────────────────────
def send(payload: dict) -> bool:
    """POST payload to producer. Returns True on success."""
    try:
        r = requests.post(PRODUCER_URL, json=payload, timeout=4)
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


# ─────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────
def run(interval: float, count: int):
    print("=" * 60)
    print("  ⚡  Substation IoT Simulator")
    print(f"  Target  : {PRODUCER_URL}")
    print(f"  Interval: {interval}s  |  Count: {'∞' if count == 0 else count}")
    print(f"  Anomaly : every {ANOMALY_EVERY} readings")
    print("=" * 60)

    tick         = 0
    anomaly_cycle = 0
    sent_ok      = 0
    sent_fail    = 0

    while True:
        tick += 1

        is_anomaly = (tick % ANOMALY_EVERY == 0)

        if is_anomaly:
            payload, label = anomaly_reading(anomaly_cycle, tick)
            anomaly_cycle += 1
        else:
            payload = apply_clamps(normal_reading(tick))
            label   = None

        ok = send(payload)

        ts = datetime.datetime.now().strftime("%H:%M:%S")

        if ok:
            sent_ok += 1
            if label:
                print(
                    f"[{ts}] #{tick:04d}  🔴 ANOMALY ({label:<12})  "
                    f"T={payload['temperature']:.1f}°C  "
                    f"Vib={payload['vibration']:.2f}  "
                    f"V={payload['voltage']:.1f}V  "
                    f"H={payload['humidity']:.1f}%"
                )
            else:
                print(
                    f"[{ts}] #{tick:04d}  🟢 NORMAL               "
                    f"T={payload['temperature']:.1f}°C  "
                    f"Vib={payload['vibration']:.2f}  "
                    f"V={payload['voltage']:.1f}V  "
                    f"H={payload['humidity']:.1f}%"
                )
        else:
            sent_fail += 1
            print(f"[{ts}] #{tick:04d}  ⚠  Producer unreachable — retrying in {RETRY_DELAY}s …")
            time.sleep(RETRY_DELAY)
            continue

        if count and tick >= count:
            print(f"\n✅  Done. Sent {sent_ok} OK / {sent_fail} failed.")
            break

        time.sleep(interval)


# ─────────────────────────────────────────
# CLI entry
# ─────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Substation IoT Sensor Simulator")
    parser.add_argument("--interval", type=float, default=2.0,  help="Seconds between readings (default: 2)")
    parser.add_argument("--count",    type=int,   default=0,    help="Number of readings to send; 0 = infinite (default: 0)")
    args = parser.parse_args()

    try:
        run(args.interval, args.count)
    except KeyboardInterrupt:
        print("\n🛑  Simulator stopped by user.")
