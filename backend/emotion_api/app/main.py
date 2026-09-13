"""
FastAPI Application for Emotion Recognition API
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import numpy as np
import time
import asyncio
from typing import Optional, List
from pydantic import BaseModel

from app.config import settings
from app.services.inference import inference_engine, EmotionPrediction
from app.services.audio import audio_processor
from app.services.video import video_processor


# ============================================================
# LIFESPAN MANAGEMENT
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events"""
    print("=" * 60)
    print(f"🚀 Starting {settings.APP_NAME} v{settings.VERSION}")
    print("=" * 60)
    
    # Initialize all components concurrently
    await asyncio.gather(
        inference_engine.initialize(),
        audio_processor.initialize(),
        video_processor.initialize()
    )
    
    print("=" * 60)
    print("✅ All models loaded successfully!")
    print(f"   Backend: {settings.INFERENCE_BACKEND}")
    print(f"   Device: {settings.DEVICE}")
    print("=" * 60)
    
    yield
    
    # Cleanup
    print("👋 Shutting down...")
    inference_engine.cleanup()
    audio_processor.cleanup()
    video_processor.cleanup()
    print("✅ Shutdown complete")


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Real-time multimodal emotion recognition from audio and video",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# RESPONSE MODELS
# ============================================================

class PredictionResponse(BaseModel):
    emotion: str
    confidence: float
    valence: str
    arousal: str
    intensity: str
    probabilities: dict

class TimingInfo(BaseModel):
    feature_extraction_ms: float
    inference_ms: float
    total_ms: float

class FullResponse(BaseModel):
    success: bool
    prediction: PredictionResponse
    timing: TimingInfo

class HealthResponse(BaseModel):
    status: str
    version: str
    device: str
    backend: str
    models_loaded: bool

class EmbeddingsRequest(BaseModel):
    audio: List[List[List[float]]]      # [1, 200, 1024]
    vit: List[List[List[float]]]        # [1, 32, 768]
    landmarks: List[List[List[float]]]  # [1, 32, 936]


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/", tags=["General"])
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.VERSION,
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        device=settings.DEVICE,
        backend=settings.INFERENCE_BACKEND,
        models_loaded=inference_engine.is_initialized
    )


@app.post("/predict/multimodal", response_model=FullResponse, tags=["Prediction"])
async def predict_multimodal(
    audio: UploadFile = File(..., description="Audio file (WAV, MP3, etc.)"),
    video: UploadFile = File(..., description="Video file (MP4, AVI, etc.)")
):
    """
    Full multimodal emotion prediction from audio and video files.
    
    - **audio**: Audio file in WAV, MP3, or other common format
    - **video**: Video file in MP4, AVI, or other common format
    
    Returns emotion prediction with confidence, valence, arousal, and intensity.
    """
    total_start = time.perf_counter()
    
    # Read files
    audio_bytes = await audio.read()
    video_bytes = await video.read()
    
    if len(audio_bytes) == 0:
        raise HTTPException(400, "Audio file is empty")
    if len(video_bytes) == 0:
        raise HTTPException(400, "Video file is empty")
    
    # Extract features in parallel
    feature_start = time.perf_counter()
    
    audio_task = audio_processor.extract(audio_bytes)
    video_task = video_processor.extract(video_bytes)
    
    audio_features, video_result = await asyncio.gather(audio_task, video_task)
    
    feature_time = (time.perf_counter() - feature_start) * 1000
    
    if audio_features is None:
        raise HTTPException(400, "Failed to process audio. Ensure valid audio format.")
    if video_result is None:
        raise HTTPException(400, "Failed to process video. Ensure valid video format.")
        
    vit_features, landmark_features = video_result
    
    # Add batch dimension
    audio_features = audio_features[np.newaxis, ...]
    vit_features = vit_features[np.newaxis, ...]
    landmark_features = landmark_features[np.newaxis, ...]
    
    # Run inference
    prediction = await inference_engine.predict(
        audio_features, vit_features, landmark_features
    )
    
    total_time = (time.perf_counter() - total_start) * 1000
    
    return FullResponse(
        success=True,
        prediction=PredictionResponse(
            emotion=prediction.emotion,
            confidence=round(prediction.confidence, 4),
            valence=prediction.valence,
            arousal=prediction.arousal,
            intensity=prediction.intensity,
            probabilities={k: round(v, 4) for k, v in prediction.probabilities.items()}
        ),
        timing=TimingInfo(
            feature_extraction_ms=round(feature_time, 2),
            inference_ms=round(prediction.inference_time_ms, 2),
            total_ms=round(total_time, 2)
        )
    )


