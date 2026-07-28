function formatTime(ts) {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

const TIER_LABELS = {
  1: "Tier 1 \u2014 Safe",
  2: "Tier 2 \u2014 Write",
  3: "Tier 3 \u2014 Destructive",
};

export default function HistoryPanel({ history }) {
  if (history.length === 0) {
    return (
      <div className="empty-state">
        No commands yet.
        <br />
        <br />
        Try saying: "Open Firefox"
      </div>
    );
  }

  return (
    <div>
      {history.map((item) => (
        <div
          key={item.id}
          className={`history-item ${item.success ? "success" : "failure"} ${
            item.tier === 3 ? "tier-3" : ""
          }`}
        >
          <div className="history-ts">{formatTime(item.ts)}</div>
          <div className="history-intent">{item.intent}</div>
          <div className="history-response">{item.response}</div>
          <div className="history-tier">{TIER_LABELS[item.tier] || `Tier ${item.tier}`}</div>
        </div>
      ))}
    </div>
  );
}
