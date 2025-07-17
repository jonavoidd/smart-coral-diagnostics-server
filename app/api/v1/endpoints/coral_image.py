from fastapi import (
    APIRouter,
    Body,
    Form,
    UploadFile,
    File,
    HTTPException,
    Depends,
    status,
)
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.auth import require_role
from app.core.supabase_client import supabase
from app.db.connection import get_db
from app.models.users import UserRole
from app.schemas.coral_image import CoralImageOut
from app.schemas.user import UserOut
from app.services.coral_image_service import (
    upload_image_to_supabase_service,
    get_all_images_service,
    get_image_for_user_service,
    get_single_image_service,
    delete_single_image_service,
    delete_multiple_images_service,
)
from app.services.image_processing import (
    validate_image,
    optimize_for_storage,
)

router = APIRouter()


@router.post("/")
async def analyze_coral_image(
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(require_role([UserRole.USER, UserRole.ADMIN])),
):
    """
    Uploads an image file to Supabase storage and returns its public URL.

    <b>Args</b>:
        file (UploadFile): The image file uploaded by the user. Supported types are PNG and JPEG/JPG.

    <b>Returns</b>:
        dict: A dictionary containing the unique filename and the public URL of the uploaded image.

    <b>Raises</b>:
        HTTPException:
            - 400: If the uploaded file is not a valid image type.
            - 500: If the upload to Supabase fails for any reason.
    """

    validate_image(file)
    optimized = optimize_for_storage(file)

    try:
        return upload_image_to_supabase_service(
            db, optimized, file.filename, current_user.id, latitude, longitude
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/", response_model=List[CoralImageOut])
def get_all_images(db: Session = Depends(get_db)):
    """
    Retrieve a list of all coral images from the database.

    <b>Args</b>:
        db (Session): Database session dependency.

    <b>Returns</b>:
        List[CoralImageOut]: A list of coral image data transfer objects.
    """

    return get_all_images_service(db)


@router.get("/u/", response_model=List[CoralImageOut])
def get_user_images(
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(require_role([UserRole.USER, UserRole.ADMIN])),
):
    """
    Retrieve a list of coral images belonging to the currently authenticated user.

    <b>Args</b>:
        db (Session): Database session dependency.
        current_user (UserOut): The currently authenticated user, ensured to have USER or ADMIN role.

    <b>Returns</b>:
        List[CoralImageOut]: A list of coral images for the current user.
    """

    return get_image_for_user_service(db, current_user.id)


@router.get("/id/{id}", response_model=CoralImageOut)
def get_single_user_by_id(id: UUID, db: Session = Depends(get_db)):
    """
    Retrieve a single coral image by its unique ID.

    <b>Args</b>:
        id (UUID): The unique identifier of the coral image.
        db (Session): Database session dependency.

    <b>Returns</b>:
        CoralImageOut: The coral image data transfer object matching the given ID.
    """

    return get_single_image_service(db, id)


@router.delete("/id/{id}")
def delete_single_image(id: UUID, db: Session = Depends(get_db)):
    success = delete_single_image_service(db, id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )
    return {"deleted": id}


@router.delete("/images/")
def delete_single_image(ids: List[UUID] = Body(...), db: Session = Depends(get_db)):
    deleted_count = delete_multiple_images_service(db, ids)
    return {"deleted_count": deleted_count}
