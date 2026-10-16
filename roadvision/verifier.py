"""Zero-shot image classification for suspected potholes."""

import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image, UnidentifiedImageError


MODEL_ID = os.environ.get("ROADVISION_MODEL", "openai/clip-vit-base-patch32")
POTHOLE_LABEL = "a road surface with a pothole"
OTHER_LABEL = "a road surface without a pothole"
MIN_POTHOLE_SCORE = 0.60
MIN_SCORE_MARGIN = 0.15


class ImageVerificationError(Exception):
    """Raised when an image is invalid or the AI model cannot run."""


@dataclass(frozen=True)
class VerificationResult:
    detected: bool
    confidence: float

    @property
    def display_text(self) -> str:
        return "Pothole Detected" if self.detected else "No Pothole Detected"


class PotholeVerifier:
    """Use a Hugging Face CLIP model to classify road images without training."""

    def __init__(self) -> None:
        self._classifier: Any = None
        self._lock = threading.Lock()

    def verify(self, image_path: Path) -> VerificationResult:
        """Validate an image and return whether the model detects a pothole."""
        path = Path(image_path)
        try:
            with Image.open(path) as image:
                image.verify()
        except (OSError, UnidentifiedImageError, ValueError) as error:
            raise ImageVerificationError("This file is not a valid, readable image.") from error

        try:
            with self._lock:
                if self._classifier is None:
                    from transformers import pipeline

                    self._classifier = pipeline(
                        "zero-shot-image-classification",
                        model=MODEL_ID,
                    )
                predictions: List[Dict[str, Any]] = self._classifier(
                    str(path), candidate_labels=[POTHOLE_LABEL, OTHER_LABEL]
                )
        except Exception as error:
            raise ImageVerificationError(
                "AI verification could not run. Check internet access for the first model download and "
                "confirm this device allows PyTorch to load. Details: "
                f"{error}"
            ) from error

        scores = {item["label"]: float(item["score"]) for item in predictions}
        pothole_score = scores.get(POTHOLE_LABEL, 0.0)
        other_score = scores.get(OTHER_LABEL, 0.0)
        detected = (
            pothole_score >= MIN_POTHOLE_SCORE
            and pothole_score - other_score >= MIN_SCORE_MARGIN
        )
        return VerificationResult(detected=detected, confidence=pothole_score)