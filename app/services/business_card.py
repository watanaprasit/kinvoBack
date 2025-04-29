import json
import base64
import qrcode
from io import BytesIO
from typing import Optional, Dict, Any, List
from fastapi import UploadFile, HTTPException
from app.schemas.user.business_card import BusinessCard, BusinessCardCreate, BusinessCardUpdate
from app.db.session import get_supabase

class BusinessCardService:
    @staticmethod
    async def get_by_email(email: str):
        """Get a user by their email address"""
        # Implement your database query here
        # Example using async database client:
        try:
            query = "SELECT * FROM auth.users WHERE email = $1"
            user = await db.fetch_one(query, email)
            return dict(user) if user else None
        except Exception as e:
            print(f"Database error in get_by_email: {str(e)}")
            raise
        
    @staticmethod
    async def get_primary_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Get the primary business card for a user"""
        try:
            supabase = get_supabase()
            response = (
                supabase.table("business_cards")
                .select("*")
                .eq("user_id", user_id)
                .eq("is_primary", True)
                .single()
                .execute()
            )
            
            if not response.data:
                return None
                
            # Process contact field from JSON string if needed
            if response.data.get('contact') and isinstance(response.data['contact'], str):
                response.data['contact'] = json.loads(response.data['contact'])
                
            return response.data
        except Exception as e:
            print(f"Error getting primary business card: {str(e)}")
            return None
    
    @staticmethod
    async def create_business_card(user_id: str, card_data: BusinessCardCreate, photo: Optional[UploadFile] = None, company_logo: Optional[UploadFile] = None) -> Dict[str, Any]:
        """Create a new business card for a user"""
        try:
            supabase = get_supabase()
            
            # Check if slug is available
            slug_check = await BusinessCardService.check_slug_availability(card_data.slug)
            if not slug_check["available"]:
                raise HTTPException(status_code=400, detail="Slug already in use")
            
            # Check if this is the first card for the user (should be primary)
            cards_result = supabase.table("business_cards").select("id", count="exact").eq("user_id", user_id).execute()
            is_first_card = cards_result.count == 0
            
            # Prepare the card data
            new_card_data = {
                "user_id": user_id,
                "display_name": card_data.display_name,
                "slug": card_data.slug,
                "title": card_data.title,
                "bio": card_data.bio,
                "email": card_data.email,
                "website": card_data.website,
                "contact": json.dumps(card_data.contact) if card_data.contact else None,
                "is_primary": is_first_card  # First card is automatically primary
            }
            
            # Handle photo upload if provided
            if photo:
                # Implement file upload logic here
                # For example, save to cloud storage and store URL
                photo_url = f"/uploads/photos/{user_id}_{photo.filename}"
                new_card_data["photo_url"] = photo_url
                
            # Handle company logo upload if provided
            if company_logo:
                # Implement file upload logic here
                logo_url = f"/uploads/logos/{user_id}_{company_logo.filename}"
                new_card_data["company_logo_url"] = logo_url
            
            # Insert the new card
            result = supabase.table("business_cards").insert(new_card_data).execute()
            
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to create business card")
                
            # Process contact field from JSON string if needed
            if result.data[0].get('contact') and isinstance(result.data[0]['contact'], str):
                result.data[0]['contact'] = json.loads(result.data[0]['contact'])
                
            return result.data[0]
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error creating business card: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error creating business card: {str(e)}")
    
    @staticmethod
    async def get_by_id(card_id: int) -> Optional[Dict[str, Any]]:
        """Get a business card by ID"""
        try:
            supabase = get_supabase()
            result = supabase.table("business_cards").select("*").eq("id", card_id).single().execute()
            
            if not result.data:
                return None
                
            # Process contact field from JSON string if needed
            if result.data.get('contact') and isinstance(result.data['contact'], str):
                result.data['contact'] = json.loads(result.data['contact'])
                
            return result.data
        except Exception as e:
            print(f"Error getting business card by ID: {str(e)}")
            return None
    
    @staticmethod
    async def get_by_user_id(user_id: str) -> List[Dict[str, Any]]:
        """Get all business cards for a user"""
        try:
            supabase = get_supabase()
            result = supabase.table("business_cards").select("*").eq("user_id", user_id).execute()
            
            cards = result.data if result.data else []
            
            # Process contact field from JSON string if needed
            for card in cards:
                if card.get('contact') and isinstance(card['contact'], str):
                    card['contact'] = json.loads(card['contact'])
                    
            return cards
        except Exception as e:
            print(f"Error getting business cards by user ID: {str(e)}")
            return []
    
    @staticmethod
    async def update_business_card(card_id: int, card_data: BusinessCardUpdate, photo: Optional[UploadFile] = None, company_logo: Optional[UploadFile] = None, current_user=None, base_url: Optional[str] = None) -> Dict[str, Any]:
        """Update a business card"""
        try:
            supabase = get_supabase()
            
            # Get the current card
            current_card = await BusinessCardService.get_by_id(card_id)
            if not current_card:
                raise HTTPException(status_code=404, detail="Business card not found")
            
            # Check if user owns this card
            if current_user and current_card["user_id"] != current_user.id:
                raise HTTPException(status_code=403, detail="Not authorized to update this business card")
            
            # Check if slug is being changed and is available
            if card_data.slug and card_data.slug != current_card["slug"]:
                slug_check = await BusinessCardService.check_slug_availability(card_data.slug, current_card["user_id"])
                if not slug_check["available"]:
                    raise HTTPException(status_code=400, detail="Slug already in use")
            
            # Prepare update data
            update_data = {}
            for field, value in card_data.dict(exclude_unset=True).items():
                if field == 'contact' and value is not None:
                    update_data[field] = json.dumps(value)
                else:
                    update_data[field] = value
            
            # Handle photo upload if provided
            if photo:
                # Implement file upload logic here
                photo_url = f"/uploads/photos/{current_card['user_id']}_{photo.filename}"
                update_data["photo_url"] = photo_url
                
            # Handle company logo upload if provided
            if company_logo:
                # Implement file upload logic here
                logo_url = f"/uploads/logos/{current_card['user_id']}_{company_logo.filename}"
                update_data["company_logo_url"] = logo_url
            
            # Update the card
            result = supabase.table("business_cards").update(update_data).eq("id", card_id).execute()
            
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to update business card")
                
            # Process contact field from JSON string if needed
            if result.data[0].get('contact') and isinstance(result.data[0]['contact'], str):
                result.data[0]['contact'] = json.loads(result.data[0]['contact'])
                
            return result.data[0]
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error updating business card: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error updating business card: {str(e)}")
    
    @staticmethod
    async def delete_business_card(card_id: int) -> bool:
        """Delete a business card"""
        try:
            supabase = get_supabase()
            
            # Get the current card
            current_card = await BusinessCardService.get_by_id(card_id)
            if not current_card:
                raise HTTPException(status_code=404, detail="Business card not found")
            
            # Check if this is the primary card
            is_primary = current_card["is_primary"]
            user_id = current_card["user_id"]
            
            # Delete the card
            result = supabase.table("business_cards").delete().eq("id", card_id).execute()
            
            # If this was the primary card, set another card as primary if available
            if is_primary:
                remaining_cards = supabase.table("business_cards").select("id").eq("user_id", user_id).limit(1).execute()
                if remaining_cards.data and len(remaining_cards.data) > 0:
                    supabase.table("business_cards").update({"is_primary": True}).eq("id", remaining_cards.data[0]["id"]).execute()
            
            return True
        except Exception as e:
            print(f"Error deleting business card: {str(e)}")
            return False
    
    @staticmethod
    async def set_as_primary(card_id: int, user_id: str) -> Dict[str, Any]:
        """Set a business card as primary"""
        try:
            supabase = get_supabase()
            
            # Find the card to set as primary
            card = supabase.table("business_cards").select("*").eq("id", card_id).eq("user_id", user_id).single().execute()
            
            if not card.data:
                raise HTTPException(status_code=404, detail="Business card not found")
            
            # Set all cards for this user as not primary
            supabase.table("business_cards").update({"is_primary": False}).eq("user_id", user_id).execute()
            
            # Set the requested card as primary
            result = supabase.table("business_cards").update({"is_primary": True}).eq("id", card_id).execute()
            
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to set card as primary")
                
            # Process contact field from JSON string if needed
            if result.data[0].get('contact') and isinstance(result.data[0]['contact'], str):
                result.data[0]['contact'] = json.loads(result.data[0]['contact'])
                
            return result.data[0]
        except Exception as e:
            print(f"Error setting card as primary: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error setting card as primary: {str(e)}")
    
    @staticmethod
    async def get_by_slug(slug: str) -> Optional[Dict[str, Any]]:
        """Get a business card by slug"""
        try:
            supabase = get_supabase()
            result = supabase.table("business_cards").select("*").eq("slug", slug).single().execute()
            
            if not result.data:
                return None
                
            # Process contact field from JSON string if needed
            if result.data.get('contact') and isinstance(result.data['contact'], str):
                result.data['contact'] = json.loads(result.data['contact'])
                
            return result.data
        except Exception as e:
            print(f"Error getting business card by slug: {str(e)}")
            return None
    
    @staticmethod
    async def check_slug_availability(slug: str, current_user_id: Optional[str] = None) -> Dict[str, bool]:
        """Check if a slug is available"""
        try:
            supabase = get_supabase()
            
            # Check in users table
            users_result = supabase.table("users").select("id").eq("slug", slug).execute()
            if users_result.data and len(users_result.data) > 0:
                return {"available": False}
            
            # Check in business_cards table
            query = supabase.table("business_cards").select("id").eq("slug", slug)
            
            # If current_user_id is provided, exclude their own cards
            if current_user_id:
                # We need to use .neq() for not equal in Supabase
                query = supabase.table("business_cards").select("id").eq("slug", slug).neq("user_id", current_user_id)
                
            cards_result = query.execute()
            
            return {"available": len(cards_result.data) == 0}
        except Exception as e:
            print(f"Error checking slug availability: {str(e)}")
            return {"available": False}
    
    @staticmethod
    def generate_qr_code_url(slug: str, base_url: Optional[str] = None) -> str:
        """Generate a URL for the QR code"""
        if base_url:
            return f"{base_url.rstrip('/')}/{slug}"
        return f"https://yourapp.com/{slug}"  # Default URL
    
    @staticmethod
    def generate_qr_code_image(data: str) -> str:
        """Generate a QR code image"""
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