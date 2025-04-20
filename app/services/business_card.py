# app/services/business_card.py

import json
import base64
import qrcode
from io import BytesIO
from typing import Optional, Dict, Any, List
from fastapi import UploadFile
from app.schemas.user.business_card import BusinessCard, BusinessCardCreate, BusinessCardUpdate
# Import your db session and models as needed

class BusinessCardService:
    @staticmethod
    async def get_primary_by_user_id(user_id: int) -> Optional[Dict[str, Any]]:
        # Implement logic to fetch primary business card for a user
        pass
        
    @staticmethod
    async def create_business_card(user_id: int, card_data: BusinessCardCreate, photo: Optional[UploadFile] = None, company_logo: Optional[UploadFile] = None) -> Dict[str, Any]:
        # Implement logic to create a business card
        pass
        
    @staticmethod
    async def get_by_id(card_id: int) -> Optional[Dict[str, Any]]:
        # Implement logic to get business card by ID
        pass
        
    @staticmethod
    async def get_by_user_id(user_id: int) -> List[Dict[str, Any]]:
        # Implement logic to get all business cards for a user
        pass
        
    @staticmethod
    async def update_business_card(card_id: int, card_data: BusinessCardUpdate, photo: Optional[UploadFile] = None, company_logo: Optional[UploadFile] = None, current_user=None, base_url: Optional[str] = None) -> Dict[str, Any]:
        # Implement logic to update a business card
        pass
        
    @staticmethod
    async def delete_business_card(card_id: int) -> bool:
        # Implement logic to delete a business card
        pass
        
    @staticmethod
    async def set_as_primary(card_id: int, user_id: int) -> Dict[str, Any]:
        # Implement logic to set a card as primary
        pass
        
    @staticmethod
    async def get_by_slug(slug: str) -> Optional[Dict[str, Any]]:
        # Implement logic to get a business card by slug
        pass
        
    @staticmethod
    def generate_qr_code_url(slug: str, base_url: Optional[str] = None) -> str:
        # Generate a URL for the QR code
        if base_url:
            return f"{base_url.rstrip('/')}/{slug}"
        return f"https://yourapp.com/{slug}"  # Default URL
        
    @staticmethod
    def generate_qr_code_image(data: str) -> str:
        # Generate a QR code image
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = BytesIO()
        img.save(buffered)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"