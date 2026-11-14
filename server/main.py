from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api.reviews import router as reviews_router

app = FastAPI(
    title="Agentic Systematic Review API",
    description="API for the multi-agent systematic review pipeline",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reviews_router)


@app.get("/")
def root():
    return {
        "message": "Agentic Systematic Review API is running."
    }
