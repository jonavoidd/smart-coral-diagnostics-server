from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from app.db.connection import get_db
from app.core.security import Hasher
from app.utils.token import TokenSecurity
from app.crud.user import get_user_by_email, create_user
from app.schemas.token import Token
from app.schemas import user

router = APIRouter()


@router.post("/signin", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = get_user_by_email(db, form_data.username)
    if not user or not Hasher.verify_password(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="incorrect email or password")

    access_token = TokenSecurity.create_access_token({"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        user: {"name": user.name, "email": user.email},
    }


@router.post("/signup", response_model=Token)
def signup(user_data: user.CreateUser, db: Session = Depends(get_db)):
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="account already exists")

    hashed_pwd = Hasher.get_hashed_password(user_data.password)
    user = create_user(
        db,
        name=user_data.name,
        email=user_data.email,
        password=hashed_pwd,
        age=user_data.age,
        agree_to_terms=user_data.agree_to_terms,
    )

    # auto login after signup
    token = TokenSecurity.create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}
