from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler
)
from fastapi.exceptions import RequestValidationError
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StartletteHttpException
from schemas import PostCreate, PostResponse, UserUpdate
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from schemas import PostCreate, PostResponse, PostUpdate, UserCreate, UserResponse
import models
from database import Base, engine, get_db


@asynccontextmanager
async def lifesapn(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
    

app = FastAPI(lifespan=lifesapn)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")
templates = Jinja2Templates(directory="templates")


@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author))
    )
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request, "home.html", {"posts": posts, "title": "Home"}
    )


@app.post(
    "/api/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED
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
    result = db.execute(select(models.User).where(models.User.email == user.email))
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



@app.patch(
    "/api/users/{user_id}", response_model=UserResponse, status_code=status.HTTP_201_CREATED
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

@app.delete(
    "/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT
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



@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User Doesn't Exist."
        )
    return user


@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User Doesn't Exist."
        )
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.user_id == user.id))
    posts = result.scalars().all()
    return posts


@app.get("/users/{user_id}/posts", include_in_schema=False, name="author_posts_page")
async def author_posts_page(
    request: Request, user_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    author = result.scalars().first()
    if not author:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User Doesn't Exist."
        )

    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.user_id == author.id))
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "author_posts.html",
        {"posts": posts, "author": author, "title": f"Posts by {author.username}"},
    )


@app.get("/posts/{post_id}", include_in_schema=False)
async def post_page(request: Request, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )
    return templates.TemplateResponse(
        request, "post.html", {"post": post, "title": post.title}
    )
    

@app.delete(
    "/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT
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

@app.post(
    "/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED
)
async def create_post(post: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    new_post = models.Post(**post.model_dump())
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=["author"])
    return new_post


@app.put(
    "/api/posts/{post_id}", response_model=PostResponse, status_code=status.HTTP_201_CREATED
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


@app.patch(
    "/api/posts/{post_id}", response_model=PostResponse, status_code=status.HTTP_201_CREATED
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



@app.get("/api/posts", response_model=list[PostResponse])
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post))
    posts = result.scalars().all()
    return posts


@app.get("/api/posts/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )
    return post


@app.exception_handler(StartletteHttpException)
async def general_http_exception_handler(
    request: Request, exception: StartletteHttpException
):

    if request.url.path.startswith("/api"):
        return http_exception_handler(request, exception)

    message = exception.detail if exception.detail else "An Error Occured."
    return templates.TemplateResponse(
        request,
        "error.html",
        {"status_code": exception.status_code, "message": message},
        status_code=exception.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exception: RequestValidationError
):
    if request.url.path.startswith("/api"):
        return validation_exception_handler(request, exception)

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Check your inputs again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )
