// LeLamp Dashboard - Real-time Controller
// No audio recording - uses text input, voice data comes from STT/TTS on Raspberry Pi
class LeLampDashboard {
  constructor() {
    this.ws = null;
    this.currentColor = { r: 255, g: 255, b: 255 };
    this.init();
  }

  init() {
    this.setupTabs();
    this.setupWebSocket();
    this.setupColorControls();
    this.setupPresets();
    this.loadExpressions();
    this.setupChat();
    this.setupSimulation();
    this.loadConversations();
    this.loadAuditLogs();
    this.setupRefreshButtons();

    // Auto-refresh every 10 seconds
    setInterval(() => {
      if (
        document
          .getElementById("conversations-panel")
          .classList.contains("active")
      ) {
        this.loadConversations();
      }
      if (document.getElementById("logs-panel").classList.contains("active")) {
        this.loadAuditLogs();
      }
    }, 10000);
  }

  // Tab Navigation
  setupTabs() {
    document.querySelectorAll(".nav-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tabId = btn.dataset.tab;
        document
          .querySelectorAll(".nav-btn")
          .forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        document
          .querySelectorAll(".tab-panel")
          .forEach((p) => p.classList.remove("active"));
        document.getElementById(`${tabId}-panel`).classList.add("active");

        if (tabId === "conversations") this.loadConversations();
        if (tabId === "logs") this.loadAuditLogs();
      });
    });
  }

  // WebSocket for real-time updates
  setupWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    this.ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

    this.ws.onopen = () => this.updateConnection(true);
    this.ws.onclose = () => {
      this.updateConnection(false);
      setTimeout(() => this.setupWebSocket(), 3000);
    };
    this.ws.onmessage = (e) => this.handleMessage(JSON.parse(e.data));
  }

  handleMessage(data) {
    if (data.type === "init") {
      document.getElementById("session-id").textContent =
        data.session_id?.slice(0, 8) || "—";
      this.updateHardwareBadge(data.hardware);
      if (data.rgb) this.setColorUI(data.rgb[0], data.rgb[1], data.rgb[2]);
    } else if (data.type === "rgb") {
      this.setColorUI(data.color[0], data.color[1], data.color[2]);
    } else if (data.type === "new_conversation") {
      this.showLastConversation(data.user_input, data.ai_response);
      this.loadConversations();
    } else if (data.type === "state_update") {
      this.handleStateUpdate(data.update_type, data.data);
    }
  }

  handleStateUpdate(type, data) {
    if (type === "face") {
      this.updateVirtualFace(data.pixels);
    } else if (type === "rgb") {
      this.updateVirtualSolid(data.color);
    } else if (type === "arm") {
      this.updateArmStatus(data.animation);
    } else if (type === "voice") {
      this.updateVoiceStatus(data.state, data.text);
    }
  }

  updateConnection(connected) {
    const status = document.getElementById("connection-status");
    status.classList.toggle("connected", connected);
    status.querySelector(".status-label").textContent = connected
      ? "Connected"
      : "Disconnected";
  }

  updateHardwareBadge(hardware) {
    const badge = document.getElementById("hardware-badge");
    badge.textContent = hardware ? "● Hardware Connected" : "● Simulation Mode";
    badge.className = `hardware-badge ${hardware ? "connected" : "simulation"}`;
  }

  // Color Controls
  setupColorControls() {
    ["r", "g", "b"].forEach((c) => {
      const slider = document.getElementById(`${c}-slider`);
      const input = document.getElementById(`${c}-input`);

      const update = (val) => {
        this.currentColor[c] = parseInt(val);
        slider.value = val;
        input.value = val;
        this.updateColorPreview();
      };

      slider.addEventListener("input", () => update(slider.value));
      input.addEventListener("change", () =>
        update(Math.min(255, Math.max(0, input.value))),
      );
      slider.addEventListener("change", () => this.sendColor());
      input.addEventListener("change", () => this.sendColor());
    });
  }

  updateColorPreview() {
    const { r, g, b } = this.currentColor;
    document.getElementById("color-preview").style.background =
      `rgb(${r}, ${g}, ${b})`;
  }

  setColorUI(r, g, b) {
    this.currentColor = { r, g, b };
    ["r", "g", "b"].forEach((c) => {
      document.getElementById(`${c}-slider`).value = this.currentColor[c];
      document.getElementById(`${c}-input`).value = this.currentColor[c];
    });
    this.updateColorPreview();
  }

  async sendColor() {
    await fetch("/api/rgb/solid", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(this.currentColor),
    });
  }

  setupPresets() {
    document.querySelectorAll(".preset-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        this.setColorUI(
          parseInt(btn.dataset.r),
          parseInt(btn.dataset.g),
          parseInt(btn.dataset.b),
        );
        this.sendColor();
      });
    });
  }

  // Expressions
  async loadExpressions() {
    const grid = document.getElementById("expressions-grid");
    try {
      const res = await fetch("/api/recordings");
      const data = await res.json();

      if (!data.recordings?.length) {
        grid.innerHTML =
          '<div class="loading-text">No expressions available</div>';
        return;
      }

      const icons = {
        happy_wiggle: "🎉",
        nod: "👍",
        headshake: "👎",
        curious: "🤔",
        excited: "🤩",
        sad: "😢",
        shy: "😊",
        shock: "😱",
        scanning: "👀",
        wake_up: "👋",
        idle: "💤",
      };

      grid.innerHTML = data.recordings
        .map(
          (name) => `
                <button class="expression-btn" data-name="${name}">
                    <span class="expression-icon">${icons[name] || "🤖"}</span>
                    <span>${name.replace(/_/g, " ")}</span>
                </button>
            `,
        )
        .join("");

      grid.querySelectorAll(".expression-btn").forEach((btn) => {
        btn.addEventListener("click", () =>
          this.playExpression(btn.dataset.name, btn),
        );
      });
    } catch (err) {
      grid.innerHTML =
        '<div class="loading-text">Failed to load expressions</div>';
    }
  }

  async playExpression(name, btn) {
    btn.classList.add("playing");
    await fetch("/api/recordings/play", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    setTimeout(() => btn.classList.remove("playing"), 3000);
  }

  // Chat - Text input (voice handled by STT/TTS on RPi)
  setupChat() {
    const input = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");

    const sendMessage = async () => {
      const message = input.value.trim();
      if (!message) return;

      input.value = "";
      sendBtn.disabled = true;
      sendBtn.textContent = "Sending...";

      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message }),
        });

        const data = await res.json();
        if (data.user_input && data.ai_response) {
          this.showLastConversation(data.user_input, data.ai_response);
          this.loadConversations();
        }
      } catch (err) {
        console.error("Chat error:", err);
      }

      sendBtn.disabled = false;
      sendBtn.textContent = "Send";
    };

    sendBtn.addEventListener("click", sendMessage);
    input.addEventListener("keypress", (e) => {
      if (e.key === "Enter") sendMessage();
    });
  }

  showLastConversation(user, ai) {
    document.getElementById("last-conversation").innerHTML = `
            <div class="convo-item"><div class="convo-user">${user}</div></div>
            <div class="convo-item"><div class="convo-ai">${ai}</div></div>
        `;
  }

  // Conversations from Firestore
  async loadConversations() {
    const list = document.getElementById("conversations-list");
    try {
      const res = await fetch("/api/conversations?limit=20");
      const data = await res.json();

      if (!data.conversations?.length) {
        list.innerHTML = '<div class="loading-text">No conversations yet</div>';
        return;
      }

      list.innerHTML = data.conversations
        .map(
          (c) => `
                <div class="conversation-card">
                    <div class="conversation-header">
                        <span class="conversation-time">${this.formatTime(c.timestamp)}</span>
                        <span class="conversation-type">${c.input_type || "text"}</span>
                    </div>
                    <div class="conversation-user">👤 ${c.user_input || "—"}</div>
                    <div class="conversation-ai">🤖 ${c.ai_response || "—"}</div>
                </div>
            `,
        )
        .join("");
    } catch (err) {
      list.innerHTML = '<div class="loading-text">Failed to load</div>';
    }
  }

  // Audit Logs from Firestore
  async loadAuditLogs() {
    const tbody = document.getElementById("logs-tbody");
    try {
      const res = await fetch("/api/audit-logs?limit=50");
      const data = await res.json();

      if (!data.logs?.length) {
        tbody.innerHTML =
          '<tr><td colspan="5" class="loading-text">No logs yet</td></tr>';
        return;
      }

      tbody.innerHTML = data.logs
        .map(
          (log) => `
                <tr>
                    <td>${this.formatTime(log.timestamp)}</td>
                    <td><code>${log.endpoint}</code></td>
                    <td><span class="method-badge method-${log.method}">${log.method}</span></td>
                    <td>${log.duration_ms?.toFixed(1) || "—"}ms</td>
                    <td>${log.response?.status_code || "—"}</td>
                </tr>
            `,
        )
        .join("");
    } catch (err) {
      tbody.innerHTML =
        '<tr><td colspan="5" class="loading-text">Failed to load</td></tr>';
    }
  }

  formatTime(isoString) {
    if (!isoString) return "—";
    return new Date(isoString).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  setupRefreshButtons() {
    document
      .getElementById("refresh-conversations")
      ?.addEventListener("click", () => this.loadConversations());
    document
      .getElementById("refresh-logs")
      ?.addEventListener("click", () => this.loadAuditLogs());
  }

  // --- Simulation Logic ---

  setupSimulation() {
    const matrix = document.getElementById("virtual-led-matrix");
    if (!matrix) return;

    matrix.innerHTML = "";
    for (let i = 0; i < 64; i++) {
      const pixel = document.createElement("div");
      pixel.className = "led-pixel";
      pixel.id = `led-${i}`;
      matrix.appendChild(pixel);
    }
  }

  updateVirtualFace(pixels) {
    if (!Array.isArray(pixels)) return;
    pixels.forEach((rgb, i) => {
      const pixel = document.getElementById(`led-${i}`);
      if (pixel) {
        const color = `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
        pixel.style.background = color;
        // Add glow if brightness is significant
        const brightness = (rgb[0] + rgb[1] + rgb[2]) / 3;
        if (brightness > 50) {
          pixel.style.boxShadow = `0 0 8px ${color}`;
        } else {
          pixel.style.boxShadow = "none";
        }
      }
    });
  }

  updateVirtualSolid(rgb) {
    const pixels = Array(64).fill(rgb);
    this.updateVirtualFace(pixels);
  }

  updateArmStatus(animation) {
    const status = document.getElementById("sim-arm-status");
    if (status) {
      status.textContent = animation.replace(/_/g, " ");
      status.classList.add("active"); // Could add animation class
      setTimeout(() => status.classList.remove("active"), 3000);
    }
  }

  updateVoiceStatus(state, text) {
    const status = document.getElementById("sim-voice-status");
    if (status) {
      status.textContent = state;
      status.className = `status-value ${state}`;

      if (state === "speaking" && text) {
        this.showLastConversation("...", text); // Partial update
      }
    }
  }
}

document.addEventListener(
  "DOMContentLoaded",
  () => (window.dashboard = new LeLampDashboard()),
);
