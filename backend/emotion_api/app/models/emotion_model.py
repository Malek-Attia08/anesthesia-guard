"""
Multimodal Emotion Recognition Model Architecture
MUST MATCH EXACTLY with the training code architecture.
"""

import torch
import torch.nn as nn
from typing import Dict, Optional, Any, Tuple


def get_model_config() -> Dict[str, Any]:
    """
    Get the model configuration matching training.
    These values MUST match what was used during training.
    """
    return {
        'AUDIO_DIM': 1024,
        'VIT_DIM': 768,
        'LANDMARK_DIM': 936,
        'AUDIO_HIDDEN': 144,      # V13 uses 144
        'VIT_HIDDEN': 96,
        'LANDMARK_HIDDEN': 96,
        'FUSION_DIM': 256,
        'DROPOUT': 0.25,
        'NUM_EMOTIONS': 6,
    }


class DualStreamVideoEncoder(nn.Module):
    """
    Dual-stream video encoder for ViT features and landmarks.
    EXACTLY matches the training architecture.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        
        # ViT stream (texture/appearance)
        self.vit_lstm = nn.LSTM(
            config['VIT_DIM'], 
            config['VIT_HIDDEN'],
            bidirectional=True, 
            batch_first=True
        )
        self.vit_norm = nn.LayerNorm(config['VIT_HIDDEN'] * 2)
        
        # Landmark stream (geometry/shape)
        self.landmark_proj = nn.Sequential(
            nn.Linear(config['LANDMARK_DIM'] * 2, 256),  # Current + Diff
            nn.LayerNorm(256),
            nn.ReLU(),
            nn.Dropout(config['DROPOUT'] * 0.5)
        )
        self.landmark_lstm = nn.LSTM(
            256, 
            config['LANDMARK_HIDDEN'],
            bidirectional=True, 
            batch_first=True
        )
        self.landmark_norm = nn.LayerNorm(config['LANDMARK_HIDDEN'] * 2)
        
        # Cross-stream fusion (simple concatenation, NO attention)
        total_dim = config['VIT_HIDDEN'] * 2 + config['LANDMARK_HIDDEN'] * 2
        self.fusion = nn.Sequential(
            nn.Linear(total_dim, total_dim // 2),
            nn.LayerNorm(total_dim // 2),
            nn.ReLU(),
            nn.Dropout(config['DROPOUT'])
        )
        
        # Output dimensions
        self.output_dim = total_dim // 2
        self.vit_output_dim = config['VIT_HIDDEN'] * 2
        self.landmark_output_dim = config['LANDMARK_HIDDEN'] * 2
    
    def forward(
        self, 
        vit: torch.Tensor, 
        landmarks: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Args:
            vit: [batch, seq_len, 768]
            landmarks: [batch, seq_len, 936]
        Returns:
            video_feat: [batch, output_dim]
            vit_feat: [batch, vit_output_dim]
            landmark_feat: [batch, landmark_output_dim]
        """
        # ViT stream
        vit_out, _ = self.vit_lstm(vit)
        vit_feat = vit_out.max(dim=1)[0]
        vit_feat = self.vit_norm(vit_feat)
        
        # Landmark stream with temporal difference
        landmark_diff = torch.zeros_like(landmarks)
        landmark_diff[:, 1:, :] = landmarks[:, 1:, :] - landmarks[:, :-1, :]
        landmark_combined = torch.cat([landmarks, landmark_diff], dim=-1)
        landmark_proj = self.landmark_proj(landmark_combined)
        
        landmark_out, _ = self.landmark_lstm(landmark_proj)
        landmark_feat = landmark_out.max(dim=1)[0]
        landmark_feat = self.landmark_norm(landmark_feat)
        
        # Simple fusion (NO cross-attention)
        combined = torch.cat([vit_feat, landmark_feat], dim=-1)
        video_feat = self.fusion(combined)
        
        return video_feat, vit_feat, landmark_feat


