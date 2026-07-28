import React, { useState, useEffect } from "react";
import "./ShortcutsPanel.css";

const BROWSERS = [
  { value: "brave-browser", label: "Brave" },
  { value: "google-chrome", label: "Chrome" },
  { value: "firefox", label: "Firefox" },
  { value: "chromium-browser", label: "Chromium" },
];

export default function ShortcutsPanel({ ws }) {
  const [shortcuts, setShortcuts] = useState([]);
  const [keyword, setKeyword] = useState("");
  const [browser, setBrowser] = useState("brave-browser");
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  const [editIdx, setEditIdx] = useState(-1);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!ws) return;
    const handler = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "shortcut_list") {
          setShortcuts(data.shortcuts);
        } else if (data.type === "shortcut_result") {
          setMessage(data.message);
          setShortcuts(data.shortcuts);
          setTimeout(() => setMessage(""), 3000);
        }
      } catch (_) {}
    };
    ws.addEventListener("message", handler);
    ws.send(JSON.stringify({ type: "shortcut_list" }));
    return () => ws.removeEventListener("message", handler);
  }, [ws]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!keyword.trim() || !url.trim()) return;
    if (editIdx >= 0) {
      ws.send(JSON.stringify({
        type: "shortcut_update",
        keyword: keyword.trim(),
        browser,
        url: url.trim(),
        description: description.trim(),
      }));
    } else {
      ws.send(JSON.stringify({
        type: "shortcut_add",
        keyword: keyword.trim(),
        browser,
        url: url.trim(),
        description: description.trim(),
      }));
    }
    setKeyword("");
    setUrl("");
    setDescription("");
    setEditIdx(-1);
  };

  const handleEdit = (sc) => {
    setKeyword(sc.keyword);
    setBrowser(sc.browser);
    setUrl(sc.url);
    setDescription(sc.description);
    setEditIdx(shortcuts.indexOf(sc));
  };

  const handleDelete = (kw) => {
    ws.send(JSON.stringify({ type: "shortcut_delete", keyword: kw }));
  };

  if (!ws) return <div className="shortcuts-panel"><p style={{color:"#666",textAlign:"center",padding:20}}>Connecting...</p></div>;

  return (
    <div className="shortcuts-panel" style={{padding:0,background:"transparent",border:"none",maxHeight:"none"}}>
      <p className="shortcuts-hint">
        Say or type a keyword to trigger. Example: say "SAD" to play a song.
      </p>
      {message && <div className="shortcuts-msg">{message}</div>}
      <form className="shortcuts-form" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Keyword (e.g. SAD)"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value.toUpperCase())}
          className="sc-input"
        />
        <input
          type="text"
          placeholder="YouTube URL or search URL"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="sc-input"
        />
        <input
          type="text"
          placeholder="Description (optional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="sc-input"
        />
        <select
          value={browser}
          onChange={(e) => setBrowser(e.target.value)}
          className="sc-select"
        >
          {BROWSERS.map((b) => (
            <option key={b.value} value={b.value}>{b.label}</option>
          ))}
        </select>
        <button type="submit" className="sc-submit">
          {editIdx >= 0 ? "Update" : "Add Shortcut"}
        </button>
        {editIdx >= 0 && (
          <button type="button" className="sc-cancel" onClick={() => {
            setKeyword(""); setUrl(""); setDescription(""); setEditIdx(-1);
          }}>Cancel</button>
        )}
      </form>
      <div className="shortcuts-list">
        {shortcuts.length === 0 && <p className="sc-empty">No shortcuts yet. Add one above.</p>}
        {shortcuts.map((sc, i) => (
          <div key={sc.keyword} className="shortcut-item">
            <div className="sc-info">
              <span className="sc-keyword">{sc.keyword}</span>
              <span className="sc-desc">{sc.description || sc.url}</span>
              <span className="sc-browser">({BROWSERS.find(b => b.value === sc.browser)?.label || sc.browser})</span>
            </div>
            <div className="sc-actions">
              <button onClick={() => handleEdit(sc)} className="sc-edit">Edit</button>
              <button onClick={() => handleDelete(sc.keyword)} className="sc-delete">Delete</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
