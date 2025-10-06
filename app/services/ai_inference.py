import json
import logging
import requests
import time
import torch

from datetime import datetime
from fastapi import HTTPException, status
from io import BytesIO
from huggingface_hub import hf_hub_download
from pathlib import Path
from PIL import Image
import torch
from torch import nn
from torchvision import transforms
from torchvision.models import googlenet, GoogLeNet_Weights
from transformers import pipeline
from typing import Dict

from app.core.config import settings

logger = logging.getLogger(__name__)
LOG_MSG = "Service:"

BASE_DIR = Path(__file__).resolve().parent.parent
# coral_classification_model = BASE_DIR / "ai_model" / "coral_classification_model.pt"
googlenet_model = BASE_DIR / "ai_model" / "coral_classification_model_googlenet.pt"


device = "cuda" if torch.cuda.is_available() else "cpu"
transform = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)

model = None
class_names = None
model_version = "coral-classification-v3-googlenet"


class CoralBleachingModel(nn.Module):
    """GoogleNet-based model for coral bleaching detection with classification and regression outputs."""

    def __init__(self, num_classes=6, pretrained=True):
        super(CoralBleachingModel, self).__init__()

        # Load Pretrained GoogleNet
        if pretrained:
            self.backbone = googlenet(
                weights=GoogLeNet_Weights.IMAGENET1K_V1
            )  # Corrected weights name
        else:
            self.backbone = googlenet(weights=None)

        # Modify the final layer
        num_features = self.backbone.fc.in_features

        # Replace the final fully connected layer
        self.backbone.fc = nn.Identity()

        # Classification head
        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(num_features, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes),
        )

        # Regression head for bleaching percentage
        self.regressor = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(num_features, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        features = self.backbone(x)
        class_output = self.classifier(features)
        bleaching_output = self.regressor(features) * 100  # Scale to percentage
        return class_output, bleaching_output


def load_model():
    global model, class_names
    if model is None:
        checkpoint = torch.load(
            "app/ai_model/coral_classification_model_googlenet.pt", map_location=device
        )
        model = CoralBleachingModel(
            num_classes=checkpoint["num_classes"], pretrained=False
        )
        model.load_state_dict(checkpoint["model_state_dict"], strict=False)
        model.eval()
        model.to(device)
        class_names = checkpoint["class_names"]
        print("✅ Model loaded successfully.")

    return model, class_names


# class CoralBleachingModel(nn.Module):
#     """ResNet50-based model for coral bleaching detection with classification and regression outputs."""

#     def __init__(self, num_classes=5, pretrained=True):
#         super(CoralBleachingModel, self).__init__()

#         # Load Pretrained ResNet50
#         if pretrained:
#             self.backbone = resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)
#         else:
#             self.backbone = resnet50(weights=None)

#         # Modify the final layer
#         num_features = self.backbone.fc.in_features
#         self.backbone.fc = nn.Identity()

#         # Classification head
#         self.classifier = nn.Sequential(
#             nn.Dropout(0.5),
#             nn.Linear(num_features, 512),
#             nn.ReLU(),
#             nn.Dropout(0.3),
#             nn.Linear(512, num_classes),
#         )

#         # Regression head for bleaching percentage
#         self.regressor = nn.Sequential(
#             nn.Dropout(0.5),
#             nn.Linear(num_features, 256),
#             nn.ReLU(),
#             nn.Dropout(0.3),
#             nn.Linear(256, 1),
#             nn.Sigmoid(),
#         )

#     def forward(self, x):
#         features = self.backbone(x)
#         class_output = self.classifier(features)
#         bleaching_output = self.regressor(features) * 100  # Scale to percentage
#         return class_output, bleaching_output


# checkpoint = torch.load(googlenet_model, map_location=device, weights_only=False)
# state_dict = checkpoint["model_state_dict"]

# num_classes = checkpoint["num_classes"]
# class_names = checkpoint["class_names"]

# model = CoralBleachingModel(num_classes=6, pretrained=False)
# model.load_state_dict(state_dict, strict=False)
# model.eval()
# model = model.to(device)


def run_inference(image_path: str) -> Dict:
    start_time = time.time()
    try:
        if image_path.startswith("http://") or image_path.startswith("https://"):
            res = requests.get(image_path)
            res.raise_for_status()
            image = Image.open(BytesIO(res.content)).convert("RGB")
        else:
            image = Image.open(image_path).convert("RGB")

        input_tensor = transform(image).unsqueeze(0).to(device)

        with torch.no_grad():
            class_logits, bleaching_output = model(input_tensor)
            probs = torch.softmax(class_logits, dim=1)
            predicted_idx = torch.argmax(probs, dim=1).item()
            predicted_label = class_names[predicted_idx]
            confidence_score = probs[0][predicted_idx].item()
            bleaching_percentage = bleaching_output.item()

        return {
            "classification_labels": predicted_label,
            "confidence_score": round(confidence_score, 4),
            "bleaching_percentage": round(bleaching_percentage, 2),
            "bounding_boxes": None,
            "model_version": model_version,
            "analysis_duration": round(time.time() - start_time, 4),
        }

        # result = model(image)
        # top = max(result, key=lambda x: x["score"])

        # return {
        #     "classification_labels": LABEL_MAP.get(top["label"], top["label"]),
        #     "confidence_score": float(top["score"]),
        #     "bounding_box": None,
        #     "model_version": MODEL_ID,
        #     "analysis_duration": time.time() - start_time,
        # }

        # return {
        #     "classification_labels": top["label"],
        #     "confidence_score": float(top["score"]),
        #     "bounding_boxes": None,
        #     "model_version": MODEL_ID,
        #     "analysis_duration": time.time() - start_time,
        # }

    except Exception as e:
        logger.error(f"error making an inference on image: {str(e)}")
        raise RuntimeError(f"inference failed: {str(e)}")


def run_llm_inference(
    latitude: float,
    longitude: float,
    classification: str,
    bleaching_percentage: float,
    water_temp: str,
    water_depth: float,
    observation_date: datetime,
):
    prompt = f"""
    A coral image was captured at latitude {latitude}, longitude {longitude}, and has been classified as: {classification} with a bleaching percent of {bleaching_percentage}%.
    At the time of observation on {observation_date}, the water temperature was {water_temp} at a depth of {water_depth} meters.

    Please provide the following in your response:

    1. **Explain the classification result** in simple terms for the user who submitted the image:
    - If the classification is "not corals", clearly explain that the subject in the image is not a coral.
    - Otherwise, explain what the classification means for the coral's health or condition.
    2. **Discuss potential environmental issues** in the general region (no need to mention exact coordinates) that could have contributed to this classification result.
    3. **Describe how these environmental factors** may affect the local marine ecosystem and the broader ecological consequences.
    4. **Suggest a list of actionable recommendations** that the user or local community can take to help address or reduce these environmental impacts.

    Please structure your response with the following two clear sections:

    - **Description**:
    [Your detailed explanation goes here]

    - **Recommended Actions**:
    - [Action 1]
    - [Action 2]
    - [Action 3]
    ...
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
                    # uncomment openrouter and comment apitogether when using the models below
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
