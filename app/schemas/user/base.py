from pydantic import BaseModel, EmailStr, constr
from typing import Optional
from datetime import datetime

class BaseSlugModel(BaseModel):
    slug: Optional[constr(min_length=3, max_length=50, pattern=r'^[a-z0-9-]+$')] = None

class Token(BaseModel):
    access_token: str
    token_type: str