class HierarchicalEmotionClassifier(nn.Module):
    """
    Hierarchical classifier: Valence -> Arousal -> Emotion
    EXACTLY matches the training architecture.
    """
    
    def __init__(self, input_dim: int, config: Dict[str, Any]):
        super().__init__()
        
        # Valence head (3 classes: negative, neutral, positive)
        self.valence_head = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 3)
        )
        self.valence_embed = nn.Embedding(3, 32)
        
        # Arousal head (2 classes: low, high)
        self.arousal_head = nn.Sequential(
            nn.Linear(input_dim + 32, 64),
            nn.ReLU(),
            nn.Linear(64, 2)
        )
        self.arousal_embed = nn.Embedding(2, 32)
        
        # Emotion head (6 classes)
        self.emotion_head = nn.Sequential(
            nn.Linear(input_dim + 64, 128),
            nn.LayerNorm(128),
            nn.ReLU(),
            nn.Dropout(config['DROPOUT']),
            nn.Linear(128, config['NUM_EMOTIONS'])
        )
    
    def forward(
        self, 
        features: torch.Tensor, 
        true_valence: Optional[torch.Tensor] = None, 
        true_arousal: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Args:
            features: [batch, input_dim]
            true_valence: Optional ground truth for teacher forcing (training only)
            true_arousal: Optional ground truth for teacher forcing (training only)
        Returns:
            emotion_logits: [batch, 6]
            valence_logits: [batch, 3]
            arousal_logits: [batch, 2]
        """
        # Valence prediction
        valence_logits = self.valence_head(features)
        
        # Use ground truth during training if provided, else use predictions
        if true_valence is not None and self.training:
            valence_idx = true_valence
        else:
            valence_idx = valence_logits.argmax(dim=1)
        valence_emb = self.valence_embed(valence_idx)
        
        # Arousal prediction (conditioned on valence)
        arousal_input = torch.cat([features, valence_emb], dim=-1)
        arousal_logits = self.arousal_head(arousal_input)
        
        if true_arousal is not None and self.training:
            arousal_idx = true_arousal
        else:
            arousal_idx = arousal_logits.argmax(dim=1)
        arousal_emb = self.arousal_embed(arousal_idx)
        
        # Emotion prediction (conditioned on valence + arousal)
        emotion_input = torch.cat([features, valence_emb, arousal_emb], dim=-1)
        emotion_logits = self.emotion_head(emotion_input)
        
        return emotion_logits, valence_logits, arousal_logits


class MultimodalEmotionModelV13(nn.Module):
    """
    Complete multimodal emotion recognition model V13.
    This architecture MUST match EXACTLY with the trained model.
    
    Includes all auxiliary classifiers and heads used during training.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        
        if config is None:
            config = get_model_config()
        
        self.config = config
        
        # ============================================================
        # Audio Encoder
        # ============================================================
        self.audio_lstm = nn.LSTM(
            config['AUDIO_DIM'], 
            config['AUDIO_HIDDEN'],
            num_layers=2, 
            bidirectional=True, 
            batch_first=True, 
            dropout=0.1
        )
        self.audio_norm = nn.LayerNorm(config['AUDIO_HIDDEN'] * 2)
        self.audio_drop = nn.Dropout(config['DROPOUT'])
        
        audio_dim = config['AUDIO_HIDDEN'] * 2  # 288
        
        # ============================================================
        # Video Encoder (Dual Stream)
        # ============================================================
        self.video_encoder = DualStreamVideoEncoder(config)
        video_dim = self.video_encoder.output_dim  # 192
        vit_dim = self.video_encoder.vit_output_dim  # 192
        lm_dim = self.video_encoder.landmark_output_dim  # 192
        
        # ============================================================
        # Multimodal Fusion
        # ============================================================
        self.fusion = nn.Sequential(
            nn.Linear(audio_dim + video_dim, config['FUSION_DIM']),
            nn.LayerNorm(config['FUSION_DIM']),
            nn.ReLU(),
            nn.Dropout(config['DROPOUT']),
            nn.Linear(config['FUSION_DIM'], config['FUSION_DIM']),
            nn.LayerNorm(config['FUSION_DIM']),
            nn.ReLU(),
            nn.Dropout(config['DROPOUT'] * 0.5)
        )
        
        # ============================================================
        # Hierarchical Classifier
        # ============================================================
        self.classifier = HierarchicalEmotionClassifier(config['FUSION_DIM'], config)
        
        # ============================================================
        # Intensity Head
        # ============================================================
        self.int_ord_head = nn.Sequential(
            nn.Linear(config['FUSION_DIM'], 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )
        
        # ============================================================
        # FEA vs SAD Binary Classifier
        # ============================================================
        self.fea_sad_head = nn.Sequential(
            nn.Linear(config['FUSION_DIM'], 64),
            nn.ReLU(),
            nn.Linear(64, 2)
        )
        
        # ============================================================
        # Auxiliary Classifiers (DEEPER - 3 layers as in V13)
        # ============================================================
        
        # Audio auxiliary classifier
        self.audio_classifier = nn.Sequential(
            nn.Linear(audio_dim, 224),
            nn.LayerNorm(224),
            nn.ReLU(),
            nn.Dropout(config['DROPOUT']),
            nn.Linear(224, 128),
            nn.LayerNorm(128),
            nn.ReLU(),
            nn.Dropout(config['DROPOUT'] * 0.5),
            nn.Linear(128, config['NUM_EMOTIONS'])
        )
        
        # ViT auxiliary classifier
        self.vit_classifier = nn.Sequential(
            nn.Linear(vit_dim, 128),
            nn.LayerNorm(128),
            nn.ReLU(),
            nn.Dropout(config['DROPOUT']),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, config['NUM_EMOTIONS'])
        )
        
        # Landmark auxiliary classifier
        self.landmark_classifier = nn.Sequential(
            nn.Linear(lm_dim, 128),
            nn.LayerNorm(128),
            nn.ReLU(),
            nn.Dropout(config['DROPOUT']),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, config['NUM_EMOTIONS'])
        )
    
    def encode_audio(self, audio: torch.Tensor) -> torch.Tensor:
        """Encode audio features"""
        out, _ = self.audio_lstm(audio)
        pooled = out.max(dim=1)[0]
        return self.audio_drop(self.audio_norm(pooled))
    
    def forward(
        self, 
        audio: torch.Tensor, 
        vit: torch.Tensor, 
        landmarks: torch.Tensor,
        audio_only: bool = False,
        video_only: bool = False,
        true_valence: Optional[torch.Tensor] = None,
        true_arousal: Optional[torch.Tensor] = None
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass matching the training code exactly.
        
        Args:
            audio: [batch, 200, 1024] - Audio embeddings from Wav2Vec2
            vit: [batch, 32, 768] - ViT embeddings
            landmarks: [batch, 32, 936] - Facial landmark features
            audio_only: If True, return audio-only prediction
            video_only: If True, return video-only prediction
            true_valence: Ground truth valence for teacher forcing (training)
            true_arousal: Ground truth arousal for teacher forcing (training)
            
        Returns:
            Dictionary with all predictions and features
        """
        # ============================================================
        # Encode Audio
        # ============================================================
        audio_feat = self.encode_audio(audio)
        audio_emotion = self.audio_classifier(audio_feat)
        
        if audio_only:
            return {
                'emotion': audio_emotion,
                'audio_feat': audio_feat
            }
        
        # ============================================================
        # Encode Video (Dual Stream)
        # ============================================================
        video_feat, vit_feat, landmark_feat = self.video_encoder(vit, landmarks)
        
        vit_emotion = self.vit_classifier(vit_feat)
        landmark_emotion = self.landmark_classifier(landmark_feat)
        
        if video_only:
            # EXACTLY V9: Average of vit and landmark predictions
            video_emotion = (vit_emotion + landmark_emotion) / 2
            return {
                'emotion': video_emotion,
                'video_feat': video_feat,
                'vit_emotion': vit_emotion,
                'landmark_emotion': landmark_emotion
            }
        
        # ============================================================
        # Multimodal Fusion
        # ============================================================
        fused = torch.cat([audio_feat, video_feat], dim=-1)
        fused = self.fusion(fused)
        
        # ============================================================
        # Hierarchical Classification
        # ============================================================
        emotion_logits, valence_logits, arousal_logits = self.classifier(
            fused, true_valence, true_arousal
        )
        
        # ============================================================
        # Intensity Prediction
        # ============================================================
        int_ord = self.int_ord_head(fused).squeeze(-1)
        
        # ============================================================
        # FEA vs SAD Binary Classification
        # ============================================================
        fea_sad_logits = self.fea_sad_head(fused)
        
        return {
            'emotion': emotion_logits,
            'valence': valence_logits,
            'arousal': arousal_logits,
            'int_ord': int_ord,
            'fea_sad': fea_sad_logits,
            'audio_emotion': audio_emotion,
            'vit_emotion': vit_emotion,
            'landmark_emotion': landmark_emotion,
            'audio_feat': audio_feat,
            'video_feat': video_feat
        }


# ============================================================
# WRAPPER FOR ONNX EXPORT
# ============================================================

class MultimodalEmotionModelForONNX(nn.Module):
    """
    Simplified wrapper for ONNX export.
    Returns tensors directly instead of dictionary.
    Only returns the main predictions needed for inference.
    """
    
    def __init__(self, base_model: MultimodalEmotionModelV13):
        super().__init__()
        self.model = base_model
        self.model.eval()
    
    def forward(
        self, 
        audio: torch.Tensor, 
        vit: torch.Tensor, 
        landmarks: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass for ONNX.
        
        Returns:
            Tuple of (emotion, valence, arousal, intensity) tensors
        """
        out = self.model(audio, vit, landmarks)
        return (
            out['emotion'],      # [batch, 6]
            out['valence'],      # [batch, 3]
            out['arousal'],      # [batch, 2]
            out['int_ord']       # [batch]
        )


# ============================================================
# WRAPPER FOR INFERENCE (SIMPLIFIED OUTPUT)
# ============================================================

class EmotionModelInference(nn.Module):
    """
    Inference wrapper that provides a cleaner interface.
    Loads from checkpoint and provides simple predict method.
    """
    
    def __init__(self, checkpoint_path: str, device: str = 'cpu'):
        super().__init__()
        
        self.device = device
        self.model = self._load_model(checkpoint_path)
        self.model.to(device)
        self.model.eval()
        
        # Emotion labels
        self.emotions = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad']
        self.valence_labels = ['negative', 'neutral', 'positive']
        self.arousal_labels = ['low', 'high']
        self.intensity_labels = ['low', 'medium', 'high']
    
    def _load_model(self, checkpoint_path: str) -> MultimodalEmotionModelV13:
        """Load model from checkpoint"""
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        
        # Get config
        if 'config' in checkpoint:
            config = checkpoint['config']
            # Handle string config values
            if isinstance(config.get('AUDIO_DIM'), str):
                config = get_model_config()
        else:
            config = get_model_config()
        
        # Create model
        model = MultimodalEmotionModelV13(config)
        
        # Load weights
        if 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
        else:
            model.load_state_dict(checkpoint)
        
        # Disable dropout for inference
        for module in model.modules():
            if isinstance(module, nn.Dropout):
                module.p = 0
        
        # Freeze parameters
        for param in model.parameters():
            param.requires_grad = False
        
        return model
    
    @torch.no_grad()
    def predict(
        self,
        audio: torch.Tensor,
        vit: torch.Tensor,
        landmarks: torch.Tensor
    ) -> Dict[str, Any]:
        """
        Run inference and return formatted predictions.
        
        Args:
            audio: [batch, 200, 1024]
            vit: [batch, 32, 768]
            landmarks: [batch, 32, 936]
            
        Returns:
            Dictionary with predictions
        """
        # Move to device
        audio = audio.to(self.device)
        vit = vit.to(self.device)
        landmarks = landmarks.to(self.device)
        
        # Run model
        outputs = self.model(audio, vit, landmarks)
        
        # Process outputs
        emotion_probs = torch.softmax(outputs['emotion'], dim=-1)
        emotion_idx = emotion_probs.argmax(dim=-1)
        
        valence_idx = outputs['valence'].argmax(dim=-1)
        arousal_idx = outputs['arousal'].argmax(dim=-1)
        intensity_val = outputs['int_ord'].clamp(0, 2).round().long()
        
        # Format results
        batch_size = audio.shape[0]
        results = []
        
        for i in range(batch_size):
            results.append({
                'emotion': self.emotions[emotion_idx[i].item()],
                'confidence': emotion_probs[i, emotion_idx[i]].item(),
                'valence': self.valence_labels[valence_idx[i].item()],
                'arousal': self.arousal_labels[arousal_idx[i].item()],
                'intensity': self.intensity_labels[intensity_val[i].item()],
                'probabilities': {
                    self.emotions[j]: emotion_probs[i, j].item()
                    for j in range(len(self.emotions))
                }
            })
        
        return results[0] if batch_size == 1 else results
    
    def forward(
        self,
        audio: torch.Tensor,
        vit: torch.Tensor,
        landmarks: torch.Tensor
    ) -> Dict[str, torch.Tensor]:
        """Forward pass (for compatibility)"""
        return self.model(audio, vit, landmarks)