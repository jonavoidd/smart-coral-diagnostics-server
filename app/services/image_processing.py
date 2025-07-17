import logging

from fastapi import UploadFile, HTTPException, status
from PIL import Image, UnidentifiedImageError
from io import BytesIO


MAX_IMAGE_DIMENSION = 1024
STORAGE_IMAGE_QUALITY = 85
AI_IMAGE_SIZE = (512, 512)
THUMBNAIL_SIZE = (256, 256)

logger = logging.getLogger(__name__)
LOG_MSG = "CRUD:"


def validate_image(file: UploadFile) -> None:
    try:
        image = Image.open(file.file)
        image.verify()
        file.file.seek(0)
    except (UnidentifiedImageError, OSError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid image file"
        )


def optimize_for_storage(file: UploadFile) -> bytes:
    try:
        image = Image.open(file.file)
        image = image.convert("RGB")
        image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))

        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=STORAGE_IMAGE_QUALITY)
        buffer.seek(0)

        return buffer.read()
    except Exception as e:
        logger.error(f"{LOG_MSG} failed to optimize image for storage: {str(e)}")


def prepare_for_ai(file: UploadFile) -> bytes:
    try:
        image = Image.open(file.file)
        image = image.convert("RGB")
        image = image.resize(AI_IMAGE_SIZE)

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        return buffer.read()
    except Exception as e:
        logger.error(f"{LOG_MSG} failed to prepare image for AI: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="image processing failed",
        )
    finally:
        file.file.seek(0)


def generate_thumbnail(file: UploadFile) -> bytes:
    try:
        image = Image.open(file.file)
        image = image.convert("RGB")
        image.thumbnail(THUMBNAIL_SIZE)

        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=80)
        buffer.seek(0)

        return buffer.read()
    except Exception as e:
        logger.error(f"{LOG_MSG} failed to generate thumbnail: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="thumbnail generation failed",
        )
    finally:
        file.file.seek(0)
