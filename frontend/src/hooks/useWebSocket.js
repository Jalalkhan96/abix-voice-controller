import { useState, useEffect, useCallback, useRef } from "react";

const WS_URL = "ws://localhost:8765";
const RECONNECT_DELAY = 2000;

export function useWebSocket({ onUiAction } = {}) {
  const [connected, setConnected] = useState(false);
  const [agentState, setAgentState] = useState("idle");
  const [captions, setCaptions] = useState([]);
  const [history, setHistory] = useState([]);
  const [pendingConfirmation, setPendingConfirmation] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);

  const addCaption = useCallback((text, role) => {
    setCaptions((prev) => {
      const next = [...prev, { text, role, id: Date.now(), ts: new Date() }];
      return next.slice(-50);
    });
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          switch (msg.type) {
            case "state_change":
              setAgentState(msg.state);
              break;
            case "caption":
              addCaption(msg.text, msg.role);
              break;
            case "command_result":
              setHistory((prev) => [
                {
                  id: Date.now(),
                  intent: msg.intent,
                  response: msg.response,
                  success: msg.success,
                  tier: msg.tier,
                  ts: new Date(),
                },
                ...prev,
              ].slice(0, 100));
              break;
            case "confirmation_needed":
              setPendingConfirmation({
                message: msg.message,
                action: msg.action,
                args: msg.args,
              });
              break;
            case "ui_action":
              if (onUiAction) onUiAction(msg.action);
              break;
          }
        } catch {}
      };

      ws.onclose = () => {
        setConnected(false);
        reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY);
      };

      ws.onerror = () => ws.close();
    } catch {
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY);
    }
  }, [addCaption]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const sendCommand = useCallback((text) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "user_input", text }));
    }
  }, []);

  const sendConfirmation = useCallback((confirmed) => {
    if (wsRef.current?.readyState === WebSocket.OPEN && pendingConfirmation) {
      wsRef.current.send(
        JSON.stringify({
          type: "user_input",
          text: confirmed ? "yes" : "no",
        })
      );
      setPendingConfirmation(null);
    }
  }, [pendingConfirmation]);

  return {
    connected,
    agentState,
    captions,
    history,
    pendingConfirmation,
    sendCommand,
    sendConfirmation,
    setHistory,
    wsRef,
  };
}
