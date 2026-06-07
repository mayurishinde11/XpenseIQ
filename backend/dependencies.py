# dependencies.py
# Shared dependency functions used across multiple routers.
# Keeping get_current_user here (instead of inside auth_router.py)
# prevents circular imports when other routers need authentication.

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import verify_token, get_user_by_id

# OAuth2PasswordBearer tells FastAPI where the login endpoint is.
# This adds the lock icon on protected routes in /docs.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Shared dependency function used by ALL routers that need authentication.
    Any route that needs to know who is logged in uses Depends(get_current_user).

    It reads the JWT token from the Authorization header,
    verifies it, and returns the current user object from the database.
    """
    try:
        # Verify the token and extract user ID
        user_id = verify_token(token)

        # Fetch the user from the database
        user = get_user_by_id(user_id, db)

        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )

        return user

    except HTTPException:
        # Re-raise HTTP exceptions as-is (e.g. 401 from above)
        raise

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token. Please log in again."
        )