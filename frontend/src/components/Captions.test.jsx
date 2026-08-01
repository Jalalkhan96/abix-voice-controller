import { render, screen } from "@testing-library/react";
import Captions from "./Captions";

describe("Captions", () => {
  it("shows the prompt when there are no captions", () => {
    render(<Captions captions={[]} />);
    expect(screen.getByText(/Say "Hi ABIX" to begin/)).toBeInTheDocument();
  });

  it("renders the most recent captions with a role marker", () => {
    const captions = [
      { id: 1, role: "user", text: "open firefox" },
      { id: 2, role: "abix", text: "Launched firefox" },
    ];
    render(<Captions captions={captions} />);
    expect(screen.getByText(/open firefox/)).toBeInTheDocument();
    expect(screen.getByText(/Launched firefox/)).toBeInTheDocument();
  });

  it("only shows the last 5 captions", () => {
    const captions = Array.from({ length: 8 }, (_, i) => ({
      id: i,
      role: "user",
      text: `command ${i}`,
    }));
    render(<Captions captions={captions} />);
    expect(screen.queryByText("command 0")).not.toBeInTheDocument();
    expect(screen.queryByText("command 2")).not.toBeInTheDocument();
    expect(screen.getByText(/command 7/)).toBeInTheDocument();
    expect(screen.getByText(/command 3/)).toBeInTheDocument();
  });
});
