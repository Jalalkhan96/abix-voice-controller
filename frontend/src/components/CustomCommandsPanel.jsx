import { useState, useEffect } from "react";
import "./ShortcutsPanel.css";

const ARG_LABELS = {
  target: "Target (app/file/URL name)",
  query: "Query",
  command: "Shell command",
};

export default function CustomCommandsPanel({ ws }) {
  const [commands, setCommands] = useState([]);
  const [availableIntents, setAvailableIntents] = useState({});
  const [trigger, setTrigger] = useState("");
  const [intent, setIntent] = useState("");
  const [argument, setArgument] = useState("");
  const [description, setDescription] = useState("");
  const [editTrigger, setEditTrigger] = useState(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!ws) return;
    const handler = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "custom_command_list") {
          setCommands(data.commands);
          setAvailableIntents(data.available_intents);
          if (!intent && Object.keys(data.available_intents).length > 0) {
            setIntent(Object.keys(data.available_intents)[0]);
          }
        } else if (data.type === "custom_command_result") {
          setMessage(data.message);
          setCommands(data.commands);
          setTimeout(() => setMessage(""), 3000);
        }
      } catch (_) {}
    };
    ws.addEventListener("message", handler);
    ws.send(JSON.stringify({ type: "custom_command_list" }));
    return () => ws.removeEventListener("message", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ws]);

  const argKey = availableIntents[intent];
  const needsArgument = argKey != null;

  const resetForm = () => {
    setTrigger("");
    setArgument("");
    setDescription("");
    setEditTrigger(null);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!trigger.trim() || !intent) return;
    const type = editTrigger ? "custom_command_update" : "custom_command_add";
    ws.send(JSON.stringify({
      type,
      trigger: trigger.trim(),
      intent,
      argument: needsArgument ? argument.trim() : "",
      description: description.trim(),
    }));
    resetForm();
  };

  const handleEdit = (cmd) => {
    setTrigger(cmd.trigger);
    setIntent(cmd.intent);
    setArgument(cmd.argument);
    setDescription(cmd.description);
    setEditTrigger(cmd.trigger);
  };

  const handleDelete = (t) => {
    ws.send(JSON.stringify({ type: "custom_command_delete", trigger: t }));
  };

  if (!ws) {
    return (
      <div style={{ color: "#666", textAlign: "center", padding: 20 }}>Connecting...</div>
    );
  }

  return (
    <div>
      <p className="shortcuts-hint">
        Map any phrase directly to an action — say or type it exactly to trigger it. Safety
        confirmations (e.g. for shell commands) still apply.
      </p>
      {message && <div className="shortcuts-msg">{message}</div>}
      <form className="shortcuts-form" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Trigger phrase (e.g. GOOD MORNING)"
          value={trigger}
          onChange={(e) => setTrigger(e.target.value.toUpperCase())}
          className="sc-input"
        />
        <select
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          className="sc-select"
        >
          {Object.keys(availableIntents).map((name) => (
            <option key={name} value={name}>{name}</option>
          ))}
        </select>
        {needsArgument && (
          <input
            type="text"
            placeholder={ARG_LABELS[argKey] || "Argument"}
            value={argument}
            onChange={(e) => setArgument(e.target.value)}
            className="sc-input"
          />
        )}
        <input
          type="text"
          placeholder="Description (optional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="sc-input"
        />
        <button type="submit" className="sc-submit">
          {editTrigger ? "Update" : "Add Command"}
        </button>
        {editTrigger && (
          <button type="button" className="sc-cancel" onClick={resetForm}>Cancel</button>
        )}
      </form>
      <div className="shortcuts-list">
        {commands.length === 0 && <p className="sc-empty">No custom commands yet. Add one above.</p>}
        {commands.map((cmd) => (
          <div key={cmd.trigger} className="shortcut-item">
            <div className="sc-info">
              <span className="sc-keyword">{cmd.trigger}</span>
              <span className="sc-desc">{cmd.description || `${cmd.intent}${cmd.argument ? ": " + cmd.argument : ""}`}</span>
              <span className="sc-browser">({cmd.intent})</span>
            </div>
            <div className="sc-actions">
              <button onClick={() => handleEdit(cmd)} className="sc-edit">Edit</button>
              <button onClick={() => handleDelete(cmd.trigger)} className="sc-delete">Delete</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
