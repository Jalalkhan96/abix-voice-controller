import { render, screen, fireEvent, act } from "@testing-library/react";
import SettingsPanel from "./SettingsPanel";

class FakeWs {
  constructor() {
    this.sent = [];
    this.listeners = [];
  }
  addEventListener(_type, handler) {
    this.listeners.push(handler);
  }
  removeEventListener(_type, handler) {
    this.listeners = this.listeners.filter((h) => h !== handler);
  }
  send(data) {
    this.sent.push(JSON.parse(data));
  }
  emit(payload) {
    this.listeners.forEach((h) => h({ data: JSON.stringify(payload) }));
  }
}

describe("SettingsPanel editable settings", () => {
  it("requests settings on mount and populates fields from the response", () => {
    const ws = new FakeWs();
    render(<SettingsPanel connected agentState="idle" ws={ws} onToggleHandTracking={jest.fn()} />);

    expect(ws.sent).toContainEqual({ type: "get_settings" });

    act(() => {
      ws.emit({
        type: "settings",
        settings: {
          wake_word_phrase: "hey computer",
          listen_duration_seconds: 15,
          stt_url: "http://localhost:8001",
          tts_url: "http://localhost:8002",
          nlu_url: "http://localhost:8003",
        },
      });
    });

    expect(screen.getByDisplayValue("hey computer")).toBeInTheDocument();
    expect(screen.getByDisplayValue("15")).toBeInTheDocument();
  });

  it("sends update_settings with the edited fields on save", () => {
    const ws = new FakeWs();
    render(<SettingsPanel connected agentState="idle" ws={ws} onToggleHandTracking={jest.fn()} />);

    act(() => {
      ws.emit({
        type: "settings",
        settings: {
          wake_word_phrase: "hi abix",
          listen_duration_seconds: 10,
          stt_url: "http://localhost:8001",
          tts_url: "http://localhost:8002",
          nlu_url: "http://localhost:8003",
        },
      });
    });

    fireEvent.change(screen.getByDisplayValue("hi abix"), { target: { value: "hey abix" } });
    fireEvent.click(screen.getByText("Save"));

    const saveMsg = ws.sent.find((m) => m.type === "update_settings");
    expect(saveMsg.fields.wake_word_phrase).toBe("hey abix");
  });

  it("shows the server's confirmation message after saving", () => {
    const ws = new FakeWs();
    render(<SettingsPanel connected agentState="idle" ws={ws} onToggleHandTracking={jest.fn()} />);

    act(() => {
      ws.emit({
        type: "settings",
        settings: { wake_word_phrase: "hi abix", listen_duration_seconds: 10, stt_url: "", tts_url: "", nlu_url: "" },
        message: "Settings saved. Restart ABIX to apply.",
      });
    });

    expect(screen.getByText("Settings saved. Restart ABIX to apply.")).toBeInTheDocument();
  });
});

describe("SettingsPanel", () => {
  it("reflects the real hand-tracking state via props, not local state", () => {
    render(
      <SettingsPanel connected agentState="idle" handTracking={true} onToggleHandTracking={jest.fn()} />
    );
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("calls onToggleHandTracking with the inverse of the current state on click", () => {
    const onToggle = jest.fn();
    const { container } = render(
      <SettingsPanel connected agentState="idle" handTracking={false} onToggleHandTracking={onToggle} />
    );
    fireEvent.click(container.querySelector(".toggle-switch"));
    expect(onToggle).toHaveBeenCalledWith(true);
  });

  it("does not manage hand-tracking state on its own", () => {
    const onToggle = jest.fn();
    const { container, rerender } = render(
      <SettingsPanel connected agentState="idle" handTracking={false} onToggleHandTracking={onToggle} />
    );
    fireEvent.click(container.querySelector(".toggle-switch"));
    // clicking alone must not flip the displayed state — only a prop change can
    expect(screen.getByText("Off")).toBeInTheDocument();
    rerender(
      <SettingsPanel connected agentState="idle" handTracking={true} onToggleHandTracking={onToggle} />
    );
    expect(screen.getByText("Active")).toBeInTheDocument();
  });
});
