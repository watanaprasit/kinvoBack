# from app.db.session import get_supabase
# import re
# from typing import Optional, Dict, Any
# from fastapi import HTTPException
# from pydantic import BaseModel

# class UserService:
#     @staticmethod
#     async def get_by_email(email: str):
#         try:
#             supabase = get_supabase()
#             response = (
#                 supabase.table("users")
#                 .select("*")
#                 .eq("email", email)
#                 .single()
#                 .execute()
#             )
            
#             if not response.data:
#                 raise HTTPException(status_code=404, detail="User not found")
                
#             return response.data
#         except Exception as e:
#             print(f"Error in get_by_email: {str(e)}")
#             raise HTTPException(status_code=500, detail=str(e))
    
#     @staticmethod
#     async def get_by_slug(slug: str) -> Optional[Dict[str, Any]]:
#         supabase = get_supabase()
#         result = supabase.table("users").select("*").eq("slug", slug).execute()
#         return result.data[0] if result.data else None

#     @staticmethod
#     async def check_slug_availability(slug: str) -> bool:
#         supabase = get_supabase()
#         result = supabase.table("users").select("id").eq("slug", slug).execute()
#         return len(result.data) == 0

#     @staticmethod
#     async def update_slug(user_id: str, slug: str) -> Optional[Dict[str, Any]]:
#         # Validate slug format
#         if not re.match(r'^[a-z0-9-]+$', slug):
#             raise ValueError("Invalid slug format")
        
#         # Check if slug is already taken
#         is_available = await UserService.check_slug_availability(slug)
#         if not is_available:
#             raise ValueError("Slug already taken")

#         supabase = get_supabase()
#         result = supabase.table("users")\
#             .update({"slug": slug, "updated_at": "now()"})\
#             .eq("id", user_id)\
#             .execute()
        
#         return result.data[0] if result.data else None
    
#     @staticmethod
#     def get_user_by_id(user_id: str):
#         supabase = get_supabase()
#         result = supabase.from_("users").select("*").eq("id", user_id).execute()
#         return result.data[0] if result.data else None
    
#     @staticmethod
#     async def get_current_user_by_token(token: str) -> Dict[str, Any]:
#         supabase = get_supabase()
#         result = supabase.table("users").select("*").eq("email", token).single().execute()
        
#         if not result.data:
#             raise HTTPException(status_code=401, detail="User not found")
        
#         return result.data
    
# class UserPublicProfileResponse(BaseModel):
#     display_name: str
#     slug: str
#     title: Optional[str] = None
#     bio: Optional[str] = None
#     photo_url: Optional[str] = None
#     company_logo_url: Optional[str] = None
#     website: Optional[str] = None
#     contact: Optional[Dict[str, Any]] = None

# class UserPublicResponse(BaseModel):
#     full_name: str
#     slug: str
#     profile: UserPublicProfileResponse
    
    
    
# new below

import re
from typing import Optional, Dict, Any, List
from fastapi import HTTPException
from pydantic import BaseModel

from app.db.session import get_supabase
from app.services.business_card import BusinessCardService 
class SubscriptionTier:
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"

class UserService:
    @staticmethod
    async def get_by_email(email: str):
        try:
            supabase = get_supabase()
            response = (
                supabase.table("users")
                .select("*")
                .eq("email", email)
                .single()
                .execute()
            )
            
            if not response.data:
                raise HTTPException(status_code=404, detail="User not found")
                
            return response.data
        except Exception as e:
            print(f"Error in get_by_email: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    async def get_by_slug(slug: str) -> Optional[Dict[str, Any]]:
        """Get a user by slug"""
        supabase = get_supabase()
        result = supabase.table("users").select("*").eq("slug", slug).execute()
        return result.data[0] if result.data else None

    @staticmethod
    async def check_slug_availability(slug: str) -> bool:
        """Check if a slug is available in both users and business_cards tables"""
        result = await BusinessCardService.check_slug_availability(slug)
        return result["available"]

    @staticmethod
    async def update_slug(user_id: str, slug: str) -> Optional[Dict[str, Any]]:
        """Update a user's slug"""
        # Validate slug format
        if not re.match(r'^[a-z0-9-]+$', slug):
            raise ValueError("Invalid slug format")
        
        # Check if slug is already taken
        is_available = await UserService.check_slug_availability(slug)
        if not is_available:
            raise ValueError("Slug already taken")

        supabase = get_supabase()
        result = supabase.table("users")\
            .update({"slug": slug, "updated_at": "now()"})\
            .eq("id", user_id)\
            .execute()
        
        return result.data[0] if result.data else None
    
    @staticmethod
    def get_user_by_id(user_id: str):
        """Get a user by ID"""
        supabase = get_supabase()
        result = supabase.table("users").select("*").eq("id", user_id).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    async def get_current_user_by_token(token: str) -> Dict[str, Any]:
        """Get the current user by token"""
        supabase = get_supabase()
        result = supabase.table("users").select("*").eq("email", token).single().execute()
        
        if not result.data:
            raise HTTPException(status_code=401, detail="User not found")
        
        return result.data
    
    @staticmethod
    async def get_subscription_tier(user_id: str) -> str:
        """Get the user's subscription tier"""
        supabase = get_supabase()
        result = supabase.table("subscriptions")\
            .select("tier")\
            .eq("user_id", user_id)\
            .eq("status", "active")\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
            
        if not result.data:
            return SubscriptionTier.FREE
            
        return result.data[0].get("tier", SubscriptionTier.FREE)
    
    @staticmethod
    async def can_create_business_card(user_id: str) -> bool:
        """Check if the user can create another business card based on their subscription"""
        supabase = get_supabase()
        
        # Get user's subscription tier
        tier = await UserService.get_subscription_tier(user_id)
        
        # Get count of existing business cards
        result = supabase.table("business_cards")\
            .select("id", count="exact")\
            .eq("user_id", user_id)\
            .execute()
        
        card_count = result.count
        
        # Check limits based on subscription tier
        if tier == SubscriptionTier.FREE and card_count >= 1:
            return False
        elif tier == SubscriptionTier.PRO and card_count >= 3:
            return False
        elif tier == SubscriptionTier.BUSINESS and card_count >= 10:
            return False
            
        return True
    
    @staticmethod
    async def get_business_cards(user_id: str) -> List[Dict[str, Any]]:
        """Get all business cards for a user"""
        return await BusinessCardService.get_by_user_id(user_id)
    
    @staticmethod
    async def get_primary_business_card(user_id: str) -> Optional[Dict[str, Any]]:
        """Get the user's primary business card"""
        return await BusinessCardService.get_primary_by_user_id(user_id)

# Response models
class UserPublicProfileResponse(BaseModel):
    display_name: str
    slug: str
    title: Optional[str] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    company_logo_url: Optional[str] = None
    website: Optional[str] = None
    contact: Optional[Dict[str, Any]] = None

class BusinessCardPublicResponse(BaseModel):
    display_name: str
    slug: str
    title: Optional[str] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    company_logo_url: Optional[str] = None
    website: Optional[str] = None
    contact: Optional[Dict[str, Any]] = None
    qr_code_url: Optional[str] = None
    is_primary: bool = False

class UserPublicResponse(BaseModel):
    full_name: str
    slug: str
    business_card: BusinessCardPublicResponse