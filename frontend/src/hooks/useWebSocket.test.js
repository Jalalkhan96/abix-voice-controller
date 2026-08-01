import { renderHook, act } from "@testing-library/react";
import { useWebSocket } from "./useWebSocket";

class MockWebSocket {
  static OPEN = 1;
  static instances = [];

  constructor(url) {
    this.url = url;
    this.readyState = 0;
    this.sent = [];
    MockWebSocket.instances.push(this);
  }

  send(data) {
    this.sent.push(JSON.parse(data));
  }

  close() {
    this.readyState = 3;
    if (this.onclose) this.onclose();
  }

  emitMessage(payload) {
    if (this.onmessage) this.onmessage({ data: JSON.stringify(payload) });
  }
}

beforeEach(() => {
  MockWebSocket.instances = [];
  global.WebSocket = MockWebSocket;
  window.abix = { getAuthToken: jest.fn().mockResolvedValue("test-token") };
});

afterEach(() => {
  delete global.WebSocket;
  delete window.abix;
});

async function connectAndAuth() {
  const { result } = renderHook(() => useWebSocket());
  const ws = MockWebSocket.instances[0];
  ws.readyState = MockWebSocket.OPEN;

  await act(async () => {
    await ws.onopen();
  });
  expect(window.abix.getAuthToken).toHaveBeenCalled();
  expect(ws.sent[0]).toEqual({ type: "auth", token: "test-token" });

  act(() => {
    ws.emitMessage({ type: "auth_result", success: true });
  });

  return { result, ws };
}

describe("useWebSocket", () => {
  it("sends an auth message on open and marks connected on success", async () => {
    const { result } = await connectAndAuth();
    expect(result.current.connected).toBe(true);
  });

  it("does not mark connected and closes the socket on auth failure", async () => {
    const { result } = renderHook(() => useWebSocket());
    const ws = MockWebSocket.instances[0];
    ws.readyState = MockWebSocket.OPEN;

    await act(async () => {
      await ws.onopen();
    });
    act(() => {
      ws.emitMessage({ type: "auth_result", success: false });
    });

    expect(result.current.connected).toBe(false);
    expect(ws.readyState).toBe(3);
  });

  it("updates agentState on state_change messages", async () => {
    const { result, ws } = await connectAndAuth();
    act(() => {
      ws.emitMessage({ type: "state_change", state: "listening" });
    });
    expect(result.current.agentState).toBe("listening");
  });

  it("appends captions and caps them at 50", async () => {
    const { result, ws } = await connectAndAuth();
    act(() => {
      ws.emitMessage({ type: "caption", text: "hello", role: "user" });
    });
    expect(result.current.captions).toHaveLength(1);
    expect(result.current.captions[0]).toMatchObject({ text: "hello", role: "user" });
  });

  it("prepends command_result entries to history", async () => {
    const { result, ws } = await connectAndAuth();
    act(() => {
      ws.emitMessage({ type: "command_result", intent: "open_app", response: "Launched firefox", success: true, tier: 2 });
    });
    expect(result.current.history[0]).toMatchObject({ intent: "open_app", success: true });
  });

  it("adds a toast when a command fails, but not when it succeeds", async () => {
    const { result, ws } = await connectAndAuth();
    act(() => {
      ws.emitMessage({ type: "command_result", intent: "open_app", response: "Launched firefox", success: true, tier: 2 });
    });
    expect(result.current.toasts).toHaveLength(0);

    act(() => {
      ws.emitMessage({ type: "command_result", intent: "delete_file", response: "Command blocked: dangerous pattern", success: false, tier: 3 });
    });
    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe("Command blocked: dangerous pattern");
  });

  it("dismissToast removes a toast by id", async () => {
    const { result, ws } = await connectAndAuth();
    act(() => {
      ws.emitMessage({ type: "command_result", intent: "run_command", response: "Command failed", success: false, tier: 3 });
    });
    expect(result.current.toasts).toHaveLength(1);
    const id = result.current.toasts[0].id;

    act(() => {
      result.current.dismissToast(id);
    });
    expect(result.current.toasts).toHaveLength(0);
  });

  it("surfaces confirmation_needed as pendingConfirmation", async () => {
    const { result, ws } = await connectAndAuth();
    act(() => {
      ws.emitMessage({ type: "confirmation_needed", message: "Delete file.txt?", action: "delete_file", args: { target: "file.txt" } });
    });
    expect(result.current.pendingConfirmation).toMatchObject({ message: "Delete file.txt?", action: "delete_file" });
  });

  it("sendCommand only sends when the socket is open", async () => {
    const { result, ws } = await connectAndAuth();
    act(() => {
      result.current.sendCommand("open firefox");
    });
    expect(ws.sent).toContainEqual({ type: "user_input", text: "open firefox" });
  });

  it("sendConfirmation sends yes/no and clears pendingConfirmation", async () => {
    const { result, ws } = await connectAndAuth();
    act(() => {
      ws.emitMessage({ type: "confirmation_needed", message: "Delete file.txt?", action: "delete_file", args: {} });
    });
    expect(result.current.pendingConfirmation).not.toBeNull();

    act(() => {
      result.current.sendConfirmation(true);
    });
    expect(ws.sent).toContainEqual({ type: "user_input", text: "yes" });
    expect(result.current.pendingConfirmation).toBeNull();
  });
});
