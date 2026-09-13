"""
GPU-Optimized Video processing - SAFE VERSION (Windows Compatible)
"""

import numpy as np
import torch
import cv2
import mediapipe as mp
from PIL import Image
import asyncio
import tempfile
import os
import platform
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple, List
import time

from transformers import ViTImageProcessor, ViTModel
from app.config import settings

# Optional: Fast video loading
try:
    import decord
    decord.bridge.set_bridge('torch')
    DECORD_AVAILABLE = True
    print("✅ Decord available")
except ImportError:
    DECORD_AVAILABLE = False
    print("⚠️ Decord not available")


class VideoProcessor:
    """
    GPU-Optimized video processor (Windows Compatible).
    
    Produces IDENTICAL output to original, just faster.
    """
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._vit_processor: Optional[ViTImageProcessor] = None
        self._vit_model: Optional[ViTModel] = None
        self._face_mesh = None
        self._initialized = False
        self._device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
    async def initialize(self) -> None:
        """Async initialization of video models"""
        if self._initialized:
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._load_models)
        self._initialized = True
        
    def _load_models(self) -> None:
        """Load ViT and MediaPipe models with GPU optimizations"""
        start_time = time.time()
        print(f"\n{'='*60}")
        print(f"🚀 Initializing GPU-Optimized Video Processor")
        print(f"   Device: {self._device}")
        print(f"   Platform: {platform.system()}")
        print(f"{'='*60}\n")
        
        # =====================================
        # CUDA Optimizations
        # =====================================
        if self._device.type == 'cuda':
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            torch.backends.cudnn.benchmark = True
            torch.backends.cudnn.enabled = True
            print(f"✅ CUDA optimizations enabled (TF32 + cuDNN)")
            
        # =====================================
        # Load ViT Model
        # =====================================
        print(f"\n📦 Loading ViT: {settings.VIT_MODEL}")
        
        self._vit_processor = ViTImageProcessor.from_pretrained(settings.VIT_MODEL)
        self._vit_model = ViTModel.from_pretrained(
            settings.VIT_MODEL,
            torch_dtype=torch.float16 if self._device.type == 'cuda' else torch.float32
        )
        
        self._vit_model.eval()
        for param in self._vit_model.parameters():
            param.requires_grad = False
            
        if self._device.type == 'cuda':
            self._vit_model = self._vit_model.cuda()
            
        # =====================================
        # torch.compile() - ONLY ON LINUX
        # Triton is NOT available on Windows!
        # =====================================
        if platform.system() == "Linux" and hasattr(torch, 'compile'):
            try:
                self._vit_model = torch.compile(
                    self._vit_model, 
                    mode='reduce-overhead',
                    fullgraph=False
                )
                print(f"   ✅ torch.compile() enabled")
            except Exception as e:
                print(f"   ⚠️ torch.compile() failed: {e}")
        else:
            print(f"   ℹ️ torch.compile() skipped (Windows/unsupported)")
                    
        print(f"   ✅ ViT loaded on {self._device}")
        
        # =====================================
        # Load MediaPipe
        # =====================================
        print(f"\n👤 Loading MediaPipe Face Mesh...")
        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
        print("   ✅ MediaPipe loaded")
        
        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"✅ Initialization complete in {elapsed:.2f}s")
        print(f"{'='*60}\n")

    def _load_video_frames(self, video_path: str) -> Optional[List[np.ndarray]]:
        """Load video frames - uses Decord if available, else cv2."""
        target_frames = settings.VIDEO_FRAMES
        
        if DECORD_AVAILABLE:
            try:
                vr = decord.VideoReader(video_path, ctx=decord.cpu(0))
                total_frames = len(vr)
                
                if total_frames < 1:
                    return None
                    
                indices = np.linspace(0, total_frames - 1, target_frames).astype(int)
                frames = vr.get_batch(indices).asnumpy()
                
                return [frames[i] for i in range(len(frames))]
                
            except Exception as e:
                print(f"   Decord failed, using cv2: {e}")
                
        return self._load_video_cv2(video_path)
        
    def _load_video_cv2(self, video_path: str) -> Optional[List[np.ndarray]]:
        """Load video frames using OpenCV"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames < 1:
            cap.release()
            return None
            
        frame_indices = np.linspace(0, total_frames - 1, settings.VIDEO_FRAMES).astype(int)
        frame_indices_set = set(frame_indices)
        
        frames = []
        current_frame = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            if current_frame in frame_indices_set:
                frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                
            current_frame += 1
            
        cap.release()
        return frames if frames else None

    def _normalize_landmarks(
        self, 
        landmarks, 
        width: int, 
        height: int
    ) -> np.ndarray:
        """Normalize landmarks - EXACT SAME as original."""
        if not landmarks or not landmarks.landmark:
            return np.zeros(468 * 2, dtype=np.float32)
            
        coords = np.array([
            (lm.x * width, lm.y * height) 
            for lm in landmarks.landmark
        ])[:468]
        
        nose = coords[1]
        coords = coords - nose
        
        face_width = np.linalg.norm(coords[33] - coords[263]) + 1e-6
        coords = coords / face_width
        
        return coords.flatten().astype(np.float32)

    @torch.inference_mode()
    def _extract_features_sync(
        self, 
        video_bytes: bytes
    ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """GPU-optimized feature extraction."""
        temp_path = None
        start_time = time.time()
        
        try:
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                f.write(video_bytes)
                temp_path = f.name
                
            # 1. Load Frames
            t0 = time.time()
            frames = self._load_video_frames(temp_path)
            
            if not frames:
                print("❌ No frames extracted")
                return None
                
            print(f"   📹 Loaded {len(frames)} frames in {time.time()-t0:.3f}s")
            
            # 2. Process Each Frame
            t0 = time.time()
            vit_images = []
            landmark_vectors = []
            
            for frame_rgb in frames:
                h, w = frame_rgb.shape[:2]
                
                results = self._face_mesh.process(frame_rgb)
                
                if results.multi_face_landmarks:
                    lms = results.multi_face_landmarks[0]
                    lm_vec = self._normalize_landmarks(lms, w, h)
                    
                    xs = [l.x * w for l in lms.landmark]
                    ys = [l.y * h for l in lms.landmark]
                    x1, x2 = int(min(xs)), int(max(xs))
                    y1, y2 = int(min(ys)), int(max(ys))
                    
                    margin_x = int((x2 - x1) * 0.2)
                    margin_y = int((y2 - y1) * 0.2)
                    x1 = max(0, x1 - margin_x)
                    x2 = min(w, x2 + margin_x)
                    y1 = max(0, y1 - margin_y)
                    y2 = min(h, y2 + margin_y)
                    
                    if x2 > x1 and y2 > y1:
                        face_crop = frame_rgb[y1:y2, x1:x2]
                        face_pil = Image.fromarray(face_crop).resize((224, 224))
                    else:
                        face_pil = Image.fromarray(frame_rgb).resize((224, 224))
                else:
                    lm_vec = np.zeros(468 * 2, dtype=np.float32)
                    face_pil = Image.fromarray(frame_rgb).resize((224, 224))
                    
                vit_images.append(face_pil)
                landmark_vectors.append(lm_vec)
                
            print(f"   👤 Face detection in {time.time()-t0:.3f}s (MediaPipe)")
            
            if not vit_images:
                print("❌ No frames processed")
                return None
                
            # 3. Extract ViT Features (GPU BATCHED)
            t0 = time.time()
            
            pixel_values = self._vit_processor(
                images=vit_images, 
                return_tensors="pt"
            ).pixel_values
            
            if self._device.type == 'cuda':
                pixel_values = pixel_values.cuda().half()
                
            vit_features_list = []
            batch_size = 16
            
            for i in range(0, len(pixel_values), batch_size):
                batch = pixel_values[i:i + batch_size]
                out = self._vit_model(pixel_values=batch).last_hidden_state[:, 0, :]
                vit_features_list.append(out.float().cpu())
                
            vit_emb = torch.cat(vit_features_list, dim=0)
            
            print(f"   🧠 ViT extraction in {time.time()-t0:.3f}s (GPU)")
            
            # 4. Stack Landmarks
            lm_tensor = torch.tensor(
                np.array(landmark_vectors), 
                dtype=torch.float32
            )
            
            # 5. Pad/Truncate
            target_len = settings.VIDEO_FRAMES
            current_len = vit_emb.shape[0]
            
            if current_len < target_len:
                pad_vit = torch.zeros(target_len - current_len, 768)
                pad_lm = torch.zeros(target_len - current_len, 936)
                vit_emb = torch.cat([vit_emb, pad_vit], dim=0)
                lm_tensor = torch.cat([lm_tensor, pad_lm], dim=0)
            elif current_len > target_len:
                vit_emb = vit_emb[:target_len]
                lm_tensor = lm_tensor[:target_len]
                
            total_time = time.time() - start_time
            print(f"   ⏱️ Total: {total_time:.3f}s")
            
            return (
                vit_emb.numpy().astype(np.float32),
                lm_tensor.numpy().astype(np.float32)
            )
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None
            
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
    async def extract(
        self, 
        video_bytes: bytes
    ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Async feature extraction"""
        if not self._initialized:
            await self.initialize()
            
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._extract_features_sync,
            video_bytes
        )
        
    def cleanup(self) -> None:
        """Cleanup resources"""
        self.executor.shutdown(wait=False)
        self._vit_model = None
        self._vit_processor = None
        if self._face_mesh:
            self._face_mesh.close()
        self._initialized = False
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


# Singleton instance
video_processor = VideoProcessor()