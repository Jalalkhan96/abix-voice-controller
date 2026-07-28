from __future__ import annotations

import json
import logging
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger("abix.wakeword_train")


@dataclass
class WakeWordModel:
    name: str
    phrase: str
    model_path: str
    created_at: str = ""


class WakeWordTrainer:
    def __init__(self, data_dir: str = "data/wakewords") -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._models_file = self._data_dir / "models.json"
        self._models: list[WakeWordModel] = []
        self._load_models()

    def _load_models(self) -> None:
        if not self._models_file.exists():
            return
        try:
            with open(self._models_file) as f:
                data = json.load(f)
            self._models = [WakeWordModel(**m) for m in data]
        except Exception as e:
            logger.warning("Failed to load wake word models: %s", e)

    def _save_models(self) -> None:
        data = [
            {"name": m.name, "phrase": m.phrase, "model_path": m.model_path, "created_at": m.created_at}
            for m in self._models
        ]
        with open(self._models_file, "w") as f:
            json.dump(data, f, indent=2)

    def start_training(self, phrase: str, name: str | None = None) -> str:
        model_name = name or phrase.replace(" ", "_").lower()
        model_dir = self._data_dir / model_name
        model_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Starting wake word training for phrase: '%s'", phrase)

        try:
            from openwakeword.utils.download import download_models
            download_models()
        except Exception as e:
            logger.debug("openwakeword download: %s", e)

        return (
            f"Training wake word '{phrase}' is a multi-step process.\n"
            f"1. Record 5-10 audio samples of yourself saying '{phrase}'\n"
            f"2. Place them in: {model_dir}\n"
            f"3. Run: python -m openwakeword.training --data {model_dir} --output {model_dir}/model.onnx\n"
            f"\nSamples directory: {model_dir}"
        )

    def list_models(self) -> str:
        if not self._models:
            return "No custom wake word models."
        lines = ["Custom wake word models:"]
        for m in self._models:
            lines.append(f"  - {m.name}: '{m.phrase}' ({m.model_path})")
        return "\n".join(lines)

    def delete_model(self, name: str) -> str:
        for i, m in enumerate(self._models):
            if m.name == name:
                model_path = Path(m.model_path)
                if model_path.exists():
                    import shutil
                    shutil.rmtree(model_path.parent, ignore_errors=True)
                self._models.pop(i)
                self._save_models()
                return f"Deleted wake word model '{name}'"
        return f"Model '{name}' not found"

    def register_model(self, name: str, phrase: str, model_path: str) -> str:
        from datetime import datetime, timezone
        model = WakeWordModel(
            name=name,
            phrase=phrase,
            model_path=model_path,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._models.append(model)
        self._save_models()
        return f"Registered wake word model '{name}' for phrase '{phrase}'"
