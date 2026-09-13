"""
Audio processing service for feature extraction using Wav2Vec2
"""

import numpy as np
import torch
import librosa
import io
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import soundfile as sf

from transformers import Wav2Vec2Processor, Wav2Vec2Model

from app.config import settings


class AudioProcessor:
    """
    Handles audio preprocessing and feature extraction.
    Uses Wav2Vec2 model for extracting audio embeddings.
    """
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._processor: Optional[Wav2Vec2Processor] = None
        self._model: Optional[Wav2Vec2Model] = None
        self._initialized = False
        self._device = settings.DEVICE
        
    async def initialize(self) -> None:
        """Async initialization of the audio model"""
        if self._initialized:
            return
            
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._load_model)
        self._initialized = True
        
    def _load_model(self) -> None:
        """Load Wav2Vec2 model with optimizations"""
        print(f"Loading Wav2Vec2 model: {settings.WAV2VEC_MODEL}")
        
        self._processor = Wav2Vec2Processor.from_pretrained(
            settings.WAV2VEC_MODEL
        )
        self._model = Wav2Vec2Model.from_pretrained(
            settings.WAV2VEC_MODEL
        )
        
        # Set to evaluation mode
        self._model.eval()
        
        # Freeze parameters
        for param in self._model.parameters():
            param.requires_grad = False
            
        # Move to appropriate device
        if self._device == 'cuda' and torch.cuda.is_available():
            self._model = self._model.cuda()
            # Use half precision on GPU for speed
            self._model = self._model.half()
            
        print(f"✅ Wav2Vec2 loaded on {self._device}")
        
    def _load_audio_from_bytes(self, audio_bytes: bytes) -> Optional[tuple]:
        """Load audio from bytes buffer"""
        try:
            # Try reading with soundfile first
            audio_buffer = io.BytesIO(audio_bytes)
            audio_data, sample_rate = sf.read(audio_buffer)
            return audio_data, sample_rate
        except Exception:
            pass
            
        try:
            # Fallback: save to temp file and use librosa
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name
                
            audio_data, sample_rate = librosa.load(temp_path, sr=None)
            os.unlink(temp_path)
            return audio_data, sample_rate
        except Exception as e:
            print(f"Failed to load audio: {e}")
            return None
        
    def _extract_features_sync(self, audio_bytes: bytes) -> Optional[np.ndarray]:
        """
        Synchronous feature extraction.
        
        Returns:
            numpy array of shape [200, 1024] or None if failed
        """
        try:
            # Load audio
            result = self._load_audio_from_bytes(audio_bytes)
            if result is None:
                return None
                
            audio_data, sample_rate = result
            
            # Convert to mono if stereo
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)
            
            # Resample to 16kHz if needed
            if sample_rate != settings.AUDIO_SAMPLE_RATE:
                audio_data = librosa.resample(
                    audio_data, 
                    orig_sr=sample_rate, 
                    target_sr=settings.AUDIO_SAMPLE_RATE
                )
            
            # Check minimum length (0.1 seconds)
            if len(audio_data) < 1600:
                print("Audio too short")
                return None
                
            # Normalize audio
            if np.abs(audio_data).max() > 0:
                audio_data = audio_data / np.abs(audio_data).max()
                
            # Process through Wav2Vec2
            inputs = self._processor(
                audio_data, 
                sampling_rate=settings.AUDIO_SAMPLE_RATE,
                return_tensors="pt",
                padding=True
            )
            
            input_values = inputs.input_values
            
            if self._device == 'cuda' and torch.cuda.is_available():
                input_values = input_values.cuda().half()
                
            with torch.no_grad():
                outputs = self._model(input_values)
                hidden_states = outputs.last_hidden_state.squeeze(0)
                
                # Convert back to float32
                if hidden_states.dtype == torch.float16:
                    hidden_states = hidden_states.float()
                
            # Pad or truncate to fixed length
            target_len = settings.AUDIO_MAX_LENGTH
            current_len = hidden_states.shape[0]
            
            if current_len > target_len:
                hidden_states = hidden_states[:target_len]
            elif current_len < target_len:
                pad_size = target_len - current_len
                padding = torch.zeros(pad_size, 1024, device=hidden_states.device)
                hidden_states = torch.cat([hidden_states, padding], dim=0)
                
            return hidden_states.cpu().numpy().astype(np.float32)
            
        except Exception as e:
            print(f"Audio extraction error: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    async def extract(self, audio_bytes: bytes) -> Optional[np.ndarray]:
        """
        Async feature extraction.
        
        Args:
            audio_bytes: Raw audio file bytes
            
        Returns:
            numpy array of shape [200, 1024] or None if failed
        """
        if not self._initialized:
            await self.initialize()
            
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._extract_features_sync,
            audio_bytes
        )
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self.executor.shutdown(wait=False)
        self._model = None
        self._processor = None
        self._initialized = False


# Singleton instance
audio_processor = AudioProcessor()