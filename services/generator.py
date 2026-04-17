from groq import Groq
import os
import json
import logging
from db.mongo import collection
from config import GROQ_API_KEY


# Groq client
client = Groq(api_key=GROQ_API_KEY)

cache = {}

def generate_post(topic: str):
    logging.info(f"Generating post for topic: {topic}")
    post = None
    score = 0
    if not topic.strip():
        return {
            "success": False,
            "message": "Topic cannot be empty",
            "data": None
        }
        
    if topic in cache:
        return {
            "success": True,
            "message": "Returned from cache",
            "data": cache[topic],
            "meta": {
                "cached": True
            }
        }

    for i in range(3):
        try:
            prompt = f"""
You are a professional LinkedIn content writer.

Return output in STRICT JSON format:

{{
  "post": "clean linkedin post without markdown or special characters",
  "score": number between 0 and 100
}}

Rules:
- No bold, no emojis, no extra formatting
- No explanation
- Only valid JSON
- Post should be engaging and professional

Topic: {topic}
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
            logging.info(f"Attempt {i+1}")

            # Parse JSON
            try:
                parsed = json.loads(content)
            except Exception as e:
                logging.error(f"Error: {str(e)}")
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
    if not post:
        return {
            "success": False,
            "message": "Failed to generate valid post",
            "data": None
        }
    # Save to MongoDB
    post_data = {
        "topic": topic,
        "post": post,
        "score": score,
        "favorite": False
    }
    inserted = collection.insert_one(post_data)

    result = {
        "topic": topic,
        "post": post,
        "score": score,
        "id": str(inserted.inserted_id)
    }

    cache[topic] = result
    return {
        "success": True,
        "message": "Post generated successfully",
        "data": result,
        "meta": {
            "attempts": i + 1,
            "cached": False
        }
    }
    