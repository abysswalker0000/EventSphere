from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.category import CategorySchema
from app.models.category import Category
from app.database import get_db
from sqlalchemy import select

router = APIRouter()

@router.get("/", tags=["Categories"], summary="Get all categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category))
    categories = result.scalars().all()
    return categories

@router.post("/", tags= ["Categories"], summary="Create new category")
async def create_category(new_category: CategorySchema, db:AsyncSession = Depends(get_db)):
    db_category = Category(name = new_category.name)
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    return {"success": True, "message": "Category added successfully" }