@app.post("/predict/audio", tags=["Prediction"])
async def predict_audio_only(
    audio: UploadFile = File(..., description="Audio file (WAV, MP3, etc.)")
):
    """
    Audio-only emotion prediction.
    
    Note: Uses dummy video features, accuracy may be lower than multimodal.
    """
    total_start = time.perf_counter()
    
    audio_bytes = await audio.read()
    
    if len(audio_bytes) == 0:
        raise HTTPException(400, "Audio file is empty")
    
    # Extract audio features
    feature_start = time.perf_counter()
    audio_features = await audio_processor.extract(audio_bytes)
    feature_time = (time.perf_counter() - feature_start) * 1000
    
    if audio_features is None:
        raise HTTPException(400, "Failed to process audio")
    
    # Use dummy video features (zeros)
    audio_features = audio_features[np.newaxis, ...]
    dummy_vit = np.zeros((1, settings.VIDEO_FRAMES, settings.VIT_DIM), dtype=np.float32)
    dummy_landmarks = np.zeros((1, settings.VIDEO_FRAMES, settings.LANDMARK_DIM), dtype=np.float32)
    
    # Run inference
    prediction = await inference_engine.predict(
        audio_features, dummy_vit, dummy_landmarks
    )
    
    total_time = (time.perf_counter() - total_start) * 1000
    
    return {
        "success": True,
        "mode": "audio_only",
        "warning": "Audio-only mode may have reduced accuracy",
        "prediction": {
            "emotion": prediction.emotion,
            "confidence": round(prediction.confidence, 4),
            "probabilities": {k: round(v, 4) for k, v in prediction.probabilities.items()}
        },
        "timing": {
            "feature_extraction_ms": round(feature_time, 2),
            "inference_ms": round(prediction.inference_time_ms, 2),
            "total_ms": round(total_time, 2)
        }
    }


@app.post("/predict/video", tags=["Prediction"])
async def predict_video_only(
    video: UploadFile = File(..., description="Video file (MP4, AVI, etc.)")
):
    """
    Video-only emotion prediction.
    
    Note: Uses dummy audio features, accuracy may be lower than multimodal.
    """
    total_start = time.perf_counter()
    
    video_bytes = await video.read()
    
    if len(video_bytes) == 0:
        raise HTTPException(400, "Video file is empty")
    
    # Extract video features
    feature_start = time.perf_counter()
    video_result = await video_processor.extract(video_bytes)
    feature_time = (time.perf_counter() - feature_start) * 1000
    
    if video_result is None:
        raise HTTPException(400, "Failed to process video")
        
    vit_features, landmark_features = video_result
    
    # Use dummy audio features (zeros)
    dummy_audio = np.zeros((1, settings.AUDIO_MAX_LENGTH, settings.AUDIO_DIM), dtype=np.float32)
    vit_features = vit_features[np.newaxis, ...]
    landmark_features = landmark_features[np.newaxis, ...]
    
    # Run inference
    prediction = await inference_engine.predict(
        dummy_audio, vit_features, landmark_features
    )
    
    total_time = (time.perf_counter() - total_start) * 1000
    
    return {
        "success": True,
        "mode": "video_only",
        "warning": "Video-only mode may have reduced accuracy",
        "prediction": {
            "emotion": prediction.emotion,
            "confidence": round(prediction.confidence, 4),
            "valence": prediction.valence,
            "arousal": prediction.arousal,
            "probabilities": {k: round(v, 4) for k, v in prediction.probabilities.items()}
        },
        "timing": {
            "feature_extraction_ms": round(feature_time, 2),
            "inference_ms": round(prediction.inference_time_ms, 2),
            "total_ms": round(total_time, 2)
        }
    }


@app.post("/predict/embeddings", tags=["Prediction"])
async def predict_from_embeddings(request: EmbeddingsRequest):
    """
    Direct prediction from pre-computed embeddings.
    
    This is the fastest endpoint - for clients that can extract features locally.
    
    Expected shapes:
    - audio: [1, 200, 1024]
    - vit: [1, 32, 768]
    - landmarks: [1, 32, 936]
    """
    try:
        audio_np = np.array(request.audio, dtype=np.float32)
        vit_np = np.array(request.vit, dtype=np.float32)
        landmarks_np = np.array(request.landmarks, dtype=np.float32)
        
        # Validate shapes
        if audio_np.shape != (1, settings.AUDIO_MAX_LENGTH, settings.AUDIO_DIM):
            raise HTTPException(400, f"Invalid audio shape. Expected (1, {settings.AUDIO_MAX_LENGTH}, {settings.AUDIO_DIM})")
        if vit_np.shape != (1, settings.VIDEO_FRAMES, settings.VIT_DIM):
            raise HTTPException(400, f"Invalid vit shape. Expected (1, {settings.VIDEO_FRAMES}, {settings.VIT_DIM})")
        if landmarks_np.shape != (1, settings.VIDEO_FRAMES, settings.LANDMARK_DIM):
            raise HTTPException(400, f"Invalid landmarks shape. Expected (1, {settings.VIDEO_FRAMES}, {settings.LANDMARK_DIM})")
            
    except ValueError as e:
        raise HTTPException(400, f"Invalid embeddings format: {e}")
    
    prediction = await inference_engine.predict(audio_np, vit_np, landmarks_np)
    
    return {
        "success": True,
        "prediction": {
            "emotion": prediction.emotion,
            "confidence": round(prediction.confidence, 4),
            "valence": prediction.valence,
            "arousal": prediction.arousal,
            "intensity": prediction.intensity,
            "probabilities": {k: round(v, 4) for k, v in prediction.probabilities.items()}
        },
        "inference_ms": round(prediction.inference_time_ms, 2)
    }


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc),
            "detail": "An unexpected error occurred"
        }
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )