import json
import logging
import requests
import time
import torch

from fastapi import HTTPException, status
from io import BytesIO
from huggingface_hub import hf_hub_download
from PIL import Image
from torch import nn
from torchvision import models, transforms
from transformers import pipeline
from typing import Dict

from app.core.config import settings

logger = logging.getLogger(__name__)
LOG_MSG = "Service:"


# class CoralBleachingModel(nn.Module):
#     """ResNet50-based model for coral bleaching detection"""

#     def __init__(self, num_classes=2, pretrained=True):
#         super(CoralBleachingModel, self).__init__()

#         # Load Pretained ResNet50
#         if pretrained:
#             self.backbone = models.resnet50(
#                 weights=models.ResNet50_Weights.IMAGENET1K_V2
#             )
#         else:
#             self.backbone = models.resnet50(weights=None)

#         # Modify the fianl layer
#         num_features = self.backbone.fc.in_features
#         self.backbone.fc = nn.Sequential(
#             nn.Dropout(0.5),
#             nn.Linear(num_features, 512),
#             nn.ReLU(),
#             nn.Dropout(0.3),
#             nn.Linear(512, num_classes),
#         )

#     def forward(self, x):
#         return self.backbone(x)


# MODEL_FILENAME = settings.HF_MODEL_FILENAME
# MODEL_ID = f"{settings.HF_USERNAME}/{settings.HF_MODEL_NAME}"
# model_path = hf_hub_download(repo_id=MODEL_ID, filename=MODEL_FILENAME)

# model = CoralBleachingModel(num_classes=2)
# model.load_state_dict(torch.load(model_path, map_location="cpu"))
# model.eval()

# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# model.to(device)
# # model = pipeline("image-classification", model=MODEL_ID, device=device)

# transform = transforms.Compose(
#     [
#         transforms.Resize((224, 224)),
#         transforms.ToTensor(),
#         transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
#     ]
# )

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
    A coral image taken from latitude: {latitude}, longitude: {longitude} was classified as {classification}.
    1. Please explain the classification result to the user who uploaded the image.
    2. Describe the possible environmental issues in the region that may have caused this result, no need to mention the latitude and longitude anymore and only the general area.
    3. Explain how these issues could affect the local marine ecosystem and their broader impacts.
    4. Finally, provide a list of recommended actions that the user or community could take to help mitigate these issues.
       Present this list in bullet points.

    Please structure your response clearly with two sections:
    - Description:
      [Your explanation here]
    - Recommended Actions:
      - Action 1
      - Action 2
      - ...
    """
    try:
        response = requests.post(
            # url="https://openrouter.ai/api/v1/chat/completions",
            url="https://api.together.xyz/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.TOGETHER_AI_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps(
                {
                    "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
                    # "model": "deepseek/deepseek-chat-v3-0324:free",
                    # "model": "moonshotai/kimi-k2:free",
                    # "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
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
                    "temperature": 0.5,
                    "max_tokens": 512,
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
