from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form, Query, Body
from typing import Optional, Dict, Any, List
from sqlalchemy.exc import IntegrityError
from pydantic import EmailStr, HttpUrl
from app.schemas.user.business_card import BusinessCard, BusinessCardCreate, BusinessCardUpdate
from app.schemas.user.user import UserResponse
from app.services.user import UserService
from app.core.security import get_current_user
from app.services.business_card import BusinessCardService
import json

router = APIRouter()

@router.get("/by-email")
async def get_user_by_email(email: str = Query(...)):
    """
    Get user data by email with their primary business card information
    """
    try:
        user = await UserService.get_by_email(email)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        business_card = await BusinessCardService.get_primary_by_user_id(user["id"])
    
        if not business_card:
            card_data = BusinessCardCreate(
                user_id=user["id"],
                display_name=user["full_name"],
                slug=user["slug"],
                is_primary=True
            )
            business_card = await BusinessCardService.create_business_card(
                user_id=user["id"],
                card_data=card_data
            )

        return {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "username": user.get("username"),
            "slug": user["slug"],
            "business_card": business_card
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error in get_user_by_email: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/by-email/{email}")
async def get_user_by_email(email: str):
    """Get a user by their email address"""
    try:
        # Validate email format
        if not email or '@' not in email:
            raise HTTPException(status_code=400, detail="Invalid email format")
            
        # Get user from database
        user = await UserService.get_by_email(email)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Return user data (excluding sensitive fields)
        return {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "slug": user["slug"],
            "subscription_tier": user.get("subscription_tier", "free"),
            "created_at": user.get("created_at"),
            "updated_at": user.get("updated_at")
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching user by email: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")



@router.get("/me", response_model=UserResponse)
async def get_current_user_data(current_user = Depends(get_current_user)):
    try:
        # Get user's primary business card
        business_card = await BusinessCardService.get_primary_by_user_id(current_user.id)
        
        return {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "slug": current_user.slug,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at,
            "google_id": current_user.google_id,
            "business_card": business_card  # Include business card data in response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/me/slug", response_model=UserResponse)
async def update_user_slug(
    slug: str,
    current_user = Depends(get_current_user)
):
    try:
        # Validate slug
        slug = slug.strip().lower()
        
        if len(slug) > 20:
            raise HTTPException(status_code=400, detail="Slug must be 20 characters or less")
            
        if ' ' in slug:
            raise HTTPException(status_code=400, detail="Slug cannot contain spaces")
            
        updated_user = await UserService.update_slug(current_user.id, slug)
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get updated business card data
        business_card = await BusinessCardService.get_primary_by_user_id(current_user.id)
        return {**updated_user, "business_card": business_card}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Slug already taken")

@router.get("/check-slug/{slug}")
async def check_slug_availability(slug: str):
    try:
        # Validate slug format before checking availability
        slug = slug.strip().lower()
        
        if len(slug) > 20:
            return {"available": False, "error": "Slug must be 20 characters or less"}
            
        if ' ' in slug:
            return {"available": False, "error": "Slug cannot contain spaces"}
            
        is_available = await UserService.check_slug_availability(slug)
        return {"available": is_available}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}/business-cards", response_model=List[BusinessCard])
async def get_user_business_cards(
    user_id: int,
    current_user = Depends(get_current_user)
):
    # Only allow users to access their own business cards
    if str(current_user.id) != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    
    business_cards = await BusinessCardService.get_by_user_id(user_id)
    return business_cards

@router.get("/{user_id}/business-card", response_model=BusinessCard)
async def get_user_primary_business_card(user_id: int):
    business_card = await BusinessCardService.get_primary_by_user_id(user_id)
    if not business_card:
        raise HTTPException(status_code=404, detail="Business card not found")
    return business_card

@router.post("/business-card", response_model=BusinessCard)
async def create_business_card(
    display_name: str = Form(...),
    slug: str = Form(...),
    title: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    email: Optional[EmailStr] = Form(None),
    website: Optional[str] = Form(None),
    contact: Optional[str] = Form(None),
    is_primary: bool = Form(False),
    photo: Optional[UploadFile] = File(None),
    company_logo: Optional[UploadFile] = File(None),
    current_user = Depends(get_current_user)
):
    try:
        # Check if user can create more business cards
        can_create = await UserService.can_create_business_card(current_user.id)
        if not can_create:
            subscription_tier = await UserService.get_subscription_tier(current_user.id)
            raise HTTPException(
                status_code=403, 
                detail=f"You've reached the maximum number of business cards for your {subscription_tier} subscription"
            )
        
        # Validate display_name
        if len(display_name.strip()) > 30:
            raise HTTPException(status_code=400, detail="Display name must be 30 characters or less")
            
        # Process and validate slug
        slug = slug.strip().lower() if slug else None
        
        if not slug:
            raise HTTPException(status_code=400, detail="Slug is required")
            
        if len(slug) > 20:
            raise HTTPException(status_code=400, detail="Slug must be 20 characters or less")
            
        if ' ' in slug:
            raise HTTPException(status_code=400, detail="Slug cannot contain spaces")
        
        # Validate title
        if title and len(title.strip()) > 40:
            raise HTTPException(status_code=400, detail="Title must be 40 characters or less")
        
        if bio and len(bio.strip()) > 200:
            raise HTTPException(status_code=400, detail="Bio must be 200 characters or less")
        
        # Parse contact JSON if provided
        contact_data = None
        if contact:
            try:
                contact_data = json.loads(contact)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON format for contact field")
        
        card_data = BusinessCardCreate(
            user_id=current_user.id,
            display_name=display_name,
            slug=slug,
            title=title,
            bio=bio,
            email=email,
            website=website,
            contact=contact_data,
            is_primary=is_primary
        )
        
        business_card = await BusinessCardService.create_business_card(
            user_id=current_user.id,
            card_data=card_data,
            photo=photo,
            company_logo=company_logo
        )
        
        if not business_card:
            raise HTTPException(status_code=500, detail="Failed to create business card")
        
        return business_card
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/business-card/{card_id}", response_model=BusinessCard)
async def update_business_card(
    card_id: int,
    display_name: Optional[str] = Form(None),
    slug: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    contact: Optional[str] = Form(None),
    is_primary: Optional[bool] = Form(None),
    base_url: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    company_logo: Optional[UploadFile] = File(None),
    current_user = Depends(get_current_user)
):
    try:
        # Verify card belongs to user
        card = await BusinessCardService.get_by_id(card_id)
        if not card or card.get('user_id') != current_user.id:
            raise HTTPException(status_code=404, detail="Business card not found")
        
        # Validate inputs
        if display_name is not None:
            if not display_name.strip():
                raise HTTPException(status_code=400, detail="Display name cannot be empty")
            if len(display_name.strip()) > 30:
                raise HTTPException(status_code=400, detail="Display name must be 30 characters or less")
        
        # Validate slug
        if slug is not None and slug.strip():
            slug = slug.strip().lower()
            
            if len(slug) > 20:
                raise HTTPException(status_code=400, detail="Slug must be 20 characters or less")
                
            if ' ' in slug:
                raise HTTPException(status_code=400, detail="Slug cannot contain spaces")
                
            # Check slug availability (unless it's the same as current)
            if slug != card.get('slug'):
                slug_available = await UserService.check_slug_availability(slug)
                if not slug_available:
                    raise HTTPException(status_code=400, detail="Slug is already taken")
                
        # Validate title
        if title is not None and len(title.strip()) > 40:
            raise HTTPException(status_code=400, detail="Title must be 40 characters or less")
        
        if bio is not None and len(bio.strip()) > 200:
            raise HTTPException(status_code=400, detail="Bio must be 200 characters or less")
            
        # Parse contact JSON if provided
        contact_data = None
        if contact is not None:
            try:
                contact_data = json.loads(contact)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON format for contact field")
            
        # Create card update data with only the fields that are provided
        card_data = BusinessCardUpdate(
            display_name=display_name if display_name is not None else None,
            slug=slug if slug is not None and slug.strip() else None,
            title=title if title is not None else None,
            bio=bio if bio is not None else None,
            photo_url=None,
            company_logo_url=None,
            email=email,
            website=website,
            contact=contact_data,
            is_primary=is_primary
        )
        
        # Update business card
        updated_card = await BusinessCardService.update_business_card(
            card_id=card_id,
            card_data=card_data,
            photo=photo,
            company_logo=company_logo,
            current_user=current_user,
            base_url=base_url
        )
        
        return updated_card
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update business card: {str(e)}"
        )

@router.delete("/business-card/{card_id}")
async def delete_business_card(
    card_id: int,
    current_user = Depends(get_current_user)
):
    try:
        # Verify card belongs to user
        card = await BusinessCardService.get_by_id(card_id)
        if not card or card.get('user_id') != current_user.id:
            raise HTTPException(status_code=404, detail="Business card not found")
        
        # Don't allow deletion of primary card if it's the only card
        if card.get('is_primary'):
            all_cards = await BusinessCardService.get_by_user_id(current_user.id)
            if len(all_cards) <= 1:
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot delete your only business card. Create another card before deleting this one."
                )
        
        success = await BusinessCardService.delete_business_card(card_id)
        if success:
            return {"message": "Business card deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete business card")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/business-card/{card_id}/set-primary", response_model=BusinessCard)
