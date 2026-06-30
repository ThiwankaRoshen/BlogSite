from typing import Annotated
from fastapi import APIRouter, Request, HTTPException, status, Depends
from schemas import PostResponse, UserUpdate
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from schemas import PostResponse, UserCreate, UserResponse
import models
from database import get_db


router = APIRouter()

@router.post(
    "", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User).where(models.User.username == user.username)
    )
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A User Exist with this username.",
        )
    result = await db.execute(select(models.User).where(models.User.email == user.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A User Exist with this email.",
        )

    new_user = models.User(**user.model_dump())
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user



@router.patch(
    "/{user_id}", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def update_user_patch(user_id: int, user: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    existing_user = result.scalars().first()
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not Exist.",
        )
    if  user.username and existing_user.username != user.username:
        result = await db.execute(select(models.User).where(
            models.User.username == user.username, 
            models.User.id != user_id )).scalars().first()
        if result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A User Exist with this username.",
            )
    if  user.email and existing_user.email != user.email:
        result = await db.execute(select(models.User).where(
            models.User.email == user.email ,
            models.User.id != user_id)).scalars().first()
        if result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A User Exist with this email.",
            )
    if  user.image_file and existing_user.image_file != user.image_file:
        result = await db.execute(select(models.User).where(
            models.User.image_file == user.image_file ,
            models.User.id != user_id)).scalars().first()
        if result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A User Exist with this image file.",
            )
    update_data = user.model_dump(exclude_unset=True) 
    
    for field, val in update_data.items():
        setattr(existing_user, field, val)
        
    await db.commit()
    await db.refresh(existing_user)
    return existing_user

@router.delete(
    "/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    existing_user = result.scalars().first()
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not Exist.",
        )
    
    await db.delete(existing_user)
    await db.commit()



@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User Doesn't Exist."
        )
    return user


@router.get("/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User Doesn't Exist."
        )
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user.id)
        .order_by(models.Post.date_posted.desc())    
    )
    posts = result.scalars().all()
    return posts

