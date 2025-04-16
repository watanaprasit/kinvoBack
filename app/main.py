from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .api.v1 import auth, users
from .core.config import settings
from fastapi import Request
from .services.user import UserService
from .services.user_profile import UserProfileService
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
        
        # Get profile data
        profile = await UserProfileService.get_by_user_id(user["id"])
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        # Return only the public information
        return {
            "full_name": user["full_name"],
            "slug": user["slug"],
            "profile": {
                "display_name": profile["display_name"],
                "slug": profile["slug"],
                "title": profile.get("title"),
                "bio": profile.get("bio"),
                "photo_url": profile.get("photo_url"),
                "company_logo_url": profile.get("company_logo_url"),
                "website": profile.get("website"),
                "contact": profile.get("contact")
                # Only include non-sensitive fields
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching profile by slug: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
# In your FastAPI main.py
@app.get("/api/v1/profiles/{slug}", tags=["profiles"])
async def get_profile_api(slug: str):
    # Reuse your existing logic from the /{slug} endpoint
    try:
        # Get user by slug
        user = await UserService.get_by_slug(slug)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get profile data
        profile = await UserProfileService.get_by_user_id(user["id"])
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Return only the public information
        return {
            "full_name": user["full_name"],
            "slug": user["slug"],
            "profile": {
                "display_name": profile["display_name"],
                "slug": profile["slug"],
                "title": profile.get("title"),
                "bio": profile.get("bio"),
                "photo_url": profile.get("photo_url"),
                "company_logo_url": profile.get("company_logo_url"),
                "website": profile.get("website"),
                "contact": profile.get("contact")
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
        profile_url = f"{base_url.rstrip('/')}/{slug}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(profile_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffered = BytesIO()
        img.save(buffered)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "qr_data": profile_url,
            "qr_image": f"data:image/png;base64,{img_str}"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating QR code: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating QR code")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)