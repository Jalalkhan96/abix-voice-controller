from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger("abix.voiceprint")


@dataclass
class VoiceProfile:
    name: str
    embedding: list[float]
    created_at: str = ""


class VoiceprintVerifier:
    def __init__(self, data_dir: str = "data") -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._profiles_file = self._data_dir / "voiceprints.json"
        self._profiles: dict[str, VoiceProfile] = {}
        self._model = None
        self._load_profiles()

    def _load_profiles(self) -> None:
        if not self._profiles_file.exists():
            return
        try:
            with open(self._profiles_file) as f:
                data = json.load(f)
            for name, profile_data in data.items():
                self._profiles[name] = VoiceProfile(
                    name=name,
                    embedding=profile_data.get("embedding", []),
                    created_at=profile_data.get("created_at", ""),
                )
        except Exception as e:
            logger.warning("Failed to load voice profiles: %s", e)

    def _save_profiles(self) -> None:
        data = {
            name: {"embedding": p.embedding, "created_at": p.created_at}
            for name, p in self._profiles.items()
        }
        with open(self._profiles_file, "w") as f:
            json.dump(data, f, indent=2)

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        try:
            import numpy as np
            self._np = np
            self._model = True
            logger.info("Voiceprint verifier initialized (basic mode)")
        except ImportError:
            logger.warning("numpy not available for voiceprint")

    def enroll(self, name: str, audio_samples: list[bytes]) -> str:
        self._ensure_model()
        if not audio_samples:
            return "No audio samples provided."

        import numpy as np

        embeddings = []
        for sample in audio_samples:
            arr = np.frombuffer(sample, dtype=np.int16).astype(np.float32)
            embedding = self._extract_embedding(arr)
            if embedding is not None:
                embeddings.append(embedding)

        if not embeddings:
            return "Could not extract voice features from samples."

        avg_embedding = np.mean(embeddings, axis=0).tolist()

        from datetime import datetime, timezone
        self._profiles[name] = VoiceProfile(
            name=name,
            embedding=avg_embedding,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._save_profiles()
        return f"Voice profile enrolled for '{name}' with {len(embeddings)} samples."

    def verify(self, audio: bytes, threshold: float = 0.85) -> str | None:
        self._ensure_model()
        import numpy as np

        arr = np.frombuffer(audio, dtype=np.int16).astype(np.float32)
        embedding = self._extract_embedding(arr)
        if embedding is None:
            return None

        best_match = None
        best_score = 0.0

        for name, profile in self._profiles.items():
            profile_emb = np.array(profile.embedding)
            score = float(np.dot(embedding, profile_emb) / (
                np.linalg.norm(embedding) * np.linalg.norm(profile_emb) + 1e-8
            ))
            if score > best_score:
                best_score = score
                best_match = name

        if best_score >= threshold and best_match:
            logger.info("Voice verified: %s (score: %.3f)", best_match, best_score)
            return best_match

        return None

    def _extract_embedding(self, audio: "np.ndarray") -> "np.ndarray | None":  # type: ignore
        import numpy as np

        if len(audio) < 1600:
            return None

        chunk_size = 1600
        num_chunks = min(len(audio) // chunk_size, 50)
        features = []

        for i in range(num_chunks):
            chunk = audio[i * chunk_size : (i + 1) * chunk_size]
            features.extend([
                float(np.mean(chunk)),
                float(np.std(chunk)),
                float(np.max(np.abs(chunk))),
                float(np.median(np.abs(chunk))),
            ])

        embedding = np.array(features, dtype=np.float32)
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding

    def list_profiles(self) -> list[str]:
        return list(self._profiles.keys())

    def delete_profile(self, name: str) -> str:
        if name in self._profiles:
            del self._profiles[name]
            self._save_profiles()
            return f"Deleted voice profile '{name}'"
        return f"Profile '{name}' not found"

    @property
    def enabled(self) -> bool:
        return len(self._profiles) > 0
