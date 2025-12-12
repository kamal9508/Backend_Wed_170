from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional


class OrgCreate(BaseModel):
    organization_name: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=6)


class OrgUpdate(BaseModel):
    organization_name: Optional[str]
    email: Optional[EmailStr]
    password: Optional[str]


class OrgOut(BaseModel):
    id: str
    organization_name: str
    collection_name: str
    admin_email: str


class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
