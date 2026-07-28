import { useState } from "react";
import Orb3D from "./components/Orb3D";
import Captions from "./components/Captions";
import HistoryPanel from "./components/HistoryPanel";
import SettingsPanel from "./components/SettingsPanel";
import ShortcutsPanel from "./components/ShortcutsPanel";
import { useWebSocket } from "./hooks/useWebSocket";
import "./App.css";

const STATE_LABELS = {
  idle: "Idle",
  listening: "Listening",
  thinking: "Thinking",
  speaking: "Speaking",
  confirming: "Confirming",
};

export default function App() {
  const [panelOpen, setPanelOpen] = useState(true);
  const [panelTab, setPanelTab] = useState("history");
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [textInput, setTextInput] = useState("");

  const {
    connected,
    agentState,
    captions,
    history,
    pendingConfirmation,
    sendCommand,
    sendConfirmation,
    wsRef,
  } = useWebSocket({
    onUiAction: (action) => {
      switch (action) {
        case "open_settings":
          setPanelOpen(true);
          setPanelTab("settings");
          break;
        case "open_shortcuts":
          setPanelOpen(true);
          setPanelTab("shortcuts");
          break;
        case "close_panel":
          setPanelOpen(false);
          break;
        case "minimize":
          window.abix?.minimize();
          break;
        case "maximize":
          window.abix?.maximize();
          break;
        case "close":
          window.abix?.close();
          break;
      }
    },
  });

  return (
    <div className="app-layout">
      {/* Title bar */}
      <div className="titlebar">
        <div className="titlebar-title">ABIX</div>
        <div className="titlebar-status">
          <div className={`status-dot ${connected ? "connected" : ""} ${agentState}`} />
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)" }}>
            {STATE_LABELS[agentState] || agentState}
          </span>
        </div>
        <div className="titlebar-buttons">
          <button className="titlebar-btn" onClick={() => window.abix?.minimize()}>{"\u2013"}</button>
          <button className="titlebar-btn" onClick={() => window.abix?.maximize()}>{"\u25A1"}</button>
          <button className="titlebar-btn close" onClick={() => window.abix?.close()}>{"\u2715"}</button>
        </div>
      </div>

      {/* Mic indicator */}
      <div className="mic-indicator">
        <div className={`mic-dot ${agentState === "listening" ? "active" : ""}`} />
        <span>MIC {agentState === "listening" ? "ACTIVE" : "READY"}</span>
      </div>

      {/* Panel toggle */}
      <button
        className="panel-toggle"
        onClick={() => setPanelOpen(!panelOpen)}
        title={panelOpen ? "Close panel" : "Open panel"}
      >
        {panelOpen ? "\u276F" : "\u276E"}
      </button>

      {/* 3D Orb */}
      <div className="orb-area">
        <Orb3D agentState={agentState} />
        <Captions captions={captions} />
      </div>

      {/* Text input bar */}
      <div className="text-input-bar">
        <input
          type="text"
          className="text-input"
          placeholder="Type a command..."
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && textInput.trim()) {
              sendCommand(textInput.trim());
              setTextInput("");
            }
          }}
        />
        <button
          className="text-send-btn"
          onClick={() => {
            if (textInput.trim()) {
              sendCommand(textInput.trim());
              setTextInput("");
            }
          }}
        >
          Send
        </button>
      </div>

      {/* Side panel */}
      <div className={`side-panel ${panelOpen ? "" : "collapsed"}`}>
        <div className="panel-header">
          <div style={{ display: "flex", gap: 0 }}>
            <button
              className="panel-title"
              style={{
                background: panelTab === "history" ? "var(--bg-elevated)" : "transparent",
                border: "none",
                padding: "6px 12px",
                borderRadius: "4px",
                cursor: "pointer",
                color: panelTab === "history" ? "var(--accent-amber)" : "var(--text-muted)",
              }}
              onClick={() => setPanelTab("history")}
            >
              History
            </button>
            <button
              className="panel-title"
              style={{
                background: panelTab === "settings" ? "var(--bg-elevated)" : "transparent",
                border: "none",
                padding: "6px 12px",
                borderRadius: "4px",
                cursor: "pointer",
                color: panelTab === "settings" ? "var(--accent-amber)" : "var(--text-muted)",
              }}
              onClick={() => setPanelTab("settings")}
            >
              Settings
            </button>
            <button
              className="panel-title"
              style={{
                background: panelTab === "shortcuts" ? "var(--bg-elevated)" : "transparent",
                border: "none",
                padding: "6px 12px",
                borderRadius: "4px",
                cursor: "pointer",
                color: panelTab === "shortcuts" ? "var(--accent-amber)" : "var(--text-muted)",
              }}
              onClick={() => setPanelTab("shortcuts")}
            >
              Shortcuts
            </button>
          </div>
          <button className="panel-close-btn" onClick={() => setPanelOpen(false)}>
            {"\u2715"}
          </button>
        </div>
        <div className="panel-content">
          {panelTab === "history" ? (
            <HistoryPanel history={history} />
          ) : panelTab === "settings" ? (
            <SettingsPanel connected={connected} agentState={agentState} />
          ) : (
            <ShortcutsPanel ws={wsRef.current} />
          )}
        </div>
      </div>

      {/* Confirmation overlay */}
      {pendingConfirmation && (
        <div className="confirm-overlay">
          <div className="confirm-card">
            <div className="confirm-title">Confirm Action</div>
            <div className="confirm-message">{pendingConfirmation.message}</div>
            <div className="confirm-buttons">
              <button className="confirm-btn yes" onClick={() => sendConfirmation(true)}>
                Confirm
              </button>
              <button className="confirm-btn no" onClick={() => sendConfirmation(false)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
