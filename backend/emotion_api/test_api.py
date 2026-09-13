"""
Test script for Emotion Recognition API
"""

import requests
import json
import os
import tempfile
import numpy as np
from pathlib import Path

API_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint"""
    print("\n" + "="*50)
    print("Testing /health endpoint...")
    print("="*50)
    
    response = requests.get(f"{API_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print("✅ Health check passed!")


def test_root():
    """Test root endpoint"""
    print("\n" + "="*50)
    print("Testing / endpoint...")
    print("="*50)
    
    response = requests.get(f"{API_URL}/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200
    print("✅ Root endpoint passed!")


def create_dummy_audio_file():
    """Create a dummy WAV file for testing"""
    import wave
    import struct
    
    # Create a simple sine wave
    sample_rate = 16000
    duration = 2  # seconds
    frequency = 440  # Hz
    
    n_samples = int(sample_rate * duration)
    
    # Generate sine wave
    samples = []
    for i in range(n_samples):
        sample = int(32767 * np.sin(2 * np.pi * frequency * i / sample_rate))
        samples.append(struct.pack('<h', sample))
    
    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    
    with wave.open(temp_file.name, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b''.join(samples))
    
    return temp_file.name


def create_dummy_video_file():
    """Create a dummy MP4 file for testing"""
    try:
        import cv2
    except ImportError:
        print("   ⚠️ OpenCV not available for video creation")
        return None
    
    temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    
    # Create a simple video with colored frames
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_file.name, fourcc, 30, (224, 224))
    
    # Write 60 frames (2 seconds)
    for i in range(60):
        # Create a frame with a simple pattern
        frame = np.zeros((224, 224, 3), dtype=np.uint8)
        # Add a circle that moves (simulating a face)
        center_x = 112 + int(20 * np.sin(i * 0.1))
        center_y = 112
        cv2.circle(frame, (center_x, center_y), 50, (200, 180, 160), -1)  # Face
        cv2.circle(frame, (center_x - 15, center_y - 10), 5, (50, 50, 50), -1)  # Left eye
        cv2.circle(frame, (center_x + 15, center_y - 10), 5, (50, 50, 50), -1)  # Right eye
        cv2.ellipse(frame, (center_x, center_y + 15), (15, 8), 0, 0, 180, (50, 50, 50), 2)  # Mouth
        out.write(frame)
    
    out.release()
    return temp_file.name


def test_predict_embeddings():
    """Test prediction with pre-computed embeddings"""
    print("\n" + "="*50)
    print("Testing /predict/embeddings endpoint...")
    print("="*50)
    
    # Create dummy embeddings
    audio_emb = np.random.randn(1, 200, 1024).tolist()
    vit_emb = np.random.randn(1, 32, 768).tolist()
    landmark_emb = np.random.randn(1, 32, 936).tolist()
    
    payload = {
        "audio": audio_emb,
        "vit": vit_emb,
        "landmarks": landmark_emb
    }
    
    print("Sending request with random embeddings...")
    response = requests.post(
        f"{API_URL}/predict/embeddings",
        json=payload
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        print(f"\n📊 Prediction: {result['prediction']['emotion']} "
              f"(confidence: {result['prediction']['confidence']:.2%})")
        print("✅ Embeddings prediction passed!")
    else:
        print(f"❌ Error: {response.text}")


def test_predict_audio():
    """Test audio-only prediction"""
    print("\n" + "="*50)
    print("Testing /predict/audio endpoint...")
    print("="*50)
    
    # Create dummy audio file
    audio_path = create_dummy_audio_file()
    print(f"Created test audio: {audio_path}")
    
    try:
        with open(audio_path, 'rb') as f:
            files = {'audio': ('test.wav', f, 'audio/wav')}
            response = requests.post(f"{API_URL}/predict/audio", files=files)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            print("✅ Audio prediction passed!")
        else:
            print(f"❌ Error: {response.text}")
    finally:
        os.unlink(audio_path)


def test_predict_video():
    """Test video-only prediction"""
    print("\n" + "="*50)
    print("Testing /predict/video endpoint...")
    print("="*50)
    
    video_path = create_dummy_video_file()
    
    if video_path is None:
        print("⚠️ Skipping video test (OpenCV not available)")
        return
    
    print(f"Created test video: {video_path}")
    
    try:
        with open(video_path, 'rb') as f:
            files = {'video': ('test.mp4', f, 'video/mp4')}
            response = requests.post(f"{API_URL}/predict/video", files=files)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            print("✅ Video prediction passed!")
        else:
            print(f"❌ Error: {response.text}")
    finally:
        os.unlink(video_path)


def test_predict_multimodal():
    """Test full multimodal prediction"""
    print("\n" + "="*50)
    print("Testing /predict/multimodal endpoint...")
    print("="*50)
    
    audio_path = create_dummy_audio_file()
    video_path = create_dummy_video_file()
    
    if video_path is None:
        print("⚠️ Skipping multimodal test (OpenCV not available)")
        os.unlink(audio_path)
        return
    
    print(f"Created test audio: {audio_path}")
    print(f"Created test video: {video_path}")
    
    try:
        with open(audio_path, 'rb') as audio_f, open(video_path, 'rb') as video_f:
            files = {
                'audio': ('test.wav', audio_f, 'audio/wav'),
                'video': ('test.mp4', video_f, 'video/mp4')
            }
            print("Sending request (this may take a while)...")
            response = requests.post(f"{API_URL}/predict/multimodal", files=files)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            
            pred = result['prediction']
            timing = result['timing']
            
            print(f"\n📊 RESULTS:")
            print(f"   Emotion: {pred['emotion']} ({pred['confidence']:.2%})")
            print(f"   Valence: {pred['valence']}")
            print(f"   Arousal: {pred['arousal']}")
            print(f"   Intensity: {pred['intensity']}")
            print(f"\n⏱️ TIMING:")
            print(f"   Feature extraction: {timing['feature_extraction_ms']:.2f}ms")
            print(f"   Inference: {timing['inference_ms']:.2f}ms")
            print(f"   Total: {timing['total_ms']:.2f}ms")
            print("\n✅ Multimodal prediction passed!")
        else:
            print(f"❌ Error: {response.text}")
    finally:
        os.unlink(audio_path)
        os.unlink(video_path)


def test_with_real_files(audio_path: str = None, video_path: str = None):
    """Test with real audio/video files"""
    print("\n" + "="*50)
    print("Testing with real files...")
    print("="*50)
    
    if audio_path and video_path:
        if not os.path.exists(audio_path):
            print(f"❌ Audio file not found: {audio_path}")
            return
        if not os.path.exists(video_path):
            print(f"❌ Video file not found: {video_path}")
            return
        
        with open(audio_path, 'rb') as audio_f, open(video_path, 'rb') as video_f:
            files = {
                'audio': (os.path.basename(audio_path), audio_f),
                'video': (os.path.basename(video_path), video_f)
            }
            response = requests.post(f"{API_URL}/predict/multimodal", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
        else:
            print(f"Error: {response.text}")
    else:
        print("Usage: test_with_real_files('path/to/audio.wav', 'path/to/video.mp4')")


def run_all_tests():
    """Run all tests"""
    print("\n" + "🧪"*25)
    print("   EMOTION RECOGNITION API - TEST SUITE")
    print("🧪"*25)
    
    tests = [
        ("Health Check", test_health),
        ("Root Endpoint", test_root),
        ("Embeddings Prediction", test_predict_embeddings),
        ("Audio Prediction", test_predict_audio),
        ("Video Prediction", test_predict_video),
        ("Multimodal Prediction", test_predict_multimodal),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            test_func()
            results.append((name, "✅ PASSED"))
        except Exception as e:
            results.append((name, f"❌ FAILED: {e}"))
    
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    for name, status in results:
        print(f"   {name}: {status}")
    
    passed = sum(1 for _, s in results if "PASSED" in s)
    total = len(results)
    print(f"\n   Total: {passed}/{total} tests passed")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "health":
            test_health()
        elif sys.argv[1] == "embeddings":
            test_predict_embeddings()
        elif sys.argv[1] == "audio":
            test_predict_audio()
        elif sys.argv[1] == "video":
            test_predict_video()
        elif sys.argv[1] == "multimodal":
            test_predict_multimodal()
        elif sys.argv[1] == "real" and len(sys.argv) >= 4:
            test_with_real_files(sys.argv[2], sys.argv[3])
        else:
            print("Usage:")
            print("  python test_api.py           # Run all tests")
            print("  python test_api.py health    # Test health endpoint")
            print("  python test_api.py embeddings # Test embeddings endpoint")
            print("  python test_api.py audio     # Test audio endpoint")
            print("  python test_api.py video     # Test video endpoint")
            print("  python test_api.py multimodal # Test multimodal endpoint")
            print("  python test_api.py real <audio.wav> <video.mp4>  # Test with real files")
    else:
        run_all_tests()