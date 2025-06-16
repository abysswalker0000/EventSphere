from fastapi import APIRouter, HTTPException, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func
from typing import List
import logging

from app.database import get_db
from app.models.category import Category
from app.models.event import Event
from app.models.user import User 
from app.schemas.category import CategorySchema, CategoryResponseSchema, CategoryUpdateSchema
from app.auth.dependencies import get_current_active_user, get_current_admin_user 

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/categories",
    tags=["Categories"]
)

@router.get(
    "/", 
    summary="Get all categories", 
    response_model=List[CategoryResponseSchema]
)
async def get_all_categories_public(
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(Category).order_by(Category.name))
        categories = result.scalars().all()
        return categories
    except Exception as e:
        logger.error(f"Error fetching categories: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching categories."
        )

@router.post(
    "/", 
    summary="Create new category (Admin only)", 
    response_model=CategoryResponseSchema, 
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_admin_user)] 
)
async def create_category_admin(
    new_category_data: CategorySchema,
    db: AsyncSession = Depends(get_db)
):
    existing_category_check = await db.execute(select(Category).filter(Category.name == new_category_data.name))
    if existing_category_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A category with the name '{new_category_data.name}' already exists."
        )

    db_category = Category(name=new_category_data.name)
    db.add(db_category)
    try:
        await db.commit()
        await db.refresh(db_category)
        logger.info(f"Category '{db_category.name}' created.") 
    except IntegrityError as e_integrity: 
        await db.rollback()
        logger.warning(
            f"IntegrityError creating category with name '{new_category_data.name}': {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=f"A category with the name '{new_category_data.name}' already exists or another integrity constraint was violated."
        )
    except Exception as e_general:
        await db.rollback()
        logger.error(
            f"Unexpected error creating category with name '{new_category_data.name}': {str(e_general)}",
            exc_info=True 
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the category."
        )
    return db_category

@router.get(
    "/{category_id}", 
    summary="Get specific category", 
    response_model=CategoryResponseSchema
)
async def get_category_by_id_public(
    category_id: int, 
    db:AsyncSession = Depends(get_db)
):
    category: Category | None = None
    try:
        result = await db.execute(select(Category).filter(Category.id == category_id))
        category = result.scalars().first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id {category_id} not found."
            )
        return category
    except HTTPException: 
        raise
    except Exception as e:
        logger.error(f"Error fetching specific category with id {category_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching specific category with id {category_id}."
        )
    
@router.patch(
    "/{category_id}", 
    summary="Update category name (Admin only)", 
    response_model=CategoryResponseSchema,
    dependencies=[Depends(get_current_admin_user)] 
)
async def update_category_admin( 
    category_id: int, 
    category_update_data: CategoryUpdateSchema, 
    db:AsyncSession = Depends(get_db)
):
    db_category: Category | None = None
    update_payload_str = category_update_data.model_dump_json(exclude_unset=True)
    try:
        result = await db.execute(select(Category).filter(Category.id == category_id))
        db_category = result.scalars().first()

        if not db_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id {category_id} not found to update."
            )
        
        updated_data = category_update_data.model_dump(exclude_unset=True)
        if not updated_data: 
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update."
            )

        if updated_data.get("name") and updated_data["name"] != db_category.name:
            existing_name_check = await db.execute(
                select(Category).filter(Category.name == updated_data["name"], Category.id != category_id)
            )
            if existing_name_check.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A category with the name '{updated_data['name']}' already exists."
                )

        for key, value in updated_data.items():
            setattr(db_category, key, value)
        
        await db.commit()
        await db.refresh(db_category)
        logger.info(f"Category ID {category_id} updated. New name: {db_category.name if 'name' in updated_data else '(not changed)'}")
        return db_category

    except IntegrityError as e_integrity: 
        await db.rollback()
        logger.warning(
            f"IntegrityError updating category id {category_id} with payload {update_payload_str}: {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot update category: the new name might already exist or another integrity constraint was violated."
        )
    except HTTPException:
        raise
    except Exception as e_general:
        await db.rollback()
        category_name_for_log = db_category.name if db_category else "N/A"
        logger.error(
            f"Error updating category id {category_id} (name: {category_name_for_log}) with payload {update_payload_str}: {str(e_general)}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating category {category_id}."
        )
    
@router.delete(
    "/{category_id}",
    summary="Delete a category (Admin only)",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin_user)] 
)
async def delete_category_admin(
    category_id: int, 
    db: AsyncSession = Depends(get_db)
):
    db_category_to_delete: Category | None = None
    try:
        result = await db.execute(select(Category).filter(Category.id == category_id))
        db_category_to_delete = result.scalars().first()

        if not db_category_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id {category_id} not found."
            )

        event_count_result = await db.execute(
            select(func.count(Event.id)).where(Event.category_id == category_id)
        )
        associated_events_count = event_count_result.scalar_one_or_none() or 0

        if associated_events_count > 0:
            logger.warning(
                f"Admin attempt to delete category '{db_category_to_delete.name}' (ID: {category_id}) which has {associated_events_count} associated event(s)."
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete category '{db_category_to_delete.name}' (ID: {category_id}): it is currently associated with {associated_events_count} event(s)."
            )

        category_name_for_log = db_category_to_delete.name 
        await db.delete(db_category_to_delete)
        await db.commit()
        
        logger.info(f"Category '{category_name_for_log}' (ID: {category_id}) deleted successfully.")
        return Response(status_code=status.HTTP_204_NO_CONTENT)


    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        category_name_for_log = db_category_to_delete.name if db_category_to_delete else "N/A"
        logger.error(
            f"Error deleting category with id {category_id} (name: {category_name_for_log}): {str(e)}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting category with id {category_id}."
        )