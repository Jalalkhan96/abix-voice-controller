import { useState, useEffect } from "react";

const DEFAULT_SETTINGS = {
  wake_word_phrase: "hi abix",
  listen_duration_seconds: 10,
  stt_url: "",
  tts_url: "",
  nlu_url: "",
};

export default function SettingsPanel({ connected, agentState, handTracking, onToggleHandTracking, ws }) {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [loaded, setLoaded] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!ws) return;
    const handler = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "settings") {
          setSettings(data.settings);
          setLoaded(true);
          if (data.message) {
            setMessage(data.message);
            setTimeout(() => setMessage(""), 4000);
          }
        }
      } catch (_) {}
    };
    ws.addEventListener("message", handler);
    ws.send(JSON.stringify({ type: "get_settings" }));
    return () => ws.removeEventListener("message", handler);
  }, [ws]);

  const setField = (key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = (e) => {
    e.preventDefault();
    if (!ws) return;
    ws.send(JSON.stringify({ type: "update_settings", fields: settings }));
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

      <form className="settings-section" onSubmit={handleSave}>
        <div className="settings-label">Voice</div>
        <div className="settings-row">
          <span className="settings-key">Wake Word</span>
          <input
            type="text"
            className="settings-input"
            value={settings.wake_word_phrase}
            disabled={!loaded}
            onChange={(e) => setField("wake_word_phrase", e.target.value)}
          />
        </div>
        <div className="settings-row">
          <span className="settings-key">Listen Duration (s)</span>
          <input
            type="number"
            min={3}
            max={60}
            className="settings-input settings-input-narrow"
            value={settings.listen_duration_seconds}
            disabled={!loaded}
            onChange={(e) => setField("listen_duration_seconds", e.target.value)}
          />
        </div>
        <div className="settings-row">
          <span className="settings-key">STT Engine</span>
          <span className="settings-value">faster-whisper</span>
        </div>
        <div className="settings-row">
          <span className="settings-key">TTS Engine</span>
          <span className="settings-value">Piper</span>
        </div>

        <div className="settings-label" style={{ marginTop: 16 }}>Services</div>
        <div className="settings-row">
          <span className="settings-key">STT URL</span>
          <input
            type="text"
            className="settings-input"
            value={settings.stt_url}
            disabled={!loaded}
            onChange={(e) => setField("stt_url", e.target.value)}
          />
        </div>
        <div className="settings-row">
          <span className="settings-key">TTS URL</span>
          <input
            type="text"
            className="settings-input"
            value={settings.tts_url}
            disabled={!loaded}
            onChange={(e) => setField("tts_url", e.target.value)}
          />
        </div>
        <div className="settings-row">
          <span className="settings-key">NLU URL</span>
          <input
            type="text"
            className="settings-input"
            value={settings.nlu_url}
            disabled={!loaded}
            onChange={(e) => setField("nlu_url", e.target.value)}
          />
        </div>

        <button type="submit" className="settings-save-btn" disabled={!loaded}>
          Save
        </button>
        {message && <div className="settings-saved-msg">{message}</div>}
      </form>

      <div className="settings-section">
        <div className="settings-label">Hand Tracking</div>
        <div className="settings-row">
          <span className="settings-key">Enable Camera Mouse</span>
          <div
            className={`toggle-switch ${handTracking ? "active" : ""}`}
            onClick={() => onToggleHandTracking(!handTracking)}
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
          <span className="settings-value">Safe — Auto-run</span>
        </div>
        <div className="settings-row">
          <span className="settings-key" style={{ color: "#FF8A3D" }}>Tier 2</span>
          <span className="settings-value">Write — Logged</span>
        </div>
        <div className="settings-row">
          <span className="settings-key" style={{ color: "#E85D4C" }}>Tier 3</span>
          <span className="settings-value">Confirm Required</span>
        </div>
      </div>
    </div>
  );
}
