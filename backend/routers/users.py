from typing import Annotated
from fastapi import APIRouter, Request, HTTPException, status, Depends
from schemas import PostResponse, UserUpdate
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from schemas import PostResponse, UserCreate, UserPrivate, UserPublic, Token
import models
from database import get_db

from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm
from auth import (
    create_access_token,
    hash_password,
    oauth2_scheme,
    verify_access_token,
    verify_password
)
from config import settings
router = APIRouter()

@router.post(
    "", response_model=UserPrivate, status_code=status.HTTP_201_CREATED
)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User)
        .where(func.lower(models.User.username) == user.username.lower())
    )
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A User Exist with this username.",
        )
    result = await db.execute(
        select(models.User)
        .where(func.lower(models.User.email) == user.email.lower())
    )
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A User Exist with this email.",
        )
    new_user = models.User(
        username=user.username,
        email=user.email.lower(),
        password_hash=hash_password(user.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post(
    "/token", response_model=Token
)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        select(models.User)
        .where(func.lower(models.User.email) == form_data.username.lower())
    )
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect Email or Password.",
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub":str(user.id)
        },
        expires_delta=access_token_expires
    )
    return Token(
        access_token=access_token,
        token_type="bearer"
    )

@router.get(
    "/me", response_model=UserPrivate
)
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)]   
):
    user_id = verify_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate":"Bearer"}
        )
    
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate":"Bearer"}
        )
    result = await db.execute(
        select(models.User).where(models.User.id == user_id_int)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate":"Bearer"}
        )
    return user

    
@router.patch(
    "/{user_id}", response_model=UserPrivate, status_code=status.HTTP_201_CREATED
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
    if  user.username and existing_user.username.lower() != user.username.lower():
        result = await db.execute(select(models.User).where(
            func.lower(models.User.username) == user.username.lower(), 
            models.User.id != user_id )).scalars().first()
        if result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A User Exist with this username.",
            )
    if  user.email and existing_user.email != user.email.lower():
        result = await db.execute(select(models.User).where(
            func.lower(models.User.email) == user.email.lower(),
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
    if user.username is not None:
        existing_user.username = user.username
    if user.email is not None:
        existing_user.email = user.email
    if user.image_file is not None: 
        existing_user.image_file = user.image_file
     
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



@router.get("/{user_id}", response_model=UserPublic)
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

