import { render, screen, fireEvent } from "@testing-library/react";
import ToastStack from "./ToastStack";

describe("ToastStack", () => {
  it("renders nothing when there are no toasts", () => {
    const { container } = render(<ToastStack toasts={[]} onDismiss={jest.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders a toast per entry", () => {
    render(
      <ToastStack
        toasts={[
          { id: 1, message: "Command blocked: dangerous pattern" },
          { id: 2, message: "Command failed: file not found" },
        ]}
        onDismiss={jest.fn()}
      />
    );
    expect(screen.getByText(/Command blocked/)).toBeInTheDocument();
    expect(screen.getByText(/Command failed/)).toBeInTheDocument();
  });

  it("calls onDismiss with the toast id when its close button is clicked", () => {
    const onDismiss = jest.fn();
    render(
      <ToastStack toasts={[{ id: 42, message: "oops" }]} onDismiss={onDismiss} />
    );
    fireEvent.click(screen.getByLabelText("Dismiss"));
    expect(onDismiss).toHaveBeenCalledWith(42);
  });
});
