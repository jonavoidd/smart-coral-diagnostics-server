import logging
import time
import torch

import numpy as np
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification
from typing import Any, Dict, Tuple

from app.core.config import settings
from app.schemas.coral_bleaching import (
    BleachingInferenceResult,
    BleachingPrediction,
    BleachingStatus,
)

logger = logging.getLogger(__name__)
LOG_MSG = "Service:"


class CoralBleachingInferenceService:
    def __init__(self):
        self.model = None
        self.processor = None
        self.model_version = None
        self.device = settings.MODEL_DEVICE

    async def load_model(self):
        try:
            if settings.CUSTOM_BLEACHING_MODEL_PATH:
                logger.info(
                    f"{LOG_MSG} loading custom bleaching model from {settings.CUSTOM_BLEACHING_MODEL_PATH}"
                )
                model_path = settings.BLEACHING_MODEL_NAME
            else:
                logger.info(
                    f"{LOG_MSG} loading base model: {settings.BLEACHING_MODEL_NAME}"
                )
                model_path = settings.BLEACHING_MODEL_NAME

            self.processor = AutoImageProcessor.from_pretrained(
                model_path, cache_dir=settings.BLEACHING_MODEL_CACHE_DIR
            )

            self.model = AutoModelForImageClassification.from_pretrained(
                model_path, cache_dir=settings.BLEACHING_MODEL_CACHE_DIR, num_labels=2
            )

            self.model.to(self.device)
            self.model.eval()
            self.model_version = f"{model_path}:v1.0"

            logger.info(
                f"{LOG_MSG} coral bleaching detection model loaded successfully"
            )
        except Exception as e:
            logger.error(f"{LOG_MSG} failed to load bleaching model: {str(e)}")

    async def predict_bleaching(
        self, image: Image.Image, confidence_threshold: float = 0.7
    ) -> BleachingInferenceResult:
        if not self.model:
            await self.load_model()

        start_time = time.time()

        try:
            inputs = self.processor(image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model(**inputs)
                probabilities = torch.nn.functional.softmax(outputs.logits[0], dim=0)

            healthy_prob = float(probabilities[0])
            bleached_prob = float(probabilities[1])

            if bleached_prob >= confidence_threshold:
                status = BleachingStatus.BLEACHED
                confidence = bleached_prob
            elif healthy_prob >= confidence_threshold:
                status = BleachingStatus.HEALTHY
                confidence = healthy_prob
            elif abs(bleached_prob - healthy_prob) < 0.2:
                status = BleachingStatus.PARTIALLY_BLEACHED
                confidence = max(healthy_prob, bleached_prob)
            else:
                status = BleachingStatus.UNCERTAIN
                confidence = max(healthy_prob, bleached_prob)

            prediction = BleachingPrediction(
                status=status,
                confidence=confidence,
                healthy_probability=healthy_prob,
                bleached_probability=bleached_prob,
            )

            processing_time = time.time() - start_time

            return BleachingInferenceResult(
                prediction=prediction,
                processing_time=processing_time,
                model_version=self.model_version,
                image_metadata={
                    "size": image.size,
                    "mode": image.mode,
                    "format": getattr(image, "format", None),
                },
            )
        except Exception as e:
            logger.error(f"{LOG_MSG} bleaching inference failed: {str(e)}")
            raise


coral_bleaching_inference_service = CoralBleachingInferenceService()
