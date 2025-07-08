from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from starlette.config import Config

config = Config(".env")
oauth = OAuth(config)


try:
    oauth.register(
        name="google",
        client_id=config("GOOGLE_CLIENT_ID"),
        client_secret=config("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid_configuration",
        client_kwargs={"scope": "openid email profile"},
    )
except Exception as e:
    print(f"OAuth2 not configured: {e}")
    OAUTH_ENABLED = False
