from fastapi import FastAPI
from pydantic import BaseModel, Field
from groq import Groq
from pymongo import MongoClient
import certifi
import json
import logging
from fastapi.middleware.cors import CORSMiddleware
import os

cache = {}

# Logging setup
logging.basicConfig(level=logging.INFO)

# MongoDB connection
client_mongo = MongoClient(
    os.getenv("MONGO_URL"),
    tls=True,
    tlsCAFile=certifi.where(),
    tlsAllowInvalidCertificates=True
)

db = client_mongo["ai_database"]
collection = db["posts"]

# FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all (for now)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Request schema
class RequestData(BaseModel):
    topic: str = Field(min_length=3, max_length=50)

# Generate post
@app.post("/generate-post")
def generate_post(data: RequestData):
    if not data.topic.strip():
        return {
            "success": False,
            "message": "Topic cannot be empty",
            "data": None
        }
        
    if data.topic in cache:
        return {
            "success": True,
            "message": "Returned from cache",
            "data": cache[data.topic],
            "meta": {
                "cached": True
            }
        }

    for i in range(3):
        try:
            prompt = f"""
            Generate a HIGHLY engaging LinkedIn post on the topic: "{topic}"

            Rules:
            - First line must be a strong hook (curiosity/emotion)
            - Use short sentences
            - Use line breaks (very important)
            - Write like a human, not AI
            - Add a personal tone
            - Add 1 relatable insight
            - End with a call-to-action (question or thought)

            Format:
            Return ONLY this JSON:
            {{
                "post": "...",
                "score": number (0-100 based on virality)
            }}
            """

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a LinkedIn content writer"},
                    {"role": "user", "content": prompt}
                ]
            )

            content = response.choices[0].message.content

            # Debug log (see raw AI output if needed)
            logging.info(f"Raw AI Response: {content}")

            # Parse JSON
            try:
                parsed = json.loads(content)
            except Exception as e:
                logging.error(f"JSON Parsing Error: {content}")
                continue

            # Validate structure
            if not isinstance(parsed, dict):
                continue

            post = parsed.get("post")
            score = parsed.get("score")

            # Validate types
            if not isinstance(post, str):
                continue

            try:
                score = int(score)
            except:
                continue

            # Validate content
            if not post or len(post.strip()) < 50:
                continue

            logging.info(f"Attempt {i+1} | Score: {score}")

            # Accept only high-quality
            if score >= 80:
                break
            else:
                if i == 2:
                    return {
                        "success": False,
                        "message": "Failed to generate high-quality content",
                        "data": None
                    }

        except Exception as e:
            return {
                "success": False,
                "message": f"Server error: {str(e)}",
                "data": None
            }

    # Save to MongoDB
    collection.insert_one({
        "topic": data.topic,
        "post": post,
        "score": score
    })

    result = {
        "topic": data.topic,
        "post": post,
        "score": score
    }

    cache[data.topic] = result
    return {
        "success": True,
        "message": "Post generated successfully",
        "data": result,
        "meta": {
            "attempts": i + 1,
            "cached": False
        }
    }

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