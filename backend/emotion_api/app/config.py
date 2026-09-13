"""
Configuration settings for the Emotion Recognition API
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import Literal, List
from pathlib import Path
import torch


# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    """Application settings"""
    
    # ===================
    # API Settings
    # ===================
    APP_NAME: str = "Emotion Recognition API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"
    
    # ===================
    # Model Paths
    # ===================
    MODELS_RAW_DIR: Path = PROJECT_ROOT / "models_raw"
    OPTIMIZED_MODELS_DIR: Path = PROJECT_ROOT / "optimized_models"
    
    # Specific model files
    ORIGINAL_MODEL_PATH: Path = PROJECT_ROOT / "models_raw" / "best_model_v13.pt"
    QUANTIZED_MODEL_PATH: Path = PROJECT_ROOT / "optimized_models" / "model_quantized.pt"
    SCRIPTED_MODEL_PATH: Path = PROJECT_ROOT / "optimized_models" / "model_scripted.pt"
    ONNX_MODEL_PATH: Path = PROJECT_ROOT / "optimized_models" / "model.onnx"
    
    # ===================
    # Inference Settings
    # ===================
    INFERENCE_BACKEND: Literal["pytorch", "pytorch_quantized", "torchscript", "onnx"] = "onnx"
    DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"
    MAX_BATCH_SIZE: int = 8
    NUM_WORKERS: int = 4
    
    # ===================
    # Model Architecture Config (must match training)
    # ===================
    AUDIO_DIM: int = 1024
    VIT_DIM: int = 768
    LANDMARK_DIM: int = 936
    AUDIO_HIDDEN: int = 144
    VIT_HIDDEN: int = 96
    LANDMARK_HIDDEN: int = 96
    FUSION_DIM: int = 256
    DROPOUT: float = 0.25
    NUM_EMOTIONS: int = 6
    
    # ===================
    # Audio Processing
    # ===================
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_MAX_LENGTH: int = 200  # frames
    WAV2VEC_MODEL: str = "audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim"
    
    # ===================
    # Video Processing
    # ===================
    VIDEO_FRAMES: int = 32
    VIDEO_SIZE: tuple = (224, 224)
    VIT_MODEL: str = "dima806/facial_emotions_image_detection"
    
    # ===================
    # Labels
    # ===================
    EMOTIONS: List[str] = ["ANG", "DIS", "FEA", "HAP", "NEU", "SAD"]
    EMOTION_NAMES: List[str] = ["angry", "disgust", "fear", "happy", "neutral", "sad"]
    VALENCE_NAMES: List[str] = ["negative", "neutral", "positive"]
    AROUSAL_NAMES: List[str] = ["low", "high"]
    INTENSITY_NAMES: List[str] = ["low", "medium", "high"]
    
    # ===================
    # Rate Limiting
    # ===================
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Export settings instance
settings = get_settings()