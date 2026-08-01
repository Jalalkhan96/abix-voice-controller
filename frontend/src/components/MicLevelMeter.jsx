// Relative weight per bar so the outer bars need more signal to move than
// the center one — reads more like a real level meter than uniform bars.
const BAR_WEIGHTS = [0.5, 0.8, 1.0, 0.8, 0.5];

export default function MicLevelMeter({ level = 0, active = false }) {
  return (
    <div className="mic-level-meter" aria-hidden="true">
      {BAR_WEIGHTS.map((weight, i) => {
        const scale = active ? Math.min(1, Math.max(0.15, level * weight * 1.6)) : 0.15;
        return (
          <div
            key={i}
            className={`mic-level-bar ${active ? "active" : ""}`}
            style={{ transform: `scaleY(${scale})` }}
          />
        );
      })}
    </div>
  );
}
