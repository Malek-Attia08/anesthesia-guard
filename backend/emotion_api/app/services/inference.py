"""
Inference engine with support for multiple backends:
- PyTorch (original)
- PyTorch Quantized
- TorchScript
- ONNX (recommended for production)
"""

import numpy as np
import torch
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from pathlib import Path

from app.config import settings
from app.models.emotion_model import MultimodalEmotionModelV13, get_model_config


@dataclass
class EmotionPrediction:
    """Prediction result container"""
    emotion: str
    confidence: float
    valence: str
    arousal: str
    intensity: str
    probabilities: Dict[str, float]
    inference_time_ms: float


class InferenceEngine:
    """
    Optimized inference engine supporting multiple backends.
    """
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=settings.NUM_WORKERS)
        self._model = None
        self._onnx_session = None
        self._backend = settings.INFERENCE_BACKEND
        self._device = settings.DEVICE
        self._initialized = False
        
        # Label mappings
        self._emotion_labels = settings.EMOTION_NAMES
        self._valence_labels = settings.VALENCE_NAMES
        self._arousal_labels = settings.AROUSAL_NAMES
        self._intensity_labels = settings.INTENSITY_NAMES
        
    async def initialize(self) -> None:
        """Async initialization"""
        if self._initialized:
            return
            
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._load_model)
        self._initialized = True
        
    def _load_model(self) -> None:
        """Load model based on configured backend"""
        print(f"Loading model with backend: {self._backend}")
        
        if self._backend == "onnx":
            self._load_onnx()
        elif self._backend == "torchscript":
            self._load_torchscript()
        elif self._backend == "pytorch_quantized":
            self._load_quantized()
        else:  # pytorch
            self._load_pytorch()
            
    def _load_pytorch(self) -> None:
        """Load original PyTorch model"""
        checkpoint_path = settings.ORIGINAL_MODEL_PATH
        
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Model not found: {checkpoint_path}")
        
        # PyTorch 2.6+ requires weights_only=False for checkpoints with config dict
        try:
            checkpoint = torch.load(
                checkpoint_path, 
                map_location=self._device,
                weights_only=False
            )
        except TypeError:
            # Older PyTorch versions don't have weights_only parameter
            checkpoint = torch.load(checkpoint_path, map_location=self._device)
        
        # Get config from checkpoint or use default
        if 'config' in checkpoint:
            config = checkpoint['config']
            if isinstance(config.get('AUDIO_DIM'), str):
                config = get_model_config()
            # Ensure all required keys exist
            default_config = get_model_config()
            for key in default_config:
                if key not in config:
                    config[key] = default_config[key]
        else:
            config = get_model_config()
        
        self._model = MultimodalEmotionModelV13(config)
        
        # Load weights
        if 'model_state_dict' in checkpoint:
            self._model.load_state_dict(checkpoint['model_state_dict'])
        else:
            self._model.load_state_dict(checkpoint)
        
        self._model.eval()
        
        # Disable dropout
        for module in self._model.modules():
            if isinstance(module, torch.nn.Dropout):
                module.p = 0
                
        # Freeze parameters
        for param in self._model.parameters():
            param.requires_grad = False
            
        if self._device == 'cuda' and torch.cuda.is_available():
            self._model = self._model.cuda()
            
        print(f"✅ PyTorch model loaded on {self._device}")
        
    def _load_quantized(self) -> None:
        """Load quantized PyTorch model"""
        checkpoint_path = settings.QUANTIZED_MODEL_PATH
        
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Quantized model not found: {checkpoint_path}")
        
        try:
            checkpoint = torch.load(
                checkpoint_path, 
                map_location='cpu',
                weights_only=False
            )
        except TypeError:
            checkpoint = torch.load(checkpoint_path, map_location='cpu')
        
        self._model = checkpoint['model']
        self._model.eval()
        
        print("✅ Quantized model loaded (CPU only)")
        
    def _load_torchscript(self) -> None:
        """Load TorchScript model"""
        script_path = settings.SCRIPTED_MODEL_PATH
        
        if not script_path.exists():
            raise FileNotFoundError(f"TorchScript model not found: {script_path}")
        
        self._model = torch.jit.load(str(script_path), map_location=self._device)
        self._model.eval()
        
        if self._device == 'cuda' and torch.cuda.is_available():
            self._model = self._model.cuda()
            
        print(f"✅ TorchScript model loaded on {self._device}")
        
    def _load_onnx(self) -> None:
        """Load ONNX model with optimizations"""
        try:
            import onnxruntime as ort
        except ImportError:
            raise ImportError("onnxruntime not installed. Run: pip install onnxruntime")
        
        onnx_path = settings.ONNX_MODEL_PATH
        
        if not onnx_path.exists():
            raise FileNotFoundError(f"ONNX model not found: {onnx_path}")
            
        # Session options for optimization
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.intra_op_num_threads = settings.NUM_WORKERS
        sess_options.inter_op_num_threads = settings.NUM_WORKERS
        sess_options.enable_mem_pattern = True
        sess_options.enable_cpu_mem_arena = True
        
        # Select execution providers
        providers = ['CPUExecutionProvider']
        if self._device == 'cuda' and torch.cuda.is_available():
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            
        self._onnx_session = ort.InferenceSession(
            str(onnx_path),
            sess_options=sess_options,
            providers=providers
        )
        
        print(f"✅ ONNX model loaded with providers: {self._onnx_session.get_providers()}")
        
    def _run_pytorch(
        self, 
        audio: np.ndarray, 
        vit: np.ndarray, 
        landmarks: np.ndarray
    ) -> Dict[str, np.ndarray]:
        """Run PyTorch/TorchScript inference"""
        with torch.no_grad():
            audio_t = torch.from_numpy(audio).float()
            vit_t = torch.from_numpy(vit).float()
            landmarks_t = torch.from_numpy(landmarks).float()
            
            if self._device == 'cuda' and torch.cuda.is_available():
                audio_t = audio_t.cuda()
                vit_t = vit_t.cuda()
                landmarks_t = landmarks_t.cuda()
            
            outputs = self._model(audio_t, vit_t, landmarks_t)
            
            # Handle both dict output (PyTorch) and tuple output (TorchScript)
            if isinstance(outputs, dict):
                return {
                    'emotion': outputs['emotion'].cpu().numpy(),
                    'valence': outputs['valence'].cpu().numpy(),
                    'arousal': outputs['arousal'].cpu().numpy(),
                    'intensity': outputs['int_ord'].cpu().numpy()
                }
            else:
                # TorchScript returns tuple: (emotion, valence, arousal, intensity)
                return {
                    'emotion': outputs[0].cpu().numpy(),
                    'valence': outputs[1].cpu().numpy(),
                    'arousal': outputs[2].cpu().numpy(),
                    'intensity': outputs[3].cpu().numpy()
                }
                
    def _run_onnx(
        self, 
        audio: np.ndarray, 
        vit: np.ndarray, 
        landmarks: np.ndarray
    ) -> Dict[str, np.ndarray]:
        """Run ONNX inference"""
        outputs = self._onnx_session.run(
            None,
            {
                'audio': audio.astype(np.float32),
                'vit': vit.astype(np.float32),
                'landmarks': landmarks.astype(np.float32)
            }
        )
        return {
            'emotion': outputs[0],
            'valence': outputs[1],
            'arousal': outputs[2],
            'intensity': outputs[3]
        }
        
    def _predict_sync(
        self,
        audio: np.ndarray,
        vit: np.ndarray,
        landmarks: np.ndarray
    ) -> EmotionPrediction:
        """Synchronous prediction"""
        start_time = time.perf_counter()
        
        # Run inference based on backend
        if self._backend == "onnx" and self._onnx_session is not None:
            outputs = self._run_onnx(audio, vit, landmarks)
        else:
            outputs = self._run_pytorch(audio, vit, landmarks)
            
        inference_time = (time.perf_counter() - start_time) * 1000
        
        # Process emotion output
        emotion_logits = outputs['emotion'][0]
        emotion_probs = self._softmax(emotion_logits)
        emotion_idx = int(np.argmax(emotion_probs))
        
        # Process valence output
        valence_idx = int(np.argmax(outputs['valence'][0]))
        
        # Process arousal output
        arousal_idx = int(np.argmax(outputs['arousal'][0]))
        
        # Process intensity output
        intensity_val = outputs['intensity']
        if isinstance(intensity_val, np.ndarray):
            if intensity_val.ndim > 0:
                intensity_val = float(intensity_val.flat[0])
            else:
                intensity_val = float(intensity_val)
        intensity_idx = int(np.clip(np.round(intensity_val), 0, 2))
        
        return EmotionPrediction(
            emotion=self._emotion_labels[emotion_idx],
            confidence=float(emotion_probs[emotion_idx]),
            valence=self._valence_labels[valence_idx],
            arousal=self._arousal_labels[arousal_idx],
            intensity=self._intensity_labels[intensity_idx],
            probabilities={
                label: float(prob) 
                for label, prob in zip(self._emotion_labels, emotion_probs)
            },
            inference_time_ms=inference_time
        )
        
    async def predict(
        self,
        audio: np.ndarray,
        vit: np.ndarray,
        landmarks: np.ndarray
    ) -> EmotionPrediction:
        """
        Async prediction.
        
        Args:
            audio: [1, 200, 1024] audio embeddings
            vit: [1, 32, 768] ViT embeddings
            landmarks: [1, 32, 936] landmark embeddings
            
        Returns:
            EmotionPrediction object
        """
        if not self._initialized:
            await self.initialize()
            
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._predict_sync,
            audio, vit, landmarks
        )
        
    async def predict_batch(
        self,
        audio_batch: np.ndarray,
        vit_batch: np.ndarray,
        landmarks_batch: np.ndarray
    ) -> List[EmotionPrediction]:
        """Batch prediction"""
        if not self._initialized:
            await self.initialize()
            
        predictions = []
        batch_size = audio_batch.shape[0]
        
        for i in range(batch_size):
            pred = await self.predict(
                audio_batch[i:i+1],
                vit_batch[i:i+1],
                landmarks_batch[i:i+1]
            )
            predictions.append(pred)
            
        return predictions
    
    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        """Compute softmax"""
        exp_x = np.exp(x - np.max(x))
        return exp_x / exp_x.sum()
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self.executor.shutdown(wait=False)
        self._model = None
        self._onnx_session = None
        self._initialized = False
        
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    @property
    def backend(self) -> str:
        return self._backend


# Singleton instance
inference_engine = InferenceEngine()