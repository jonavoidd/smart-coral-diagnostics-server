from fastapi import APIRouter, UploadFile, File, HTTPException
from uuid import uuid4

from app.core.supabase_client import supabase

router = APIRouter()


@router.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)):
    """
    Uploads an image file to Supabase storage and returns its public URL.

    Args:
        file (UploadFile): The image file uploaded by the user. Supported types are PNG and JPEG/JPG.

    Returns:
        dict: A dictionary containing the unique filename and the public URL of the uploaded image.

    Raises:
        HTTPException:
            - 400: If the uploaded file is not a valid image type.
            - 500: If the upload to Supabase fails for any reason.
    """

    if file.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
        raise HTTPException(status_code=400, detail="invalid image type")

    # generate a unique file name
    file_ext = file.filename.split(".")[-1]
    filename = f"{uuid4().hex}.{file_ext}"
    file_bytes = await file.read()

    # upload image to supabase storage
    try:
        supabase.storage.from_("coral-images").upload(
            path=filename,
            file=file_bytes,
            file_options={"content-type": file.content_type},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to upload image: {e}")

    # get public url
    public_url = supabase.storage.from_("coral-images").get_public_url(filename)

    return {"filename": filename, "url": public_url}
