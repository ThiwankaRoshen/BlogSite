from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StartletteHttpException
from schemas import PostCreate, PostResponse

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

posts: list[dict] = [
    {
        "id": 1,
        "author": "Trx",
        "title": "FastAPI",
        "content": "This framework is great",
        "date_posted": "April 20, 2013",
    },
    {
        "id": 2,
        "author": "Trx",
        "title": "Python Tips",
        "content": "Use type hints for clarity",
        "date_posted": "May 5, 2014",
    },
    {
        "id": 3,
        "author": "Trx",
        "title": "Async IO",
        "content": "Async operations can improve performance",
        "date_posted": "June 12, 2015",
    },
]


@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
def home(request: Request):
    return templates.TemplateResponse(
        request, "home.html", {"posts": posts, "title": "Home"}
    )


@app.get("/posts/{post_id}", include_in_schema=False)
def post_page(request: Request, post_id: int):
    post = next((p for p in posts if p["id"] == post_id), None)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )
    return templates.TemplateResponse(
        request, "post.html", {"post": post, "title": post["title"]}
    )


@app.post("/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(post: PostCreate):
    new_id = max(p["id"] for p in posts) + 1 if posts else 1
    new_post = {
        "id": new_id,
        **post.model_dump(),
        "date_posted": "April 20, 2910"
    }
    posts.append(new_post)
    return new_post

@app.get("/api/posts", response_model=list[PostResponse])
def get_posts():
    return posts


@app.get("/api/posts/{post_id}", response_model=PostResponse)
def get_post(post_id: int):
    post = next((p for p in posts if p["id"] == post_id), None)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )
    return post


@app.exception_handler(StartletteHttpException)
async def general_http_exception_handler(request: Request, exception: StartletteHttpException):
    message = (
        exception.detail
        if exception.detail
        else "An Error Occured."
    )
    
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=exception.status_code,
            content={
                "detail":message
            }
        )

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code, 
            "message": exception.detail
        },
        status_code=exception.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "detail":exception.errors()
            }
        )

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Check your inputs again."
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )
