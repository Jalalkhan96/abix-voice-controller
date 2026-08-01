import { render, screen, fireEvent, act } from "@testing-library/react";
import CustomCommandsPanel from "./CustomCommandsPanel";

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

const AVAILABLE_INTENTS = {
  open_app: "target",
  media_play: null,
  run_command: "command",
};

describe("CustomCommandsPanel", () => {
  it("requests the command list and available intents on mount", () => {
    const ws = new FakeWs();
    render(<CustomCommandsPanel ws={ws} />);
    expect(ws.sent).toContainEqual({ type: "custom_command_list" });
  });

  it("renders existing custom commands from the server", () => {
    const ws = new FakeWs();
    render(<CustomCommandsPanel ws={ws} />);
    act(() => {
      ws.emit({
        type: "custom_command_list",
        commands: [
          { trigger: "GOOD MORNING", intent: "media_play", argument: "", description: "Start the day" },
        ],
        available_intents: AVAILABLE_INTENTS,
      });
    });
    expect(screen.getByText("GOOD MORNING")).toBeInTheDocument();
    expect(screen.getByText("Start the day")).toBeInTheDocument();
  });

  it("only shows an argument field for intents that need one", () => {
    const ws = new FakeWs();
    render(<CustomCommandsPanel ws={ws} />);
    act(() => {
      ws.emit({ type: "custom_command_list", commands: [], available_intents: AVAILABLE_INTENTS });
    });

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "media_play" } });
    expect(screen.queryByPlaceholderText(/Target|Query|command/i)).not.toBeInTheDocument();

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "open_app" } });
    expect(screen.getByPlaceholderText(/Target/)).toBeInTheDocument();
  });

  it("sends custom_command_add with trigger, intent, and argument on submit", () => {
    const ws = new FakeWs();
    render(<CustomCommandsPanel ws={ws} />);
    act(() => {
      ws.emit({ type: "custom_command_list", commands: [], available_intents: AVAILABLE_INTENTS });
    });

    fireEvent.change(screen.getByPlaceholderText(/Trigger phrase/), { target: { value: "good morning" } });
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "open_app" } });
    fireEvent.change(screen.getByPlaceholderText(/Target/), { target: { value: "firefox" } });
    fireEvent.click(screen.getByText("Add Command"));

    const addMsg = ws.sent.find((m) => m.type === "custom_command_add");
    expect(addMsg).toMatchObject({ trigger: "GOOD MORNING", intent: "open_app", argument: "firefox" });
  });

  it("sends custom_command_delete for the clicked command", () => {
    const ws = new FakeWs();
    render(<CustomCommandsPanel ws={ws} />);
    act(() => {
      ws.emit({
        type: "custom_command_list",
        commands: [{ trigger: "PING", intent: "media_play", argument: "", description: "" }],
        available_intents: AVAILABLE_INTENTS,
      });
    });
    fireEvent.click(screen.getByText("Delete"));
    expect(ws.sent).toContainEqual({ type: "custom_command_delete", trigger: "PING" });
  });
});
