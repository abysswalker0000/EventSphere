from fastapi import APIRouter, HTTPException, Depends,status
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.category import CategorySchema, CategoryResponseSchema, CategoryUpdateSchema
from app.models.category import Category
from app.models.event import Event
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from sqlalchemy import select, func
from typing import List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    tags= ["Categories"],
    prefix="/categories"
)

@router.get("/", summary="Get all categories", response_model=List[CategoryResponseSchema])
async def get_categories(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Category))
        categories = result.scalars().all()
        return categories
    except Exception as e:
        logger.error(f"Error fetching categories : {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching categories"
        )

@router.post("/", summary="Create new category", response_model=CategoryResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_category(new_category: CategorySchema, db:AsyncSession = Depends(get_db)):
    db_category = Category(name = new_category.name)
    db.add(db_category)
    try:
        await db.commit()
        await db.refresh(db_category)
    except IntegrityError as e_integrity:
        await db.rollback()
        logger.warning(
            f"IntegrityError creating category with name '{new_category.name}': {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=f"A category with the name '{new_category.name}' already exists or another integrity constraint was violated"
        )
    except Exception as e_general:
        await db.rollback()
        logger.error(
            f"Unexpected error creating category with name '{new_category.name}': {str(e_general)}",
            exc_info=True 
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the category"
        )
    return db_category

@router.get("/{category_id}", summary="Get specific category", response_model = CategoryResponseSchema)
async def get_category_by_id(category_id: int, db:AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Category).filter(Category.id == category_id))
        category = result.scalars().first()
        return category
    except Exception as e:
        logger.error(f"Error fetching specific category with id {category_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching specific category"
        )
    
@router.patch("/{category_id}", summary="Update category name", response_model=CategoryResponseSchema)
async def change_category_name(category_id: int, category_update: CategoryUpdateSchema, db:AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Category).filter(Category.id == category_id))
        db_category = result.scalars().first()
        if not db_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category not found"
            )
        updated_data = category_update.model_dump(exclude_unset=True)
        if not updated_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided to update"
            )
        for key, value in updated_data.items():
            setattr(db_category,key,value)
        await db.commit()
        await db.refresh(db_category)
        return db_category
    except IntegrityError as e_integrity:
        await db.rollback()
        logger.warning(
            f"IntegrityError updating category id {category_id} with data {updated_data}: {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot update category: the new name '{category_update.name}' might already exist or another integrity constraint was violated."
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error updating category id {category_id} with data {updated_data}: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the category."
        )
    
@router.delete(
    "/{category_id}",
    summary="Delete a category",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
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
                f"Attempt to delete category '{db_category_to_delete.name}' (ID: {category_id}) which has {associated_events_count} associated event(s)."
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete category '{db_category_to_delete.name}' (ID: {category_id}): it is currently associated with {associated_events_count} event(s)."
            )

        await db.delete(db_category_to_delete)
        await db.commit()
        
        logger.info(f"Category '{db_category_to_delete.name}' (ID: {category_id}) deleted successfully.")
        return None

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