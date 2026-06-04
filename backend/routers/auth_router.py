# auth_router.py
# This file contains all authentication API routes:
# POST /auth/register - create a new account
# POST /auth/login - log in and get a JWT token
# GET /auth/me - get current logged in user info

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import (
    register_user,
    get_user_by_email,
    verify_password,
    create_access_token,
    verify_token,
    get_user_by_id
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# OAuth2PasswordBearer tells FastAPI where to find the token
# tokenUrl is the endpoint where users get their token
# FastAPI uses this to add a lock icon on protected routes in /docs
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    This is a dependency function.
    Any route that needs to know who is logged in
    will use Depends(get_current_user).
    
    It reads the JWT token from the request header,
    verifies it, and returns the current user object.
    """
    try:
        # Verify the token and get user ID
        user_id = verify_token(token)

        # Get the user from database
        user = get_user_by_id(user_id, db)

        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )

        return user

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token. Please log in again."
        )


@router.post("/register")
def register(
    email: str,
    password: str,
    full_name: str,
    db: Session = Depends(get_db)
):
    """
    Creates a new user account.
    Hashes the password before saving to database.
    """
    try:
        user = register_user(
            email=email,
            password=password,
            full_name=full_name,
            db=db
        )

        return {
            "status": "success",
            "message": "Account created successfully",
            "user_id": user.id,
            "email": user.email
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Logs in a user and returns a JWT token.
    
    OAuth2PasswordRequestForm automatically reads
    username and password from the request body.
    We use email as the username field.
    """

    # Step 1 — Find user by email
    user = get_user_by_email(form_data.username, db)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Step 2 — Verify password
    # We compare the plain text password with the stored hash
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Step 3 — Create JWT token
    token = create_access_token(user_id=user.id)

    # Step 4 — Return token
    # access_token and token_type are required by OAuth2 standard
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email
    }


@router.get("/me")
def get_me(current_user=Depends(get_current_user)):
    """
    Returns the currently logged in user's information.
    This route is protected — requires a valid JWT token.
    
    Depends(get_current_user) automatically:
    1. Reads the token from the Authorization header
    2. Verifies it
    3. Returns the user object
    """
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "created_at": str(current_user.created_at)
    }