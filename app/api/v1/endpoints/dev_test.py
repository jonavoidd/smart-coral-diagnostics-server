from fastapi import APIRouter

from app.jobs.deactivate_users import deactivate_inactive_users
from app.services.email_service import email_service

router = APIRouter()


@router.post("/test/deactivate-users")
def test_deact_inactive():
    deactivate_inactive_users.delay()
    return {"message": "deactivate task sent"}


@router.get("/test-email")
async def test_email():
    ok = await email_service.send_email(
        to_email="test@yopmail.com",
        subject="✅ SendGrid Test from FastAPI on Render",
        html_content="<h3>Hello from SendGrid!</h3><p>This was sent via FastAPI on Render.</p>",
        text_content="Hello from SendGrid!",
    )
    return {"success": ok}
