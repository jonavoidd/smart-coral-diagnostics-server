from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.oauth import oauth
from app.core.security import Hasher
from app.crud.user import (
    get_user_by_email,
    create_user,
    create_social_user,
    update_user_details,
)
from app.db.connection import get_db
from app.schemas.token import Token
from app.schemas import user
from app.utils.token import TokenSecurity

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@router.get("/index")
def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    payload = TokenSecurity.decode_access_token(token)
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=400, detail="invalid token")

    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=400, detail="user not found")

    return user


@router.post("/token", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    Authenticate a user using email and password, and return an access token if successful.

    Args:
        form_data (OAuth2PasswordRequestForm): The login credentials containing 'username' (email) and 'password'.
        db (Session): Database session dependency.

    Returns:
        dict: A dictionary containing the access token, token type, user's name, and email.

    Raises:
        HTTPException: If the user is not found, uses a non-local provider, or the password is incorrect.
    """

    user = get_user_by_email(db, form_data.username)
    if not user:
        raise HTTPException(status_code=400, detail="incorrect email or password")

    if user.provider != "local":
        raise HTTPException(
            status_code=400, detail="please use social login for this acccount"
        )

    if not Hasher.verify_password(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="incorrect email or password")

    access_token = TokenSecurity.create_access_token({"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "name": user.name,
        "email": user.email,
    }


@router.post("/signup", response_model=Token)
def signup(user_data: user.CreateUser, db: Session = Depends(get_db)):
    """
    Register a new user with the provided details, then return an access token for immediate login.

    Args:
        user_data (user.CreateUser): The new user's registration data, including name, email, password, age, and agreement to terms.
        db (Session): Database session dependency.

    Returns:
        dict: A dictionary containing the access token, token type, user's name, and email.

    Raises:
        HTTPException: If an account with the given email already exists.
    """

    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="account already exists")

    hashed_pwd = Hasher.hash_password(user_data.password)
    user = create_user(
        db,
        name=user_data.name,
        email=user_data.email,
        password=hashed_pwd,
        provider="local",
        age=user_data.age,
        agree_to_terms=user_data.agree_to_terms,
    )

    # auto login after signup
    token = TokenSecurity.create_access_token({"sub": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "name": user.name,
        "email": user.email,
    }


@router.get("/auth/{provider}")
async def social_auth(provider: str, request: Request):
    """
    Initiates OAuth2 authorization flow with the specified social provider.

    Args:
        provider (str): The name of the social login provider (currently only 'google' is supported).
        request (Request): The incoming HTTP request, used to generate the redirect URI.

    Returns:
        Response: A redirect response to the provider's OAuth2 authorization URL.

    Raises:
        HTTPException: If the provider is not supported.
    """

    if provider not in ["google"]:
        raise HTTPException(status_code=400, detail="unsupported provider")

    client = oauth.create_client(provider)
    redirect_uri = request.url_for("social_callback", provider=provider)
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/auth/{provider}/callback")
async def social_callback(
    provider: str, request: Request, db: Session = Depends(get_db)
):
    """
    Handles the OAuth2 callback from a social provider, retrieves user info, and logs the user in.

    Args:
        provider (str): The name of the social login provider (e.g., 'google').
        request (Request): The HTTP request containing the authorization response from the provider.
        db (Session): The SQLAlchemy database session dependency.

    Returns:
        RedirectResponse: Redirects the user to the frontend with an access token as query parameters.

    Raises:
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
                    "https://googleapis.com/oauth2/v2/userinfo", token=token
                )
                user_info = response.json()

        email = user_info.get("email")
        name = user_info.get("name")
        provider_id = user_info.get("sub") or user_info.get("id")

        if not email:
            raise HTTPException(
                status_code=400, detail="email not provided by social platform provider"
            )

        existing_user = get_user_by_email(db, email)

        if existing_user:
            if existing_user.provider == "local":
                user = update_user_details(
                    db=db,
                    name=name,
                    email=email,
                    provider=provider,
                    provider_id=provider_id,
                )
            else:
                user = create_social_user(
                    db=db,
                    name=name,
                    email=email,
                    provider=provider,
                    provider_id=-provider_id,
                )

            access_token = TokenSecurity.create_access_token({"sub": user.email})

            frontend_url = f"http://localhost:8000/api/v1/auth/callback?token={access_token}&name{user.name}&email={user.email}"
            return RedirectResponse(frontend_url)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")
