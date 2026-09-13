"""
Model architecture definitions
"""

from .emotion_model import (
    MultimodalEmotionModelV13,
    DualStreamVideoEncoder,
    HierarchicalEmotionClassifier,
    get_model_config
)

__all__ = [
    "MultimodalEmotionModelV13",
    "DualStreamVideoEncoder", 
    "HierarchicalEmotionClassifier",
    "get_model_config"
]