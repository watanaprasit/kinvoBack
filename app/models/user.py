# from pydantic import BaseModel
# from typing import Optional
# from datetime import datetime

# # Pydantic schema for user data validation and response modeling

# class UserBase(BaseModel):
#     email: str
#     full_name: Optional[str] = None
#     slug: Optional[str] = None

# class UserCreate(UserBase):
#     password: str  # The password is required for user creation

# class UserResponse(UserBase):
#     id: int
#     created_at: datetime
#     updated_at: datetime

#     class Config:
#         orm_mode = True  # This enables compatibility with ORMs (though not used directly here)
