import json
import logging
import requests
import time
import torch

from fastapi import HTTPException, status
from io import BytesIO
from PIL import Image
from transformers import pipeline
from typing import Dict

from app.core.config import settings

logger = logging.getLogger(__name__)
LOG_MSG = "Service:"


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


def run_llm_inference(latitude: float, longitude: float, classification: str):
    prompt = f"""
    A coral image taken from latitude:{latitude}, longitude:{longitude} was classified as {classification}. 
    Explain the result to the user who uploaded the image and also explain 
    what possible environmental issues in the region caused such a result.
    Also add how such issues could affect the local marine ecosystem and
    its impact on a broader sense encompassing other possible affected locations.
    """
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPEN_ROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps(
                {
                    "model": "deepseek/deepseek-chat-v3-0324:free",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert marine biologist with years of experience helping users understand corals and coral bleaching.",
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                }
            ),
        )

        if response.status_code != 200:
            raise Exception(f"LLM API failed: {response.status_code} - {response.text}")

        return response.json()
    except Exception as e:
        logger.error(f"{LOG_MSG} LLM request failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed to send llm request",
        )
