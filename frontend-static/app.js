const { useEffect, useMemo, useRef, useState } = React;

function App() {
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
    const response = await fetch(path, { headers: apiHeaders });
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
      const response = await fetch("/api/auth/login", {
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
    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${wsProtocol}://${window.location.host}/ws/alerts`);
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
        // ignore
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
  }, [timeline]);

  const severitySummary = summary?.alerts_by_severity || {};

  return (
    React.createElement("div", null,
      React.createElement("div", { className: "status" },
        React.createElement("span", {
          className: "dot",
          style: { background: connection === "live" ? "#2e8b57" : "#c0392b" },
        }),
        React.createElement("span", null,
          connection === "live" ? "Alert stream connected" : "Alert stream offline"
        )
      ),
      authEnabled && !token && (
        React.createElement("form", { className: "login", onSubmit: handleLogin },
          React.createElement("input", {
            type: "text",
            placeholder: "Username",
            value: loginForm.username,
            onChange: (event) => setLoginForm({ ...loginForm, username: event.target.value }),
          }),
          React.createElement("input", {
            type: "password",
            placeholder: "Password",
            value: loginForm.password,
            onChange: (event) => setLoginForm({ ...loginForm, password: event.target.value }),
          }),
          React.createElement("button", { type: "submit" }, "Login"),
          loginError && React.createElement("span", { style: { color: "#c0392b" } }, loginError)
        )
      ),
      React.createElement("div", { className: "dashboard" },
        React.createElement("div", { className: "card" },
          React.createElement("h3", null, "Total Logs"),
          React.createElement("div", { className: "value" }, summary ? summary.total_logs : "--")
        ),
        React.createElement("div", { className: "card" },
          React.createElement("h3", null, "Active Alerts"),
          React.createElement("div", { className: "value" }, summary ? summary.active_alerts : "--")
        ),
        React.createElement("div", { className: "card" },
          React.createElement("h3", null, "High Severity"),
          React.createElement("div", { className: "value" }, severitySummary.high || 0)
        ),
        React.createElement("div", { className: "card" },
          React.createElement("h3", null, "Medium Severity"),
          React.createElement("div", { className: "value" }, severitySummary.medium || 0)
        ),
        React.createElement("div", { className: "card" },
          React.createElement("h3", null, "Low Severity"),
          React.createElement("div", { className: "value" }, severitySummary.low || 0)
        )
      ),
      React.createElement("div", { className: "grid-2" },
        React.createElement("div", { className: "panel" },
          React.createElement("h2", null, "Logs Over Time"),
          React.createElement("canvas", { ref: logsChartRef, height: 160 })
        ),
        React.createElement("div", { className: "panel" },
          React.createElement("h2", null, "Alerts Over Time"),
          React.createElement("canvas", { ref: alertsChartRef, height: 160 })
        )
      ),
      React.createElement("div", { className: "panel" },
        React.createElement("h2", null, "Latest Alerts"),
        React.createElement("table", { className: "table" },
          React.createElement("thead", null,
            React.createElement("tr", null,
              React.createElement("th", null, "Timestamp"),
              React.createElement("th", null, "IP"),
              React.createElement("th", null, "Type"),
              React.createElement("th", null, "Severity")
            )
          ),
          React.createElement("tbody", null,
            alerts.slice(0, 50).map((alert) => (
              React.createElement("tr", { key: alert.id },
                React.createElement("td", null, new Date(alert.timestamp).toLocaleString()),
                React.createElement("td", null, alert.ip || "-") ,
                React.createElement("td", null, alert.alert_type),
                React.createElement("td", null,
                  React.createElement("span", { className: `tag ${alert.severity}` }, alert.severity)
                )
              )
            ))
          )
        )
      )
    )
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(React.createElement(App));
