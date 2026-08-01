import { render, screen } from "@testing-library/react";
import HistoryPanel from "./HistoryPanel";

describe("HistoryPanel", () => {
  it("shows an empty state with no history", () => {
    render(<HistoryPanel history={[]} />);
    expect(screen.getByText(/No commands yet/)).toBeInTheDocument();
  });

  it("renders history entries with tier labels", () => {
    const history = [
      { id: 1, intent: "open_app", response: "Launched firefox", success: true, tier: 2, ts: Date.now() },
      { id: 2, intent: "delete_file", response: "Deleted test.txt", success: true, tier: 3, ts: Date.now() },
    ];
    render(<HistoryPanel history={history} />);
    expect(screen.getByText("open_app")).toBeInTheDocument();
    expect(screen.getByText("Launched firefox")).toBeInTheDocument();
    expect(screen.getByText(/Tier 2/)).toBeInTheDocument();
    expect(screen.getByText(/Tier 3/)).toBeInTheDocument();
  });

  it("marks failed commands distinctly from successful ones", () => {
    const history = [
      { id: 1, intent: "run_command", response: "Command failed", success: false, tier: 3, ts: Date.now() },
    ];
    const { container } = render(<HistoryPanel history={history} />);
    expect(container.querySelector(".history-item.failure")).not.toBeNull();
    expect(container.querySelector(".history-item.success")).toBeNull();
  });
});
