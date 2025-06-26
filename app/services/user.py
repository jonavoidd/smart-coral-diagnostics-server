from uuid import UUID
from app.crud import user as user_crud
from app.schemas import user as user_schema


def create_user_service(user_data: user_schema.CreateUser):
    user_crud.create_user(**user_data.model_dump())
    return {"message": "user successfully created"}


def get_user_by_email_service(email: str) -> user_schema.UserOut:
    user_details = user_crud.get_user_by_email(email)
    return user_details


def get_user_by_id_service(id: UUID) -> user_schema.UserOut:
    user_details = user_crud.get_user_by_id(id)
    return user_details


def get_all_users_service() -> list[user_schema.UserOut]:
    return user_crud.get_all_users()


def update_user_details_service(id: UUID, update_data: user_schema.UpdateUser):
    user_crud.update_user_details(id, **update_data.model_dump())
    return {"message": "successfully updated user details"}


def delete_user_service(id: UUID):
    user_crud.delete_user(id)
    return {"message": "user successfully deleted"}
