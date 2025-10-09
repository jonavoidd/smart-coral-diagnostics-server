import logging
import secrets

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.oauth import oauth
from app.core.security import Hasher
from app.crud.user import (
    get_user_by_email,
    create_user,
    create_social_user,
    update_user_details,
)
from app.crud.user import update_user_details, modify_last_login
from app.crud.verify_token import (
    get_verification_token,
    store_verification_token,
    verify_token_and_mark_used,
)
from app.db.connection import get_db
from app.schemas.token import Token
from app.schemas.user import CreateUser, UpdateUser
from app.services.email_service import send_verification_email
from app.utils.token import TokenSecurity

router = APIRouter()
logger = logging.getLogger(__name__)
LOG_MSG = "Endpoint:"

ENV = settings.ENV

if ENV == "development":
    frontend_url = settings.FRONTEND_URL
    backend_url = settings.BACKEND_URL
else:
    frontend_url = settings.PROD_FRONTEND_URL
    backend_url = settings.PROD_BACKEND_URL


@router.post("/token")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    Authenticate a user using email and password, and return an access token if successful.

    <b>Args</b>:
        form_data (OAuth2PasswordRequestForm): The login credentials containing 'username' (email) and 'password'.
        db (Session): Database session dependency.

    <b>Returns</b>:
        dict: A dictionary containing the access token, token type, user's name, and email.

    <b>Raises</b>:
        HTTPException: If the user is not found, uses a non-local provider, or the password is incorrect.
    """
    try:
        user = get_user_by_email(db, form_data.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="incorrect email or password",
            )

        if user.provider != "local":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="please use social login for this acccount",
            )

        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="please verify your email first",
            )

        if not Hasher.verify_password(form_data.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="incorrect email or password",
            )

        name = f"{user.first_name} {user.last_name}"

        user_data = {
            "id": str(user.id),
            "is_verified": user.is_verified,
            "role": user.role,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }

        modify_last_login(db, user.id)

        access_token = TokenSecurity.create_access_token(
            user.email, user_data=user_data
        )
        response = JSONResponse(
            content={
                "message": "login successful",
                "access_token": access_token,
                "token_type": "bearer",
                "name": name,
                "email": user.email,
                "user_id": str(user.id),
                "role": user.role,
            }
        )

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="none",
            path="/",
            domain=".smart-coral-diagnostics.vercel.app",
            max_age=3600,
        )
        return response
    except Exception as e:
        logger.error(f"{LOG_MSG} error upon signin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="signin failed"
        )


@router.post("/refresh")
async def refresh_token(request: Request, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token missing"
        )

    payload = TokenSecurity.create_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token"
        )

    user = get_user_by_email(db, payload.get("sub"))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
        )

    user_data = {
        "id": user.id,
        "is_verified": user.is_verified,
        "role": user.role,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }

    new_access_token = TokenSecurity.create_access_token(
        subject=user.email, user_data=user_data
    )

    return {"access_token": new_access_token, "token_type": "bearer"}


@router.post("/signup", response_model=Token)
async def signup(user_data: CreateUser, db: Session = Depends(get_db)):
    """
    Register a new user with the provided details, then return an access token for immediate login.

    <b>Args</b>:
        user_data (user.CreateUser): The new user's registration data, including name, email, password, age, and agreement to terms.
        db (Session): Database session dependency.

    <b>Returns</b>:
        dict: A dictionary containing the access token, token type, user's name, and email.

    <b>Raises</b>:
        HTTPException: If an account with the given email already exists.
    """

    try:
        existing_user = get_user_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="account already exists"
            )

        hashed_pwd = Hasher.hash_password(user_data.password)
        user = create_user(
            db,
            payload=user_data,
            hashed_password=hashed_pwd,
        )

        verification_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.VERIFICATION_TOKEN_EXPIRE_HOURS
        )

        stored = store_verification_token(db, user.id, verification_token, expires_at)
        if not stored:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store verification token",
            )

        verification_url = (
            f"{backend_url}/api/v1/auth/verify-email?token={verification_token}"
        )

        name = f"{user_data.first_name} {user_data.last_name or ''}".strip()
        await send_verification_email(
            user_data.email, name, verification_url, expires_at
        )

        # auto login after signup
        access_token = TokenSecurity.create_access_token(user.email)
        response = JSONResponse(
            content={
                "message": "login successful",
                "access_token": access_token,
                "name": name,
                "email": user.email,
            }
        )
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="none",
        )
        return response
    except Exception as e:
        logger.error(f"{LOG_MSG} error upon signin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="signup failed"
        )


@router.get("/provider/{provider}")
async def social_auth(provider: str, request: Request):
    """
    Initiates OAuth2 authorization flow with the specified social provider.

    <b>Args</b>:
        provider (str): The name of the social login provider (currently only 'google' is supported).
        request (Request): The incoming HTTP request, used to generate the redirect URI.

    <b>Returns</b>:
        Response: A redirect response to the provider's OAuth2 authorization URL.

    <b>Raises</b>:
        HTTPException: If the provider is not supported.
    """

    if provider not in ["google"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported provider"
        )

    client = oauth.create_client(provider)
    redirect_uri = request.url_for("social_callback", provider=provider)
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/{provider}/callback")
async def social_callback(
    provider: str, request: Request, db: Session = Depends(get_db)
):
    """
    Handles the OAuth2 callback from a social provider, retrieves user info, and logs the user in.

    <b>Args</b>:
        provider (str): The name of the social login provider (e.g., 'google').
        request (Request): The HTTP request containing the authorization response from the provider.
        db (Session): The SQLAlchemy database session dependency.

    <b>Returns</b>:
        RedirectResponse: Redirects the user to the frontend with an access token as query parameters.

    <b>Raises</b>:
        HTTPException: If the authentication fails, the provider is unsupported,
                       or user information (like email) is not provided.
    """

    client = oauth.create_client(provider)

    try:
        token = await client.authorize_access_token(request)

        if provider == "google":
            user_info = token.get("userinfo")
            if not user_info:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo", token=token
                )
                user_info = response.json()

        email = user_info.get("email")
        first_name = user_info.get("given_name")
        last_name = user_info.get("family_name")
        profile = user_info.get("picture")
        provider_id = user_info.get("sub") or user_info.get("id")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email not provided by social platform provider",
            )

        existing_user = get_user_by_email(db, email)

        if existing_user:
            if existing_user.provider == "local":
                user = UpdateUser(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    provider=provider,
                    provider_id=provider_id,
                    profile=profile,
                    is_verified=True,
                )

                update_user_details(db=db, id=existing_user.id, payload=user)
            else:
                user = existing_user

        else:
            user = create_social_user(
                db=db,
                first_name=first_name,
                last_name=last_name,
                email=email,
                provider=provider,
                provider_id=provider_id,
                profile=profile,
            )

        user_data = {
            "id": str(user.id),
            "is_verified": user.is_verified,
            "role": user.role,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }

        access_token = TokenSecurity.create_access_token(
            user.email, user_data=user_data
        )

        # frontend_url = f"http://localhost:8000/api/v1/auth/callback?token={access_token}&name={user.name}&email={user.email}"
        response = RedirectResponse(frontend_url)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,
            samesite="lax",
            path="/",
            max_age=3600,
        )

        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {str(e)}",
        )


# Verify Email
@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    try:
        verification_token = get_verification_token(db, token)

        if not verification_token:
            return RedirectResponse(f"{frontend_url}/verify-email?status=failed")

        # Actually verify the user and mark the token as used
        success = verify_token_and_mark_used(db, verification_token)

        if not success:
            return RedirectResponse(f"{frontend_url}/verify-email?status=failed")

        return RedirectResponse(f"{frontend_url}/verify-email?status=succeeded")
    except Exception as e:
        logger.error(f"{LOG_MSG} error verifying email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="email verification failed",
        )


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key="access_token", httponly=True, secure=True, samesite="none", path="/"
    )
    return {"message": "logged out"}
