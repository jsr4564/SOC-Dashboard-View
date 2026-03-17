import { useEffect, useMemo, useRef, useState } from "react";
import { Chart } from "chart.js/auto";

const API_BASE = import.meta.env.VITE_API_BASE || "";
const joinUrl = (base, path) => (base ? `${base.replace(/\/$/, "")}${path}` : path);

const wsBase = API_BASE
  ? API_BASE.replace(/^http/, "ws").replace(/\/$/, "")
  : `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;

export default function App() {
  const [summary, setSummary] = useState(null);
  const [timeline, setTimeline] = useState({ logs: [], alerts: [] });
  const [alerts, setAlerts] = useState([]);
  const [connection, setConnection] = useState("connecting");
  const [authEnabled, setAuthEnabled] = useState(false);
  const [token, setToken] = useState(null);
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [loginError, setLoginError] = useState("");

  const logsChartRef = useRef(null);
  const alertsChartRef = useRef(null);
  const logsChart = useRef(null);
  const alertsChart = useRef(null);

  const apiHeaders = useMemo(() => {
    const headers = { "Content-Type": "application/json" };
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    return headers;
  }, [token]);

  async function fetchJSON(path) {
    const response = await fetch(joinUrl(API_BASE, path), { headers: apiHeaders });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    return response.json();
  }

  async function loadConfig() {
    const config = await fetchJSON("/api/auth/config");
    setAuthEnabled(config.auth_enabled);
  }

  async function loadSummary() {
    const data = await fetchJSON("/api/metrics/summary");
    setSummary(data);
  }

  async function loadTimeline() {
    const data = await fetchJSON("/api/metrics/timeline?minutes=120");
    setTimeline(data);
  }

  async function loadAlerts() {
    const data = await fetchJSON("/api/alerts?limit=200");
    setAlerts(data);
  }

  async function loadAll() {
    await Promise.all([loadSummary(), loadTimeline(), loadAlerts()]);
  }

  async function handleLogin(event) {
    event.preventDefault();
    setLoginError("");
    try {
      const response = await fetch(joinUrl(API_BASE, "/api/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(loginForm),
      });
      if (!response.ok) {
        throw new Error("Invalid credentials");
      }
      const data = await response.json();
      setToken(data.access_token);
    } catch (err) {
      setLoginError("Login failed. Check credentials.");
    }
  }

  useEffect(() => {
    loadConfig();
  }, []);

  useEffect(() => {
    if (authEnabled && !token) {
      return;
    }
    loadAll();
    const interval = setInterval(() => {
      loadSummary();
      loadTimeline();
    }, 10000);
    return () => clearInterval(interval);
  }, [authEnabled, token]);

  useEffect(() => {
    if (authEnabled && !token) {
      return;
    }
    const ws = new WebSocket(`${wsBase}/ws/alerts`);
    ws.onopen = () => setConnection("live");
    ws.onclose = () => setConnection("offline");
    ws.onerror = () => setConnection("offline");
    ws.onmessage = (event) => {
      try {
        const alert = JSON.parse(event.data);
        setAlerts((current) => [alert, ...current].slice(0, 200));
        loadSummary();
        loadTimeline();
      } catch (err) {
        // ignore malformed payloads
      }
    };
    return () => ws.close();
  }, [authEnabled, token]);

  useEffect(() => {
    if (!timeline.logs.length || !logsChartRef.current) {
      return;
    }
    const labels = timeline.logs.map((point) => new Date(point.ts).toLocaleTimeString());
    const logCounts = timeline.logs.map((point) => point.count);
    const alertCounts = timeline.alerts.map((point) => point.count);

    if (!logsChart.current) {
      logsChart.current = new Chart(logsChartRef.current, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: "Logs",
              data: logCounts,
              borderColor: "#0f8a8a",
              backgroundColor: "rgba(15, 138, 138, 0.2)",
              tension: 0.3,
              fill: true,
            },
          ],
        },
        options: { responsive: true, plugins: { legend: { display: false } } },
      });
    } else {
      logsChart.current.data.labels = labels;
      logsChart.current.data.datasets[0].data = logCounts;
      logsChart.current.update();
    }

    if (!alertsChart.current && alertsChartRef.current) {
      alertsChart.current = new Chart(alertsChartRef.current, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: "Alerts",
              data: alertCounts,
              borderColor: "#c0392b",
              backgroundColor: "rgba(192, 57, 43, 0.2)",
              tension: 0.3,
              fill: true,
            },
          ],
        },
        options: { responsive: true, plugins: { legend: { display: false } } },
      });
    } else if (alertsChart.current) {
      alertsChart.current.data.labels = labels;
      alertsChart.current.data.datasets[0].data = alertCounts;
      alertsChart.current.update();
    }

    return () => {
      logsChart.current?.destroy();
      alertsChart.current?.destroy();
      logsChart.current = null;
      alertsChart.current = null;
    };
  }, [timeline]);

  const severitySummary = summary?.alerts_by_severity || {};

  return (
    <div>
      <header>
        <h1>SOC Tracker</h1>
        <p>Live SOC telemetry, detections, and alerting for training environments.</p>
        <div className="status">
          <span
            className="dot"
            style={{ background: connection === "live" ? "#2e8b57" : "#c0392b" }}
          />
          <span>{connection === "live" ? "Alert stream connected" : "Alert stream offline"}</span>
        </div>
        {authEnabled && !token && (
          <form className="login" onSubmit={handleLogin}>
            <input
              type="text"
              placeholder="Username"
              value={loginForm.username}
              onChange={(event) =>
                setLoginForm({ ...loginForm, username: event.target.value })
              }
            />
            <input
              type="password"
              placeholder="Password"
              value={loginForm.password}
              onChange={(event) =>
                setLoginForm({ ...loginForm, password: event.target.value })
              }
            />
            <button type="submit">Login</button>
            {loginError && <span style={{ color: "#c0392b" }}>{loginError}</span>}
          </form>
        )}
      </header>

      <main>
        <div className="dashboard">
          <div className="card">
            <h3>Total Logs</h3>
            <div className="value">{summary ? summary.total_logs : "--"}</div>
          </div>
          <div className="card">
            <h3>Active Alerts</h3>
            <div className="value">{summary ? summary.active_alerts : "--"}</div>
          </div>
          <div className="card">
            <h3>High Severity</h3>
            <div className="value">{severitySummary.high || 0}</div>
          </div>
          <div className="card">
            <h3>Medium Severity</h3>
            <div className="value">{severitySummary.medium || 0}</div>
          </div>
          <div className="card">
            <h3>Low Severity</h3>
            <div className="value">{severitySummary.low || 0}</div>
          </div>
        </div>

        <div className="grid-2">
          <div className="panel">
            <h2>Logs Over Time</h2>
            <canvas ref={logsChartRef} height="160" />
          </div>
          <div className="panel">
            <h2>Alerts Over Time</h2>
            <canvas ref={alertsChartRef} height="160" />
          </div>
        </div>

        <div className="panel">
          <h2>Latest Alerts</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>IP</th>
                <th>Type</th>
                <th>Severity</th>
              </tr>
            </thead>
            <tbody>
              {alerts.slice(0, 50).map((alert) => (
                <tr key={alert.id}>
                  <td>{new Date(alert.timestamp).toLocaleString()}</td>
                  <td>{alert.ip || "-"}</td>
                  <td>{alert.alert_type}</td>
                  <td>
                    <span className={`tag ${alert.severity}`}>{alert.severity}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
