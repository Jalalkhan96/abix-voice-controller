import { render } from "@testing-library/react";
import MicLevelMeter from "./MicLevelMeter";

describe("MicLevelMeter", () => {
  it("renders one bar per configured weight", () => {
    const { container } = render(<MicLevelMeter level={0.5} active={true} />);
    expect(container.querySelectorAll(".mic-level-bar")).toHaveLength(5);
  });

  it("flattens bars to a low idle scale when inactive, regardless of level", () => {
    const { container } = render(<MicLevelMeter level={0.9} active={false} />);
    const bars = container.querySelectorAll(".mic-level-bar");
    bars.forEach((bar) => {
      expect(bar.style.transform).toBe("scaleY(0.15)");
      expect(bar.className).not.toMatch(/active/);
    });
  });

  it("scales bars up with level when active", () => {
    const { container } = render(<MicLevelMeter level={1} active={true} />);
    const bars = container.querySelectorAll(".mic-level-bar");
    bars.forEach((bar) => {
      expect(bar.className).toMatch(/active/);
      const scale = parseFloat(bar.style.transform.match(/scaleY\(([\d.]+)\)/)[1]);
      expect(scale).toBeGreaterThan(0.15);
    });
  });
});
