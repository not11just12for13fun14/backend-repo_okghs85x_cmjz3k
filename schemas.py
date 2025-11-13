"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Movie -> "movie" collection
- ListItem -> "listitem" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user"
    """
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password_hash: str = Field(..., description="Password hash")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tokens: Optional[List[str]] = Field(default_factory=list, description="Auth tokens")

class Movie(BaseModel):
    """
    Movies collection schema
    Collection name: "movie"
    """
    title: str = Field(..., description="Movie or show title")
    description: Optional[str] = Field(None, description="Synopsis")
    year: Optional[int] = Field(None, ge=1900, le=2100)
    genres: List[str] = Field(default_factory=list, description="Genres/categories")
    rating: Optional[float] = Field(None, ge=0, le=10)
    duration_minutes: Optional[int] = Field(None, ge=1)
    thumbnail_url: Optional[str] = Field(None, description="Poster or thumbnail image URL")
    video_url: Optional[str] = Field(None, description="Streamable video URL (demo)")
    featured: bool = Field(False, description="Whether to highlight on homepage")

class ListItem(BaseModel):
    """
    User saved list items
    Collection name: "listitem"
    """
    user_id: str = Field(..., description="User _id as string")
    movie_id: str = Field(..., description="Movie _id as string")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
