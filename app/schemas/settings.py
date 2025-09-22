from pydantic import BaseModel
from typing import Optional


class Settings(BaseModel):
    is_public: Optional[bool]
