from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger("abix.hand_tracking")


@dataclass
class HandLandmarks:
    index_tip: tuple[float, float]
    index_mcp: tuple[float, float]
    thumb_tip: tuple[float, float]
    middle_tip: tuple[float, float]
    wrist: tuple[float, float]
    all_points: list[tuple[float, float]]


class HandTracker:
    def __init__(self, max_hands: int = 1, min_detection_confidence: float = 0.7) -> None:
        self._max_hands = max_hands
        self._min_detection_confidence = min_detection_confidence
        self._hands = None
        self._mp_drawing = None
        self._mp_hands = None
        self._init_mediapipe()

    def _init_mediapipe(self) -> None:
        try:
            import mediapipe as mp
            self._mp_hands = mp.solutions.hands
            self._mp_drawing = mp.solutions.drawing_utils
            self._hands = self._mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=self._max_hands,
                min_detection_confidence=self._min_detection_confidence,
                min_tracking_confidence=0.5,
            )
            logger.info("MediaPipe Hands initialized")
        except ImportError:
            logger.error("mediapipe not installed")
        except Exception as e:
            logger.error("Failed to init MediaPipe: %s", e)

    def process_frame(self, frame: np.ndarray) -> HandLandmarks | None:
        if self._hands is None:
            return None

        import cv2
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb)

        if not results.multi_hand_landmarks:
            return None

        hand_landmarks = results.multi_hand_landmarks[0]
        h, w = frame.shape[:2]

        def to_px(landmark) -> tuple[float, float]:
            return (landmark.x * w, landmark.y * h)

        points = [to_px(lm) for lm in hand_landmarks.landmark]

        return HandLandmarks(
            index_tip=points[8],
            index_mcp=points[5],
            thumb_tip=points[4],
            middle_tip=points[12],
            wrist=points[0],
            all_points=points,
        )

    def draw_landmarks(self, frame: np.ndarray, landmarks: HandLandmarks) -> np.ndarray:
        if self._mp_drawing is None or self._hands is None:
            return frame

        import cv2
        import mediapipe as mp

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb)
        if results.multi_hand_landmarks:
            for hand_lm in results.multi_hand_landmarks:
                self._mp_drawing.draw_landmarks(
                    frame, hand_lm, self._mp_hands.HAND_CONNECTIONS
                )
        return frame

    def close(self) -> None:
        if self._hands:
            self._hands.close()
            self._hands = None
