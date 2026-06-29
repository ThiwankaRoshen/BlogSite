from typing import Annotated
from fastapi import APIRouter, Request, HTTPException, status, Depends
from schemas import PostCreate, PostResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from schemas import PostCreate, PostResponse, PostUpdate, UserResponse
import models
from database import get_db

router = APIRouter()


@router.delete(
    "/{post_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id)
    )
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not Found"
        )
    await db.delete(post)
    await db.commit()

@router.post(
    "", response_model=PostResponse, status_code=status.HTTP_201_CREATED
)
async def create_post(post: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    new_post = models.Post(**post.model_dump())
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=["author"])
    return new_post


@router.put(
    "/{post_id}", response_model=PostResponse, status_code=status.HTTP_201_CREATED
)
async def update_post_full(post_id: int, post: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Post).where(models.Post.id == post_id)
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not Found."
        )
    existing_post = result.scalars().first()
    if existing_post.user_id != post.user_id:
        result = await db.execute(
            select(models.User).where(models.User.id == post.user_id)
        )
        user = result.scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not Found."
            )
    existing_post.content = post.content
    existing_post.title = post.title
    existing_post.user_id = post.user_id
    
     
    await db.commit()
    await db.refresh(existing_post, attribute_names=["author"])
    return existing_post


@router.patch(
    "/{post_id}", response_model=PostResponse, status_code=status.HTTP_201_CREATED
)
async def update_post_patch(post_id: int, post: PostUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Post).where(models.Post.id == post_id)
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not Found."
        )
    existing_post = result.scalars().first()
    update_data = post.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing_post, field, value)
         
    await db.commit()
    await db.refresh(existing_post, attribute_names=["author"])
    return existing_post



@router.get("", response_model=list[PostResponse])
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post))
    posts = result.scalars().all()
    return posts


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )
    return post
