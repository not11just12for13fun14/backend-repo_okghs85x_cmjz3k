import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson.objectid import ObjectId

from database import db, create_document, get_documents
from schemas import User, Movie, ListItem

app = FastAPI(title="Netflix Clone API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utilities

def to_str_id(doc):
    if not doc:
        return doc
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d

# Auth models (simplified demo — token = email for now)
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    token: str
    user: dict

@app.get("/")
def read_root():
    return {"message": "Netflix Clone Backend Running"}

@app.get("/test")
def test_database():
    response = {"backend": "✅ Running", "database": "❌ Not Available", "collections": []}
    try:
        collections = db.list_collection_names()
        response["database"] = "✅ Connected"
        response["collections"] = collections
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response

# Auth endpoints (very basic for demo)
@app.post("/api/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest):
    existing = db["user"].find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=payload.password,  # demo only
    )
    user_id = create_document("user", user)
    token = payload.email  # demo token
    db["user"].update_one({"_id": ObjectId(user_id)}, {"$push": {"tokens": token}})
    created = db["user"].find_one({"_id": ObjectId(user_id)})
    return AuthResponse(token=token, user=to_str_id(created))

@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    user = db["user"].find_one({"email": payload.email})
    if not user or user.get("password_hash") != payload.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = payload.email
    db["user"].update_one({"_id": user["_id"]}, {"$addToSet": {"tokens": token}})
    return AuthResponse(token=token, user=to_str_id(user))

# Movies
class MovieCreate(BaseModel):
    title: str
    description: Optional[str] = None
    year: Optional[int] = None
    genres: List[str] = []
    rating: Optional[float] = None
    duration_minutes: Optional[int] = None
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None
    featured: bool = False

@app.post("/api/movies")
def create_movie(movie: MovieCreate):
    movie_model = Movie(**movie.model_dump())
    new_id = create_document("movie", movie_model)
    created = db["movie"].find_one({"_id": ObjectId(new_id)})
    return to_str_id(created)

@app.get("/api/movies")
def list_movies(genre: Optional[str] = None, featured: Optional[bool] = None):
    q = {}
    if genre:
        q["genres"] = genre
    if featured is not None:
        q["featured"] = featured
    items = get_documents("movie", q)
    return [to_str_id(i) for i in items]

@app.get("/api/movies/{movie_id}")
def get_movie(movie_id: str):
    try:
        oid = ObjectId(movie_id)
    except Exception:
        raise HTTPException(400, "Invalid id")
    m = db["movie"].find_one({"_id": oid})
    if not m:
        raise HTTPException(404, "Movie not found")
    return to_str_id(m)

# Seed demo catalog
@app.post("/api/seed")
def seed_demo_movies():
    count = db["movie"].count_documents({})
    if count > 0:
        return {"message": "Catalog already seeded", "count": count}
    demo_thumb = "https://images.unsplash.com/photo-1524985069026-dd778a71c7b4?w=800&q=80&auto=format&fit=crop"
    demo_video = "https://samplelib.com/lib/preview/mp4/sample-5s.mp4"
    demos = [
        {"title": "The Horizon", "description": "A journey beyond the edge.", "year": 2023, "genres": ["Sci-Fi", "Adventure"], "rating": 8.1, "duration_minutes": 112, "thumbnail_url": demo_thumb, "video_url": demo_video, "featured": True},
        {"title": "Crimson City", "description": "Noir mystery in neon lights.", "year": 2022, "genres": ["Thriller"], "rating": 7.6, "duration_minutes": 98, "thumbnail_url": demo_thumb, "video_url": demo_video},
        {"title": "Laugh Track", "description": "Standup that hits home.", "year": 2021, "genres": ["Comedy"], "rating": 7.2, "duration_minutes": 62, "thumbnail_url": demo_thumb, "video_url": demo_video},
        {"title": "Planet Blue", "description": "Nature docu-series pilot.", "year": 2020, "genres": ["Documentary"], "rating": 8.7, "duration_minutes": 50, "thumbnail_url": demo_thumb, "video_url": demo_video},
        {"title": "Shadow School", "description": "Teens with secret powers.", "year": 2024, "genres": ["Drama", "Fantasy"], "rating": 7.9, "duration_minutes": 45, "thumbnail_url": demo_thumb, "video_url": demo_video}
    ]
    inserted = 0
    for d in demos:
        mid = create_document("movie", Movie(**d))
        if mid:
            inserted += 1
    return {"message": "Seeded", "inserted": inserted}

# My List
class ListRequest(BaseModel):
    token: str  # demo auth
    movie_id: str

@app.post("/api/list/add")
def add_to_list(payload: ListRequest):
    user = db["user"].find_one({"tokens": payload.token})
    if not user:
        raise HTTPException(401, "Invalid token")
    existing = db["listitem"].find_one({"user_id": str(user["_id"]), "movie_id": payload.movie_id})
    if existing:
        return to_str_id(existing)
    item = ListItem(user_id=str(user["_id"]), movie_id=payload.movie_id)
    item_id = create_document("listitem", item)
    created = db["listitem"].find_one({"_id": ObjectId(item_id)})
    return to_str_id(created)

@app.get("/api/list")
def get_list(token: str):
    user = db["user"].find_one({"tokens": token})
    if not user:
        raise HTTPException(401, "Invalid token")
    items = list(db["listitem"].find({"user_id": str(user["_id"])}))
    movie_ids = [ObjectId(i["movie_id"]) for i in items]
    movies = list(db["movie"].find({"_id": {"$in": movie_ids}})) if movie_ids else []
    return [to_str_id(m) for m in movies]

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
