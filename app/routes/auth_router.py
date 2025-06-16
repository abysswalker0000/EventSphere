from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from app.database import get_db
from app.auth import schemas_auth, security
from app.auth import user_crud
from app.schemas.user import UserResponseSchema 
from app.auth.schemas_auth import UserWithTokenResponse
from app.config import settings
from app.models.user import User 
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/token", response_model=schemas_auth.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    user = await user_crud.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for email: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        logger.warning(f"Inactive user login attempt: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user. Please contact support.",
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": str(user.id)}, 
        expires_delta=access_token_expires
    )
    logger.info(f"User logged in successfully: {user.email}")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserWithTokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: schemas_auth.UserCreateAuthSchema,
    db: AsyncSession = Depends(get_db)
):
    existing_user = await user_crud.get_user_by_email(db, email=user_in.email)
    if existing_user:
        logger.warning(f"Registration attempt with existing email: {user_in.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )
    try:
        created_user = await user_crud.register_new_user(db=db, user_in=user_in)
        logger.info(f"User registered successfully: {created_user.email}")
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
        data={"sub": str(created_user.id)},
        expires_delta=access_token_expires
         )
        return {"user": created_user, "token": {"access_token": access_token, "token_type": "bearer"}}
    except Exception as e_general:
        await db.rollback() 
        logger.error(
            f"Unexpected error during user registration for email {user_in.email}: {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration."
        )