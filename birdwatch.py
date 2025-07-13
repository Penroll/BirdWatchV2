import os
import secrets
import asyncio
import crud
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from camera import take_photo
from database import SessionLocal, engine, Base
from inference_utils import perform_inference
from dotenv import load_dotenv, set_key

Base.metadata.create_all(bind=engine)

ENV_PATH = ".env"
load_dotenv(dotenv_path=ENV_PATH)
FEEDER_TOKEN = os.getenv("FEEDER_TOKEN")
if FEEDER_TOKEN is None:
    FEEDER_TOKEN = secrets.token_urlsafe(32)
    set_key(ENV_PATH, "FEEDER_TOKEN", FEEDER_TOKEN)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def add_birds_from_bg(names: str):
    db_gen = get_db()        # get the generator
    db = next(db_gen)        # get the actual Session
    try:
        result = crud.add_birds(db, names)
        return result
    finally:
        db_gen.close()

background_task = None

@asynccontextmanager
async def lifespan(fastapp: FastAPI):
    global background_task
    async def run_inference_loop():
        while True:
            image = take_photo()
            result = perform_inference(image)
            print(f"inference result: {result}")
            add_birds_from_bg(result)
            await asyncio.sleep(15)

    background_task = asyncio.create_task(run_inference_loop())

    print("Background inference task started.")

    yield

    background_task.cancel()

    print("Background inference task canceled")

    try:
        await background_task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/api/birds")
def get_birds(db: Session = Depends(get_db)):
    birds = crud.get_birds(db)
    if birds is None:
        raise HTTPException(status_code=404, detail="Not Found")
    return birds

@app.post("/api/add_birds")
def add_birds(names: str, db: Session = Depends(get_db)):
    result = crud.add_birds(db, names)
    if result is None:
        raise HTTPException(status_code=500, detail="Internal server error")
    return result