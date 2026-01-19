from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.health import router as health_router
from routes.inference import router as inference_router
from routes.stream import router as stream_router
from routes.kafka import router as kafka_router
from routes.data import router as data_router
import os

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

app = FastAPI(
    title="Forex Time Series Forecasting API",
    description="Real-time forex price prediction and streaming API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(inference_router, tags=["inference"])
app.include_router(stream_router, prefix="/stream", tags=["streaming"])
app.include_router(kafka_router, prefix="/kafka", tags=["kafka"])
app.include_router(data_router, prefix="/data", tags=["data"])


@app.get("/")
async def root():
    return {"message": "Forex Time Series Forecasting API is running."}
