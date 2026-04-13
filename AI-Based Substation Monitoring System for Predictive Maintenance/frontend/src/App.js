import React, { useEffect, useState, useRef, useCallback } from "react";
import axios from "axios";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from "chart.js";
import { Line } from "react-chartjs-2";
import "./App.css";

ChartJS.register(
  CategoryScale, LinearScale, PointElement,
  LineElement, Filler, Tooltip, Legend
);

const API = "http://127.0.0.1:8001";
const MAX_POINTS = 30;   // rolling window for charts

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────
function severityOf(reading) {
  if (!reading) return "NORMAL";
  if (reading.severity) return reading.severity;
  return reading.anomaly ? "WARNING" : "NORMAL";
}

function severityColor(sev) {
  if (sev === "CRITICAL") return "var(--red)";
  if (sev === "WARNING")  return "var(--yellow)";
  return "var(--green)";
}

function fmtTime(ts) {
  if (!ts) return "—";
  const d = new Date(ts.endsWith("Z") ? ts : ts + "Z");
  return d.toLocaleTimeString("en-IN", { hour12: false });
}

function fmtVal(v, dec = 1) {
  return v != null ? Number(v).toFixed(dec) : "—";
}

// Build chart.js dataset object
function buildChart(label, data, color, labels) {
  return {
    labels,
    datasets: [{
      label,
      data,
      borderColor: color,
      backgroundColor: color.replace(")", ", 0.08)").replace("rgb", "rgba"),
      borderWidth: 2,
      pointRadius: 2,
      pointHoverRadius: 5,
      fill: true,
      tension: 0.4,
    }],
  };
}

const chartOptions = (yLabel) => ({
  responsive: true,
  maintainAspectRatio: true,
  animation: { duration: 300 },
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: "#131e30",
      borderColor: "rgba(99,179,237,0.2)",
      borderWidth: 1,
      titleColor: "#94a3b8",
      bodyColor: "#e2e8f0",
      padding: 10,
    },
  },
  scales: {
    x: {
      ticks: { color: "#475569", font: { family: "JetBrains Mono", size: 10 }, maxTicksLimit: 6 },
      grid:  { color: "rgba(99,179,237,0.06)" },
    },
    y: {
      ticks: { color: "#475569", font: { family: "JetBrains Mono", size: 10 } },
      grid:  { color: "rgba(99,179,237,0.06)" },
      title: { display: true, text: yLabel, color: "#475569", font: { size: 10 } },
    },
  },
});

// ─────────────────────────────────────────────
// StatCard
// ─────────────────────────────────────────────
function StatCard({ label, icon, value, unit, severity, colorClass }) {
  return (
    <div className={`stat-card ${colorClass}`}>
      <div className="stat-label">{icon} {label}</div>
      <div className="stat-value" style={{ color: severityColor(severity) }}>
        {value}<span className="stat-unit"> {unit}</span>
      </div>
      <span className={`stat-badge ${severity}`}>{severity}</span>
    </div>
  );
}

