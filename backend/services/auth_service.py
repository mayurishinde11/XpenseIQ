# auth_service.py
# This file handles all authentication logic:
# - Hashing passwords before saving to database
# - Verifying passwords during login
# - Creating JWT tokens after successful login
# - Reading JWT tokens to identify the current user

from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from models.user import User
from config import SECRET_KEY

# Algorithm used to sign the JWT token
# HS256 is the most common algorithm for JWT
ALGORITHM = "HS256"

# How long a token stays valid
# After this time the user must log in again
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# CryptContext sets up our password hashing
# bcrypt is the industry standard hashing algorithm
# It's designed to be slow on purpose — makes brute force attacks hard
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Takes a plain text password and returns a hashed version.
    We NEVER store plain text passwords in the database.
    
    Example:
    Input:  "mypassword123"
    Output: "$2b$12$randomsalthere.hashedvalue..."
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Checks if a plain text password matches the stored hash.
    Used during login to verify the user's password.
    
    Returns True if password matches, False if not.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int) -> str:
    """
    Creates a JWT token for the given user ID.
    This token is sent to the user after successful login.
    
    user_id: the ID of the user who just logged in
    returns: JWT token string
    """

    # The payload is the data we store inside the token
    # sub = subject = who this token belongs to
    # exp = expiry = when this token stops working
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }

    # jwt.encode() creates the token string
    # SECRET_KEY is used to sign it — only our server knows this key
    # If someone modifies the token, the signature breaks
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return token


def verify_token(token: str) -> int:
    """
    Reads a JWT token and returns the user ID inside it.
    Used to identify who is making an API request.
    
    Returns user_id if token is valid.
    Raises an exception if token is invalid or expired.
    """
    try:
        # jwt.decode() reads the token and verifies the signature
        # If the token was tampered with, this raises an error
        # If the token is expired, this raises an error
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Extract the user ID from the payload
        user_id = int(payload.get("sub"))
        return user_id

    except JWTError:
        raise Exception("Invalid or expired token")


def get_user_by_email(email: str, db: Session):
    """
    Looks up a user in the database by their email address.
    Returns the user object if found, None if not found.
    """
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(user_id: int, db: Session):
    """
    Looks up a user in the database by their ID.
    Returns the user object if found, None if not found.
    """
    return db.query(User).filter(User.id == user_id).first()


def register_user(email: str, password: str, full_name: str, db: Session):
    """
    Creates a new user in the database.
    Hashes the password before saving.
    """

    # Check if email already exists
    existing_user = get_user_by_email(email, db)
    if existing_user:
        raise Exception("Email already registered")

    # Hash the password before saving
    hashed = hash_password(password)

    # Create new user object
    new_user = User(
        email=email,
        hashed_password=hashed,
        full_name=full_name
    )

    # Save to database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user