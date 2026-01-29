import os
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://wiki:wiki@localhost:5432/wiki",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

USERS_CREATED = Counter("users_created_total", "Total number of users created")
POSTS_CREATED = Counter("posts_created_total", "Total number of posts created")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    posts = relationship("Post", back_populates="user")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(String(2000), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="posts")


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class PostCreate(BaseModel):
    user_id: int
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=2000)


class PostOut(BaseModel):
    id: int
    user_id: int
    title: str
    body: str
    created_at: datetime

    class Config:
        from_attributes = True


app = FastAPI(title="Wiki Service")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def ensure_tables() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/users", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    user = User(name=payload.name)
    db.add(user)
    db.commit()
    db.refresh(user)
    USERS_CREATED.inc()
    return user


@app.get("/users", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db)) -> List[UserOut]:
    return db.query(User).order_by(User.id).all()


@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserOut:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/posts", response_model=PostOut)
def create_post(payload: PostCreate, db: Session = Depends(get_db)) -> PostOut:
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    post = Post(user_id=payload.user_id, title=payload.title, body=payload.body)
    db.add(post)
    db.commit()
    db.refresh(post)
    POSTS_CREATED.inc()
    return post


@app.get("/posts", response_model=List[PostOut])
def list_posts(
    user_id: Optional[int] = None, db: Session = Depends(get_db)
) -> List[PostOut]:
    query = db.query(Post)
    if user_id is not None:
        query = query.filter(Post.user_id == user_id)
    return query.order_by(Post.id).all()


@app.get("/posts/{post_id}", response_model=PostOut)
def get_post(post_id: int, db: Session = Depends(get_db)) -> PostOut:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post
