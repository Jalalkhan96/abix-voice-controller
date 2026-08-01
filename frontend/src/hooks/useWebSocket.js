import { useState, useEffect, useCallback, useRef } from "react";

const WS_URL = "ws://localhost:8765";
const RECONNECT_DELAY = 2000;
const TOAST_DURATION_MS = 5000;

export function useWebSocket({ onUiAction } = {}) {
  const [connected, setConnected] = useState(false);
  const [agentState, setAgentState] = useState("idle");
  const [captions, setCaptions] = useState([]);
  const [history, setHistory] = useState([]);
  const [pendingConfirmation, setPendingConfirmation] = useState(null);
  const [handTracking, setHandTracking] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [toasts, setToasts] = useState([]);
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);

  const addCaption = useCallback((text, role) => {
    setCaptions((prev) => {
      const next = [...prev, { text, role, id: Date.now(), ts: new Date() }];
      return next.slice(-50);
    });
  }, []);

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((message) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message }]);
    setTimeout(() => dismissToast(id), TOAST_DURATION_MS);
  }, [dismissToast]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = async () => {
        const token = (await window.abix?.getAuthToken?.()) || "";
        ws.send(JSON.stringify({ type: "auth", token }));
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          switch (msg.type) {
            case "auth_result":
              if (msg.success) {
                setConnected(true);
              } else {
                setConnected(false);
                ws.close();
              }
              break;
            case "state_change":
              setAgentState(msg.state);
              break;
            case "hand_tracking_state":
              setHandTracking(msg.active);
              break;
            case "audio_level":
              setAudioLevel(msg.level);
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
              if (!msg.success) {
                addToast(msg.response || "Command failed");
              }
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
  }, [addCaption, addToast]);

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

  const toggleHandTracking = useCallback((enable) => {
    sendCommand(enable ? "turn on hand tracking" : "turn off hand tracking");
  }, [sendCommand]);

  return {
    connected,
    agentState,
    captions,
    history,
    pendingConfirmation,
    handTracking,
    audioLevel,
    toasts,
    dismissToast,
    sendCommand,
    sendConfirmation,
    toggleHandTracking,
    setHistory,
    wsRef,
  };
}
