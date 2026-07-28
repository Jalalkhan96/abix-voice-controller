import { useState } from "react";

export default function SettingsPanel({ connected, agentState }) {
  const [handTracking, setHandTracking] = useState(false);

  const toggleHandTracking = () => {
    setHandTracking(!handTracking);
  };

  return (
    <div>
      <div className="settings-section">
        <div className="settings-label">Connection</div>
        <div className="settings-row">
          <span className="settings-key">Agent</span>
          <span className="settings-value" style={{ color: connected ? "#4FD1C5" : "#E85D4C" }}>
            {connected ? "Connected" : "Disconnected"}
          </span>
        </div>
        <div className="settings-row">
          <span className="settings-key">State</span>
          <span className="settings-value">{agentState}</span>
        </div>
      </div>

      <div className="settings-section">
        <div className="settings-label">Voice</div>
        <div className="settings-row">
          <span className="settings-key">Wake Word</span>
          <span className="settings-value">"Hi ABIX"</span>
        </div>
        <div className="settings-row">
          <span className="settings-key">STT Engine</span>
          <span className="settings-value">faster-whisper</span>
        </div>
        <div className="settings-row">
          <span className="settings-key">TTS Engine</span>
          <span className="settings-value">Piper</span>
        </div>
      </div>

      <div className="settings-section">
        <div className="settings-label">Hand Tracking</div>
        <div className="settings-row">
          <span className="settings-key">Enable Camera Mouse</span>
          <div
            className={`toggle-switch ${handTracking ? "active" : ""}`}
            onClick={toggleHandTracking}
          />
        </div>
        <div className="settings-row">
          <span className="settings-key">Camera</span>
          <span className="settings-value" style={{ color: handTracking ? "#FF8A3D" : "#8A8D93" }}>
            {handTracking ? "Active" : "Off"}
          </span>
        </div>
      </div>

      <div className="settings-section">
        <div className="settings-label">Permission Tiers</div>
        <div className="settings-row">
          <span className="settings-key" style={{ color: "#4FD1C5" }}>Tier 1</span>
          <span className="settings-value">Safe \u2014 Auto-run</span>
        </div>
        <div className="settings-row">
          <span className="settings-key" style={{ color: "#FF8A3D" }}>Tier 2</span>
          <span className="settings-value">Write \u2014 Logged</span>
        </div>
        <div className="settings-row">
          <span className="settings-key" style={{ color: "#E85D4C" }}>Tier 3</span>
          <span className="settings-value">Confirm Required</span>
        </div>
      </div>

      <div className="settings-section">
        <div className="settings-label">Services</div>
        <div className="settings-row">
          <span className="settings-key">STT</span>
          <span className="settings-value">localhost:8001</span>
        </div>
        <div className="settings-row">
          <span className="settings-key">TTS</span>
          <span className="settings-value">localhost:8002</span>
        </div>
        <div className="settings-row">
          <span className="settings-key">NLU</span>
          <span className="settings-value">localhost:8003</span>
        </div>
      </div>
    </div>
  );
}