// ─────────────────────────────────────────────
// AlertTable
// ─────────────────────────────────────────────
function AlertTable({ alerts }) {
  if (!alerts.length) {
    return <div className="no-alerts">✅ No anomalies detected recently</div>;
  }
  return (
    <div className="alert-table-wrap">
      <table className="alert-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Severity</th>
            <th>Temp (°C)</th>
            <th>Vibr (mm/s)</th>
            <th>Voltage (V)</th>
            <th>Humidity (%)</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((a, i) => (
            <tr key={i}>
              <td>{fmtTime(a.ts)}</td>
              <td>
                <span className={`severity-pill ${a.severity || "WARNING"}`}>
                  {a.severity || "ANOMALY"}
                </span>
              </td>
              <td>{fmtVal(a.temperature)}</td>
              <td>{fmtVal(a.vibration, 2)}</td>
              <td>{fmtVal(a.voltage)}</td>
              <td>{fmtVal(a.humidity)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─────────────────────────────────────────────
// SeveritySummary
// ─────────────────────────────────────────────
function SeveritySummary({ sevData }) {
  const total = sevData
    ? (sevData.CRITICAL + sevData.WARNING + sevData.NORMAL) || 1
    : 1;

  const rows = [
    { key: "CRITICAL", label: "Critical" },
    { key: "WARNING",  label: "Warning"  },
    { key: "NORMAL",   label: "Normal"   },
  ];

  return (
    <div className="severity-card">
      <div className="section-title">Severity Breakdown</div>
      <div className="severity-bars">
        {rows.map(({ key, label }) => {
          const count = sevData ? sevData[key] : 0;
          const pct   = Math.round((count / total) * 100);
          return (
            <div className="sev-row" key={key}>
              <div className="sev-meta">
                <span className={`sev-label ${key}`}>{label}</span>
                <span className="sev-count">{count} ({pct}%)</span>
              </div>
              <div className="sev-track">
                <div className={`sev-fill ${key}`} style={{ width: `${pct}%` }} />
              </div>
            </div>
          );
        })}
        {sevData && (
          <div style={{ marginTop: 8, fontSize: 11, color: "var(--text-muted)" }}>
            Anomaly rate:{" "}
            <span style={{ color: sevData.anomaly_rate_pct > 10 ? "var(--red)" : "var(--green)", fontWeight: 600 }}>
              {sevData.anomaly_rate_pct}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// App
// ─────────────────────────────────────────────
export default function App() {
  const [history,   setHistory]   = useState([]);   // rolling 30-point buffer
  const [latest,    setLatest]    = useState(null);
  const [alerts,    setAlerts]    = useState([]);
  const [sevData,   setSevData]   = useState(null);
  const [uptime,    setUptime]    = useState(0);    // seconds
  const [dataCount, setDataCount] = useState(0);
  const [apiOk,     setApiOk]     = useState(true);

  const uptimeRef = useRef(null);

  // Uptime counter
  useEffect(() => {
    uptimeRef.current = setInterval(() => setUptime(s => s + 1), 1000);
    return () => clearInterval(uptimeRef.current);
  }, []);

  // Poll /latest every 2s
  const pollLatest = useCallback(() => {
    axios.get(`${API}/latest`).then(res => {
      const d = res.data;
      setLatest(d);
      setApiOk(true);
      setHistory(prev => {
        const next = [...prev, d];
        return next.slice(-MAX_POINTS);
      });
      setDataCount(c => c + 1);
    }).catch(() => setApiOk(false));
  }, []);

  // Poll /alerts every 5s
  const pollAlerts = useCallback(() => {
    axios.get(`${API}/alerts?limit=10`).then(res => setAlerts(res.data)).catch(() => {});
  }, []);

  // Poll /severity every 8s
  const pollSeverity = useCallback(() => {
    axios.get(`${API}/severity`).then(res => setSevData(res.data)).catch(() => {});
  }, []);

  useEffect(() => {
    pollLatest(); pollAlerts(); pollSeverity();
    const t1 = setInterval(pollLatest,   2000);
    const t2 = setInterval(pollAlerts,   5000);
    const t3 = setInterval(pollSeverity, 8000);
    return () => { clearInterval(t1); clearInterval(t2); clearInterval(t3); };
  }, [pollLatest, pollAlerts, pollSeverity]);

  // Derived
  const severity   = severityOf(latest);
  const labels     = history.map((_, i) => i + 1);

  const tempData  = history.map(d => d.temperature);
  const vibrData  = history.map(d => d.vibration);
  const voltData  = history.map(d => d.voltage);
  const humidData = history.map(d => d.humidity);

  const fmtUptime = () => {
    const m = Math.floor(uptime / 60), s = uptime % 60;
    return `${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}`;
  };

  const bannerClass =
    severity === "CRITICAL" ? "critical" :
    severity === "WARNING"  ? "warning"  : "normal";

  const bannerIcon =
    severity === "CRITICAL" ? "🔴" :
    severity === "WARNING"  ? "🟡" : "🟢";

  const bannerText =
    severity === "CRITICAL" ? "⚠ CRITICAL ALERT — Immediate attention required!" :
    severity === "WARNING"  ? "⚠ WARNING — Anomaly detected, monitoring closely" :
    "✔ All systems operating within normal parameters";

  // Per-param severity for stat cards
  const tempSev  = latest && latest.temperature >= 95  ? "CRITICAL" : latest && latest.temperature >= 85  ? "WARNING" : "NORMAL";
  const vibrSev  = latest && latest.vibration   >= 4.5 ? "CRITICAL" : latest && latest.vibration   >= 3.5 ? "WARNING" : "NORMAL";
  const voltSev  = latest && (latest.voltage <= 205 || latest.voltage >= 246) ? "CRITICAL"
                 : latest && (latest.voltage <= 208 || latest.voltage >= 242) ? "WARNING" : "NORMAL";
  const humidSev = latest && latest.humidity >= 88 ? "CRITICAL" : latest && latest.humidity >= 80 ? "WARNING" : "NORMAL";

  return (
    <div className="dashboard">

      {/* ── Navbar ── */}
      <nav className="navbar">
        <div className="navbar-brand">
          <span className="bolt">⚡</span>
          Substation Monitoring System
        </div>
        <div className="navbar-meta">
          <span><span className="dot-live" /> LIVE</span>
          <span>UPTIME {fmtUptime()}</span>
          <span>READINGS {dataCount}</span>
          <span style={{ color: apiOk ? "var(--green)" : "var(--red)" }}>
            API {apiOk ? "ONLINE" : "OFFLINE"}
          </span>
        </div>
      </nav>

      {/* ── Alert Banner ── */}
      <div className={`alert-banner ${bannerClass}`}>
        <span className="banner-icon">{bannerIcon}</span>
        <span>{bannerText}</span>
      </div>

      <div className="main">

        {/* ── Stat Cards ── */}
        <div className="section-title">Live Sensor Readings</div>
        <div className="stat-grid">
          <StatCard
            label="Temperature" icon="🌡️" colorClass="temp"
            value={fmtVal(latest?.temperature)} unit="°C"
            severity={tempSev}
          />
          <StatCard
            label="Vibration" icon="📳" colorClass="vibr"
            value={fmtVal(latest?.vibration, 2)} unit="mm/s"
            severity={vibrSev}
          />
          <StatCard
            label="Voltage" icon="⚡" colorClass="volt"
            value={fmtVal(latest?.voltage)} unit="V"
            severity={voltSev}
          />
          <StatCard
            label="Humidity" icon="💧" colorClass="humid"
            value={fmtVal(latest?.humidity)} unit="%RH"
            severity={humidSev}
          />
        </div>

        {/* ── Charts ── */}
        <div className="section-title">Real-time Trends (last {MAX_POINTS} readings)</div>
        <div className="charts-grid">
          <div className="chart-card">
            <div className="chart-header">
              <span className="chart-title">
                <span className="chart-dot" style={{ background: "#f97316" }} />
                Temperature
              </span>
              <span className="chart-latest">{fmtVal(latest?.temperature)}°C</span>
            </div>
            <Line data={buildChart("Temperature", tempData, "#f97316", labels)} options={chartOptions("°C")} />
          </div>

          <div className="chart-card">
            <div className="chart-header">
              <span className="chart-title">
                <span className="chart-dot" style={{ background: "#a855f7" }} />
                Vibration
              </span>
              <span className="chart-latest">{fmtVal(latest?.vibration, 2)} mm/s</span>
            </div>
            <Line data={buildChart("Vibration", vibrData, "#a855f7", labels)} options={chartOptions("mm/s")} />
          </div>

          <div className="chart-card">
            <div className="chart-header">
              <span className="chart-title">
                <span className="chart-dot" style={{ background: "#eab308" }} />
                Voltage
              </span>
              <span className="chart-latest">{fmtVal(latest?.voltage)} V</span>
            </div>
            <Line data={buildChart("Voltage", voltData, "#eab308", labels)} options={chartOptions("V")} />
          </div>

          <div className="chart-card">
            <div className="chart-header">
              <span className="chart-title">
                <span className="chart-dot" style={{ background: "#22d3ee" }} />
                Humidity
              </span>
              <span className="chart-latest">{fmtVal(latest?.humidity)}%</span>
            </div>
            <Line data={buildChart("Humidity", humidData, "#22d3ee", labels)} options={chartOptions("%RH")} />
          </div>
        </div>

        {/* ── Bottom Row ── */}
        <div className="section-title">Alert Analysis</div>
        <div className="bottom-grid">
          <SeveritySummary sevData={sevData} />

          <div className="alert-card">
            <div className="section-title">Recent Anomaly Events</div>
            <AlertTable alerts={alerts} />
          </div>
        </div>

      </div>

      {/* ── Footer ── */}
      <div className="footer-bar">
        <span>Real-time Substation Condition Monitoring System v2.0</span>
        <span>Powered by Kafka · Cassandra · IsolationForest · FastAPI · React</span>
      </div>

    </div>
  );
}