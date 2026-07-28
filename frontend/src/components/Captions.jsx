import { useEffect, useRef } from "react";

export default function Captions({ captions }) {
  const scrollRef = useRef();
  const recent = captions.slice(-5);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [captions]);

  if (recent.length === 0) {
    return (
      <div className="captions-bar">
        <div className="caption-line system">Say "Hi ABIX" to begin</div>
      </div>
    );
  }

  return (
    <div className="captions-bar" ref={scrollRef}>
      {recent.map((cap) => (
        <div key={cap.id} className={`caption-line ${cap.role}`}>
          {cap.role === "abix" ? "\u25B6 " : cap.role === "user" ? "\u25C6 " : ""}
          {cap.text}
        </div>
      ))}
    </div>
  );
}
