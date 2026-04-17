from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models.request import RequestData
from services.generator import generate_post
from db.mongo import collection
import logging
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from fastapi.exceptions import HTTPException
from models.response import APIResponse
from fastapi import HTTPException
from bson import ObjectId
from fastapi.responses import FileResponse
import json
from auth import hash_password, create_token
from auth import verify_password
from fastapi import Header, HTTPException
from jose import jwt
from config import SECRET_KEY, ALGORITHM


user_collection = collection

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# FastAPI app
app = FastAPI()
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": str(exc),
            "data": None
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None
        }
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all (for now)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logging.info(f"Request: {request.method} {request.url}")

    response = await call_next(request)

    logging.info(f"Response Status: {response.status_code}")

    return response

@app.post("/signup")
def signup(data: RequestData):
    user = {
        "username": data.topic,  # reuse for now
        "password": hash_password("1234")  # demo
    }
    user_collection.insert_one(user)

    return {"message": "User created"}

@app.post("/login")
def login(data: RequestData):
    user = user_collection.find_one({"username": data.topic})

    if not user:
        return {"error": "User not found"}

    if not verify_password("1234", user["password"]):
        return {"error": "Wrong password"}

    token = create_token({"sub": data.topic})

    return {"access_token": token}

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

# Generate post
@app.post("/generate-post")
def generate_post_api(data: RequestData):
    result = generate_post(data.topic)
    return result

# Get all posts
@app.get("/posts")
def get_posts():
    return list(collection.find({}, {"_id": 0}))

# Get top posts
@app.get("/topposts")
def top_posts():
    return list(collection.find(
        {"score": {"$gte": 80}},
        {"_id": 0}
    ))

# Get posts by topic
@app.get("/topic")
def topic1(topic: str):
    return list(collection.find(
        {"topic": topic},
        {"_id": 0}
    ))

@app.post("/favorite/{post_id}")
def mark_favorite(post_id: str):
    result = collection.update_one(
        {"_id": ObjectId(post_id)},
        {"$set": {"favorite": True}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Post not found")

    return {
        "success": True,
        "message": "Marked as favorite",
        "data": {"post_id": post_id}
    }

@app.get("/favorites")
def get_favorites():
    posts = list(collection.find({"favorite": True}))

    for p in posts:
        p["_id"] = str(p["_id"])

    return {
        "success": True,
        "message": "Favorite posts",
        "data": posts
    }

@app.post("/unfavorite/{post_id}")
def unmark_favorite(post_id: str):
    collection.update_one(
        {"_id": ObjectId(post_id)},
        {"$set": {"favorite": False}}
    )

    return {
        "success": True,
        "message": "Removed from favorites",
        "data": {"post_id": post_id}
    }

@app.get("/export")
def export_posts():
    posts = list(collection.find({}, {"_id": 0}))

    # Save to file
    file_path = "posts.json"
    with open(file_path, "w") as f:
        json.dump(posts, f, indent=4)

    return FileResponse(
        path=file_path,
        filename="posts.json",
        media_type="application/json"
    )

@app.get("/search")
def search_posts(query: str):
    posts = list(collection.find(
        {"topic": {"$regex": query, "$options": "i"}},
        {"_id": 0}
    ))
    return posts

@app.get("/analytics")
def get_analytics():
    posts = list(collection.find())

    total = len(posts)

    if total == 0:
        return {
            "total_posts": 0,
            "avg_score": 0,
            "max_score": 0
        }

    scores = [p.get("score", 0) for p in posts]

    avg_score = sum(scores) / total
    max_score = max(scores)

    return {
        "total_posts": total,
        "avg_score": round(avg_score, 2),
        "max_score": max_score
    }

@app.get("/export/text")
def export_text():
    posts = list(collection.find({}, {"_id": 0}))

    file_path = "posts.txt"

    with open(file_path, "w") as f:
        for i, p in enumerate(posts, 1):
            f.write(f"Post {i}\n")
            f.write(f"Topic: {p['topic']}\n")
            f.write(f"Score: {p['score']}\n")
            f.write(f"{p['post']}\n")
            f.write("\n" + "-"*40 + "\n\n")

    return FileResponse(file_path, filename="posts.txt")