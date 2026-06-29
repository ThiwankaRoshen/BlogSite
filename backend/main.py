from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


posts: list[dict] = [
    {
        "id": 1,
        "author": "Trx",
        "title": "FastAPI",
        "content": "This framework is great",
        "date_posted": "April 20, 2013"
    },
    {
        "id": 2,
        "author": "Trx",
        "title": "Python Tips",
        "content": "Use type hints for clarity",
        "date_posted": "May 5, 2014"
    },
    {
        "id": 3,
        "author": "Trx",
        "title": "Async IO",
        "content": "Async operations can improve performance",
        "date_posted": "June 12, 2015"
    }
]

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/posts", response_class=HTMLResponse, include_in_schema=False)
def home():
    return f"<h1>{posts[0]}</h1>"
    
    
@app.get("/api/posts")
def get_posts():
    return posts