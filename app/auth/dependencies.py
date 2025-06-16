from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
import logging

from app.database import get_db
from app.models.user import User
from app.auth import security 
from app.auth import user_crud 
from app.config import settings

logger = logging.getLogger(__name__)

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

async def get_current_user(
    token: str = Depends(security.oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            logger.warning("Token decoding error: 'sub' claim missing.")
            raise credentials_exception
        
        try:
            user_id = int(user_id_str)
        except ValueError:
            logger.warning(f"Token decoding error: 'sub' claim '{user_id_str}' is not a valid integer.")
            raise credentials_exception

    except JWTError as e:
        logger.warning(f"Token validation error: {str(e)}")
        raise credentials_exception
    
    user = await user_crud.get_user_by_id(db, user_id=user_id)
    if user is None:
        logger.warning(f"User not found for ID {user_id} from token.")
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        logger.warning(f"Inactive user access attempt: {current_user.email} (ID: {current_user.id})")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user.")
    return current_user

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    if current_user.role != "admin":
        logger.warning(f"Non-admin user {current_user.email} (ID: {current_user.id}) attempted admin action.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Operation not permitted. Administrator privileges required."
        )
    return current_user

async def get_current_organizer_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    if current_user.role not in ["organizer", "admin"]:
        logger.warning(f"User {current_user.email} (ID: {current_user.id}) with role '{current_user.role}' attempted organizer action.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. Organizer or administrator privileges required."
        )
    return current_user