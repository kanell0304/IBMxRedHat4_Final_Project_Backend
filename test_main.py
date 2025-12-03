from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import communication, image, interview, audio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(communication.router)
app.include_router(image.router)
app.include_router(interview.router)
app.include_router(audio.router)