from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .api.v1 import auth, users
from .core.config import settings
from fastapi import Request
from .services.user import UserService
from .services.business_card import BusinessCardService  
import re
import qrcode
import base64
from io import BytesIO

app = FastAPI(title=settings.PROJECT_NAME)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your Vite app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Kinvo Backend!"}

# Include the routes for authentication
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])

# Add a public endpoint for slug access (Linktree-like functionality)
@app.get("/{slug}", tags=["public"])
async def get_public_profile_by_slug(slug: str):
    # Check if this is a reserved path
    reserved_paths = ["api", "docs", "redoc", "openapi.json"]
    if slug in reserved_paths:
        # Skip this handler for reserved paths
        raise HTTPException(status_code=404, detail="Not found")
    
    # Validate slug format
    if not re.match(r'^[a-zA-Z0-9-]+$', slug):
        raise HTTPException(status_code=404, detail="Not found")
        
    try:
        # Get user by slug
        user = await UserService.get_by_slug(slug)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get business card data
        card = await BusinessCardService.get_by_slug(slug)  # Updated service call
        
        if not card:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        # Return only the public information
        return {
            "full_name": user["full_name"],
            "slug": user["slug"],
            "profile": {
                "display_name": card["display_name"],
                "slug": card["slug"],
                "title": card.get("title"),
                "bio": card.get("bio"),
                "photo_url": card.get("photo_url"),
                "company_logo_url": card.get("company_logo_url"),
                "website": card.get("website"),
                "contact": card.get("contact")
                # Only include non-sensitive fields
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching profile by slug: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
# Add this to your main.py
@app.get("/api/v1/profiles/dashboard", tags=["profiles"])
async def get_profiles_dashboard():
    # Your dashboard logic here
    return {"data": "Your dashboard data"}


@app.get("/api/v1/profiles/{slug}", tags=["profiles"])
async def get_profile_api(slug: str):
    # Reuse your existing logic from the /{slug} endpoint
    try:
        # Get user by slug
        user = await UserService.get_by_slug(slug)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get business card data
        card = await BusinessCardService.get_by_slug(slug)  # Updated service call
        
        if not card:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Return only the public information
        return {
            "full_name": user["full_name"],
            "slug": user["slug"],
            "profile": {
                "display_name": card["display_name"],
                "slug": card["slug"],
                "title": card.get("title"),
                "bio": card.get("bio"),
                "photo_url": card.get("photo_url"),
                "company_logo_url": card.get("company_logo_url"),
                "website": card.get("website"),
                "contact": card.get("contact")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching profile by slug: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Add a public QR code endpoint
@app.get("/api/v1/profiles/{slug}/qrcode", tags=["profiles"])
async def get_public_qrcode(slug: str, base_url: str = "http://localhost:5173/"):
    try:
        # Get user by slug
        user = await UserService.get_by_slug(slug)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Generate QR code for the profile URL
        profile_url = BusinessCardService.generate_qr_code_url(slug, base_url)  # Using the service method
        
        # Generate QR code image
        qr_image = BusinessCardService.generate_qr_code_image(profile_url)  # Using the service method
        
        return {
            "qr_data": profile_url,
            "qr_image": qr_image
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating QR code: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating QR code")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)