async def set_primary_business_card(
    card_id: int,
    current_user = Depends(get_current_user)
):
    try:
        # Verify card belongs to user
        card = await BusinessCardService.get_by_id(card_id)
        if not card or card.get('user_id') != current_user.id:
            raise HTTPException(status_code=404, detail="Business card not found")
        
        # Set as primary
        updated_card = await BusinessCardService.set_as_primary(card_id, current_user.id)
        return updated_card
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{slug}", response_model=UserResponse)
async def get_user_by_slug(slug: str):
    try:
        user = await UserService.get_by_slug(slug)
        
        if not user:
            # Check if the slug belongs to a business card
            business_card = await BusinessCardService.get_by_slug(slug)
            if not business_card:
                raise HTTPException(status_code=404, detail="User not found")
                
            # Get the user associated with this business card
            user = await UserService.get_user_by_id(business_card["user_id"])
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
                
            return {
                "id": user["id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "slug": user["slug"],
                "created_at": user["created_at"],
                "updated_at": user["updated_at"],
                "google_id": None,
                "business_card": business_card
            }
        
        # Get user's primary business card
        business_card = await BusinessCardService.get_primary_by_user_id(user["id"])
        
        return {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "slug": user["slug"],
            "created_at": user["created_at"],
            "updated_at": user["updated_at"],
            "google_id": None,
            "business_card": business_card
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/business-card/{slug}", response_model=BusinessCard)
async def get_business_card_by_slug(slug: str):
    business_card = await BusinessCardService.get_by_slug(slug)
    if not business_card:
        raise HTTPException(status_code=404, detail="Business card not found")
    return business_card

@router.get("/me/qrcode", response_model=Dict[str, str])
async def get_qr_code(
    base_url: Optional[str] = Query(None),
    card_id: Optional[int] = Query(None),
    current_user = Depends(get_current_user)
):
    try:
        if card_id:
            # Get specific business card
            business_card = await BusinessCardService.get_by_id(card_id)
            if not business_card or business_card.get('user_id') != current_user.id:
                raise HTTPException(status_code=404, detail="Business card not found")
        else:
            # Get user's primary business card
            business_card = await BusinessCardService.get_primary_by_user_id(current_user.id)
        
        if not business_card:
            raise HTTPException(status_code=404, detail="Business card not found")
        
        # Get QR code data
        qr_data = business_card.get('qr_code_url')
        
        # If no QR code data exists, generate it
        if not qr_data:
            qr_data = BusinessCardService.generate_qr_code_url(business_card['slug'], base_url)
            
            # Update the business card with the new QR code data
            update_data = BusinessCardUpdate(qr_code_url=qr_data)
            if card_id:
                await BusinessCardService.update_business_card(
                    card_id=card_id,
                    card_data=update_data,
                    current_user=current_user
                )
            else:
                await BusinessCardService.update_business_card(
                    card_id=business_card['id'],
                    card_data=update_data,
                    current_user=current_user
                )
        
        # Generate QR code image
        qr_image = BusinessCardService.generate_qr_code_image(qr_data)
        
        return {
            "qr_data": qr_data,
            "qr_image": qr_image
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate QR code: {str(e)}")

@router.put("/me/qrcode", response_model=Dict[str, str])
async def update_qr_code(
    qr_data: str = Body(..., embed=True),
    card_id: Optional[int] = Body(None),
    current_user = Depends(get_current_user)
):
    try:
        if card_id:
            # Get specific business card
            business_card = await BusinessCardService.get_by_id(card_id)
            if not business_card or business_card.get('user_id') != current_user.id:
                raise HTTPException(status_code=404, detail="Business card not found")
        else:
            # Get user's primary business card
            business_card = await BusinessCardService.get_primary_by_user_id(current_user.id)
        
        if not business_card:
            raise HTTPException(status_code=404, detail="Business card not found")
        
        # Update business card with custom QR code data
        update_data = BusinessCardUpdate(qr_code_url=qr_data)
        
        if card_id:
            await BusinessCardService.update_business_card(
                card_id=card_id,
                card_data=update_data,
                current_user=current_user
            )
        else:
            await BusinessCardService.update_business_card(
                card_id=business_card['id'],
                card_data=update_data,
                current_user=current_user
            )
        
        # Generate QR code image
        qr_image = BusinessCardService.generate_qr_code_image(qr_data)
        
        return {
            "qr_data": qr_data,
            "qr_image": qr_image
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update QR code: {str(e)}")
    
@router.get("/{slug}/qrcode", response_model=Dict[str, str])
async def get_public_qr_code(
    slug: str,
    base_url: Optional[str] = Query(None)
):
    try:
        # Try to find business card by slug
        business_card = await BusinessCardService.get_by_slug(slug)
        
        if not business_card:
            # If no direct match, try to find user and their primary card
            user = await UserService.get_by_slug(slug)
            if not user:
                raise HTTPException(status_code=404, detail="User or business card not found")
            
            business_card = await BusinessCardService.get_primary_by_user_id(user["id"])
            if not business_card:
                raise HTTPException(status_code=404, detail="Business card not found")
        
        # Get QR code data
        qr_data = business_card.get('qr_code_url')
        
        # If no QR code data exists, generate it
        if not qr_data:
            qr_data = BusinessCardService.generate_qr_code_url(business_card['slug'], base_url)
        
        # Generate QR code image
        qr_image = BusinessCardService.generate_qr_code_image(qr_data)
        
        return {
            "qr_data": qr_data,
            "qr_image": qr_image
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate QR code: {str(e)}")
    
    
# Fix for the FastAPI routes to properly handle slug lookups
# Replace the current implementation of get_user_by_slug with this improved version

@router.get("/{slug}", response_model=UserResponse)
async def get_user_by_slug(slug: str):
    try:
        # Add logging to debug the issue
        print(f"Looking up slug: {slug}")
        
        # First try to find a user with this slug
        user = await UserService.get_by_slug(slug)
        
        if user:
            # User found - get their primary business card
            print(f"User found with slug: {slug}, user_id: {user['id']}")
            business_card = await BusinessCardService.get_primary_by_user_id(user["id"])
            
            # Return user data with their business card
            return {
                "id": user["id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "slug": user["slug"],
                "created_at": user["created_at"],
                "updated_at": user["updated_at"],
                "google_id": None,
                "business_card": business_card
            }
        
        # If no user found, try to find a business card with this slug
        print(f"No user found with slug: {slug}, checking business cards")
        business_card = await BusinessCardService.get_by_slug(slug)
        
        if not business_card:
            print(f"No business card found with slug: {slug}")
            raise HTTPException(status_code=404, detail="User or business card not found")
        
        # Business card found - get the associated user
        print(f"Business card found with slug: {slug}, user_id: {business_card['user_id']}")
        user_id = business_card["user_id"]
        user = await UserService.get_user_by_id(user_id)
        
        if not user:
            print(f"User not found for business card user_id: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Found both the business card and its owner - return the data
        return {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "slug": user["slug"],
            "created_at": user["created_at"],
            "updated_at": user["updated_at"],
            "google_id": None,
            "business_card": business_card
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_user_by_slug: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

# Also fix the business card specific endpoint to be more robust
@router.get("/business-card/{slug}", response_model=BusinessCard)
async def get_business_card_by_slug(slug: str):
    try:
        print(f"Looking up business card with slug: {slug}")
        business_card = await BusinessCardService.get_by_slug(slug)
        
        if not business_card:
            print(f"No business card found with slug: {slug}")
            raise HTTPException(status_code=404, detail="Business card not found")
            
        return business_card
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_business_card_by_slug: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")