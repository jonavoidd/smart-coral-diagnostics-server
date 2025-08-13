from fastapi import APIRouter

from app.jobs.deactivate_users import deactivate_inactive_users

router = APIRouter()


@router.post("/test/deactivate-users")
def test_deact_inactive():
    deactivate_inactive_users.delay()
    return {"message": "deactivate task sent"}
