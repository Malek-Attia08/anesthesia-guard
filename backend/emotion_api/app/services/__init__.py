"""
Service layer for audio, video processing and inference
"""

from .audio import AudioProcessor, audio_processor
from .video import VideoProcessor, video_processor
from .inference import InferenceEngine, inference_engine, EmotionPrediction

__all__ = [
    "AudioProcessor",
    "audio_processor",
    "VideoProcessor", 
    "video_processor",
    "InferenceEngine",
    "inference_engine",
    "EmotionPrediction"
]