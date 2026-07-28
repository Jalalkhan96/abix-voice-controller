from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger("abix.virtual_mouse")


@dataclass
class MouseState:
    x: float
    y: float
    left_down: bool = False
    scrolling: bool = False


class VirtualMouse:
    def __init__(
        self,
        smoothing: float = 0.7,
        click_threshold: float = 0.03,
        scroll_threshold: float = 0.05,
        screen_margin: float = 0.05,
    ) -> None:
        self._smoothing = smoothing
        self._click_threshold = click_threshold
        self._scroll_threshold = scroll_threshold
        self._screen_margin = screen_margin

        self._state = MouseState(x=0.5, y=0.5)
        self._prev_index_tip = None
        self._prev_middle_tip = None
        self._click_cooldown = 0.0
        self._scroll_accumulator = 0.0

        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            pyautogui.PAUSE = 0
            self._screen_w, self._screen_h = pyautogui.size()
            self._pyautogui = pyautogui
            logger.info("Virtual mouse: screen %dx%d", self._screen_w, self._screen_h)
        except Exception as e:
            logger.warning("pyautogui not available: %s", e)
            self._pyautogui = None
            self._screen_w = 1920
            self._screen_h = 1080

    def update(self, landmarks) -> None:
        if landmarks is None:
            return

        from agent.hand_tracking import HandLandmarks
        if not isinstance(landmarks, HandLandmarks):
            return

        now = time.time()

        index_x, index_y = landmarks.index_tip
        thumb_x, thumb_y = landmarks.thumb_tip
        middle_x, middle_y = landmarks.middle_tip

        norm_x = max(0.0, min(1.0, index_x / self._screen_w if self._screen_w > 0 else index_x))
        norm_y = max(0.0, min(1.0, index_y / self._screen_h if self._screen_h > 0 else index_y))

        if self._prev_index_tip is not None:
            smooth_x = self._prev_index_tip[0] * self._smoothing + norm_x * (1 - self._smoothing)
            smooth_y = self._prev_index_tip[1] * self._smoothing + norm_y * (1 - self._smoothing)
        else:
            smooth_x, smooth_y = norm_x, norm_y

        self._prev_index_tip = (smooth_x, smooth_y)
        self._move_cursor(smooth_x, smooth_y)

        pinch_dist = math.sqrt(
            (index_x - thumb_x) ** 2 + (index_y - thumb_y) ** 2
        ) / max(self._screen_w, self._screen_h)

        if pinch_dist < self._click_threshold and now - self._click_cooldown > 0.3:
            self._click()
            self._click_cooldown = now

        if self._prev_middle_tip is not None:
            scroll_delta = middle_y - self._prev_middle_tip[1]
            self._scroll_accumulator += scroll_delta
            if abs(self._scroll_accumulator) > self._scroll_threshold * self._screen_h:
                direction = -1 if self._scroll_accumulator > 0 else 1
                self._scroll(direction)
                self._scroll_accumulator = 0.0
        self._prev_middle_tip = (middle_x, middle_y)

    def _move_cursor(self, norm_x: float, norm_y: float) -> None:
        if self._pyautogui is None:
            return
        margin = self._screen_margin
        x = margin + norm_x * (1 - 2 * margin)
        y = margin + norm_y * (1 - 2 * margin)
        px = int(x * self._screen_w)
        py = int(y * self._screen_h)
        try:
            self._pyautogui.moveTo(px, py, _pause=False)
        except Exception:
            pass

    def _click(self) -> None:
        if self._pyautogui is None:
            return
        try:
            self._pyautogui.click(_pause=False)
            logger.debug("Virtual click")
        except Exception:
            pass

    def _scroll(self, direction: int) -> None:
        if self._pyautogui is None:
            return
        try:
            self._pyautogui.scroll(direction * 3, _pause=False)
            logger.debug("Virtual scroll: %d", direction)
        except Exception:
            pass
