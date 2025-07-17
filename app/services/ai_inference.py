import requests
import time
import torch

from io import BytesIO
from PIL import Image
from transformers import pipeline
from typing import Dict

from app.core.config import settings


MODEL_ID = f"{settings.HF_USERNAME}/{settings.HF_MODEL_NAME}"


device = 0 if torch.cuda.is_available() else -1
model = pipeline("image-classification", model=MODEL_ID, device=device)


LABEL_MAP = {
    "51_tabular_hard_coral": "Tabular Hard Coral",
    "polar white bleaching": "Polar White Bleaching",
    "slight pale bleaching": "Slight Pale Bleaching",
    "very pale bleaching": "Very Pale Bleaching",
}


def run_inference(image_path: str) -> Dict:
    start_time = time.time()
    try:
        if image_path.startswith("http://") or image_path.startswith("https://"):
            res = requests.get(image_path)
            res.raise_for_status()
            image = Image.open(BytesIO(res.content)).convert("RGB")
        else:
            image = Image.open(image_path).convert("RGB")

        result = model(image)
        top = max(result, key=lambda x: x["score"])

        # return {
        #     "classification_labels": LABEL_MAP.get(top["label"], top["label"]),
        #     "confidence_score": float(top["score"]),
        #     "bounding_box": None,
        #     "model_version": MODEL_ID,
        #     "analysis_duration": time.time() - start_time,
        # }

        return {
            "classification_labels": top["label"],
            "confidence_score": float(top["score"]),
            "bounding_boxes": None,
            "model_version": MODEL_ID,
            "analysis_duration": time.time() - start_time,
        }

    except Exception as e:
        raise RuntimeError(f"inference failed: {str(e)}")
