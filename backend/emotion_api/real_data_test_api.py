"""
Test script for Emotion Recognition API
"""

import requests
import json
import os
import shutil      
import tempfile
import subprocess
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


def find_ffmpeg() -> str:
    """Find ffmpeg executable on the system."""
    
    # Check if in PATH
    if shutil.which('ffmpeg'):
        return 'ffmpeg'
    
    # Common Windows locations
    common_paths = [
        r'C:\ffmpeg\bin\ffmpeg.exe',
        r'C:\ffmpeg\ffmpeg.exe',
        r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
        r'C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe',
        os.path.expanduser(r'~\ffmpeg\bin\ffmpeg.exe'),
        os.path.expanduser(r'~\Downloads\ffmpeg\bin\ffmpeg.exe'),
        os.path.expanduser(r'~\Downloads\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe'),
        r'C:\tools\ffmpeg\bin\ffmpeg.exe',
        r'D:\ffmpeg\bin\ffmpeg.exe',
    ]
    
    for path in common_paths:
        if os.path.isfile(path):
            return path
    
    # Try Windows 'where' command via cmd.exe (has different PATH than PowerShell)
    try:
        result = subprocess.run(
            ['cmd.exe', '/c', 'where', 'ffmpeg'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0].strip()
    except:
        pass
    
    return None


def extract_audio_from_video(video_path: str, output_audio_path: str = None) -> str:
    """
    Extract audio from video file using ffmpeg.
    
    Args:
        video_path: Path to video file
        output_audio_path: Optional output path. If None, creates temp file.
        
    Returns:
        Path to extracted audio file
    """
    if output_audio_path is None:
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        output_audio_path = temp_file.name
        temp_file.close()
    
    # Find ffmpeg executable
    ffmpeg_cmd = find_ffmpeg()
    
    if ffmpeg_cmd is None:
        raise RuntimeError(
            "FFmpeg not found. Please either:\n"
            "  1. Add FFmpeg to PowerShell PATH: $env:Path += ';C:\\path\\to\\ffmpeg\\bin'\n"
            "  2. Or install MoviePy: pip install moviepy\n"
            "  3. Or download FFmpeg from https://ffmpeg.org/"
        )
    
    print(f"   Using FFmpeg: {ffmpeg_cmd}")
    
    # Build command
    cmd = [
        ffmpeg_cmd,           # Use found path instead of just 'ffmpeg'
        '-i', video_path,
        '-vn',                # No video
        '-acodec', 'pcm_s16le',  # PCM 16-bit
        '-ar', '16000',       # Sample rate 16kHz
        '-ac', '1',           # Mono
        '-y',                 # Overwrite output
        '-loglevel', 'error', # Suppress verbose output
        output_audio_path
    ]
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            print(f"   FFmpeg stderr: {result.stderr}")
            raise RuntimeError(f"FFmpeg failed with code {result.returncode}")
        
        # Verify output file exists and has content
        if not os.path.exists(output_audio_path):
            raise RuntimeError("FFmpeg did not produce output file")
        
        if os.path.getsize(output_audio_path) == 0:
            raise RuntimeError("FFmpeg produced empty output file")
            
        return output_audio_path
        
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timed out after 120 seconds")



def extract_audio_moviepy(video_path: str, output_audio_path: str = None) -> str:
    """
    Extract audio using moviepy (fallback if ffmpeg not available).
    """
    try:
        from moviepy.editor import VideoFileClip
    except ImportError:
        raise RuntimeError("moviepy not installed. Run: pip install moviepy")
    
    if output_audio_path is None:
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        output_audio_path = temp_file.name
        temp_file.close()
    
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(
        output_audio_path, 
        fps=16000,
        nbytes=2,
        codec='pcm_s16le',
        verbose=False,
        logger=None
    )
    video.close()
    
    return output_audio_path


def get_audio_from_video(video_path: str) -> str:
    """
    Extract audio from video using available method.
    Tries ffmpeg first, then moviepy as fallback.
    """
    print(f"   Extracting audio from video...")
    
    # Try ffmpeg first
    try:
        audio_path = extract_audio_from_video(video_path)
        print(f"   ✅ Audio extracted using FFmpeg")
        return audio_path
    except RuntimeError as e:
        print(f"   ⚠️ FFmpeg failed: {e}")
    
    # Fallback to moviepy
    try:
        audio_path = extract_audio_moviepy(video_path)
        print(f"   ✅ Audio extracted using MoviePy")
        return audio_path
    except RuntimeError as e:
        print(f"   ⚠️ MoviePy failed: {e}")
    
    raise RuntimeError("Could not extract audio. Install FFmpeg or MoviePy.")


def create_dummy_audio_file():
    """Create a dummy WAV file for testing"""
    import wave
    import struct
    
    sample_rate = 16000
    duration = 2
    frequency = 440
    n_samples = int(sample_rate * duration)
    
    samples = []
    for i in range(n_samples):
        sample = int(32767 * np.sin(2 * np.pi * frequency * i / sample_rate))
        samples.append(struct.pack('<h', sample))
    
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
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_file.name, fourcc, 30, (224, 224))
    
    for i in range(60):
        frame = np.zeros((224, 224, 3), dtype=np.uint8)
        center_x = 112 + int(20 * np.sin(i * 0.1))
        center_y = 112
        cv2.circle(frame, (center_x, center_y), 50, (200, 180, 160), -1)
        cv2.circle(frame, (center_x - 15, center_y - 10), 5, (50, 50, 50), -1)
        cv2.circle(frame, (center_x + 15, center_y - 10), 5, (50, 50, 50), -1)
        cv2.ellipse(frame, (center_x, center_y + 15), (15, 8), 0, 0, 180, (50, 50, 50), 2)
        out.write(frame)
    
    out.release()
    return temp_file.name


def test_predict_embeddings():
    """Test prediction with pre-computed embeddings"""
    print("\n" + "="*50)
    print("Testing /predict/embeddings endpoint...")
    print("="*50)
    
    audio_emb = np.random.randn(1, 200, 1024).tolist()
    vit_emb = np.random.randn(1, 32, 768).tolist()
    landmark_emb = np.random.randn(1, 32, 936).tolist()
    
    payload = {
        "audio": audio_emb,
        "vit": vit_emb,
        "landmarks": landmark_emb
    }
    
    print("Sending request with random embeddings...")
    response = requests.post(f"{API_URL}/predict/embeddings", json=payload)
    
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
    """Test full multimodal prediction with dummy files"""
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


def test_with_video(video_path: str):
    """
    Test with a real video file.
    Audio is automatically extracted from the video.
    
    Args:
        video_path: Path to video file (contains both audio and visual)
    """
    print("\n" + "="*50)
    print("Testing with real video file...")
    print("="*50)
    
    if not video_path:
        print("❌ No video path provided")
        print("Usage: python test_api.py video_path")
        return
    
    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        return
    
    print(f"📹 Video file: {video_path}")
    print(f"   File size: {os.path.getsize(video_path) / 1024 / 1024:.2f} MB")
    
    # Extract audio from video
    audio_path = None
    try:
        audio_path = get_audio_from_video(video_path)
        print(f"🔊 Audio extracted to: {audio_path}")
        print(f"   Audio size: {os.path.getsize(audio_path) / 1024:.2f} KB")
        
        # Send both to API
        print("\n📤 Sending to API...")
        with open(audio_path, 'rb') as audio_f, open(video_path, 'rb') as video_f:
            files = {
                'audio': (os.path.basename(audio_path), audio_f, 'audio/wav'),
                'video': (os.path.basename(video_path), video_f)
            }
            response = requests.post(
                f"{API_URL}/predict/multimodal", 
                files=files,
                timeout=120  # 2 minute timeout
            )
        
        print(f"\n📥 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            pred = result['prediction']
            timing = result['timing']
            
            print("\n" + "="*50)
            print("🎭 EMOTION RECOGNITION RESULTS")
            print("="*50)
            
            # Main prediction
            print(f"\n🎯 PREDICTED EMOTION: {pred['emotion'].upper()}")
            print(f"   Confidence: {pred['confidence']:.2%}")
            
            # Additional attributes
            print(f"\n📊 ATTRIBUTES:")
            print(f"   Valence:   {pred['valence']}")
            print(f"   Arousal:   {pred['arousal']}")
            print(f"   Intensity: {pred['intensity']}")
            
            # Probabilities
            print(f"\n📈 ALL PROBABILITIES:")
            sorted_probs = sorted(
                pred['probabilities'].items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            for emotion, prob in sorted_probs:
                bar = "█" * int(prob * 30)
                print(f"   {emotion:8s}: {bar} {prob:.2%}")
            
            # Timing
            print(f"\n⏱️ TIMING:")
            print(f"   Feature extraction: {timing['feature_extraction_ms']:.2f} ms")
            print(f"   Model inference:    {timing['inference_ms']:.2f} ms")
            print(f"   Total:              {timing['total_ms']:.2f} ms")
            
            print("\n" + "="*50)
            print("✅ Test completed successfully!")
            print("="*50)
            
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup extracted audio
        if audio_path and os.path.exists(audio_path):
            os.unlink(audio_path)
            print(f"\n🧹 Cleaned up temporary audio file")


def test_batch_videos(video_folder: str):
    """
    Test multiple videos from a folder.
    
    Args:
        video_folder: Path to folder containing video files
    """
    print("\n" + "="*50)
    print("Batch testing videos from folder...")
    print("="*50)
    
    if not os.path.exists(video_folder):
        print(f"❌ Folder not found: {video_folder}")
        return
    
    # Find video files
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm'}
    video_files = [
        f for f in Path(video_folder).iterdir()
        if f.suffix.lower() in video_extensions
    ]
    
    if not video_files:
        print(f"❌ No video files found in {video_folder}")
        return
    
    print(f"Found {len(video_files)} video files\n")
    
    results = []
    
    for i, video_path in enumerate(video_files[:10], 1):  # Limit to 10 for testing
        print(f"\n[{i}/{min(len(video_files), 10)}] Processing: {video_path.name}")
        print("-" * 40)
        
        audio_path = None
        try:
            # Extract audio
            audio_path = get_audio_from_video(str(video_path))
            
            # Send to API
            with open(audio_path, 'rb') as audio_f, open(video_path, 'rb') as video_f:
                files = {
                    'audio': (f'{video_path.stem}.wav', audio_f, 'audio/wav'),
                    'video': (video_path.name, video_f)
                }
                response = requests.post(
                    f"{API_URL}/predict/multimodal",
                    files=files,
                    timeout=120
                )
            
            if response.status_code == 200:
                result = response.json()
                pred = result['prediction']
                
                results.append({
                    'file': video_path.name,
                    'emotion': pred['emotion'],
                    'confidence': pred['confidence'],
                    'status': 'success'
                })
                
                print(f"   ✅ {pred['emotion'].upper()} ({pred['confidence']:.2%})")
            else:
                results.append({
                    'file': video_path.name,
                    'emotion': None,
                    'confidence': None,
                    'status': f'error: {response.status_code}'
                })
                print(f"   ❌ Error: {response.status_code}")
                
        except Exception as e:
            results.append({
                'file': video_path.name,
                'emotion': None,
                'confidence': None,
                'status': f'error: {str(e)}'
            })
            print(f"   ❌ Error: {e}")
            
        finally:
            if audio_path and os.path.exists(audio_path):
                os.unlink(audio_path)
    
    # Summary
    print("\n" + "="*50)
    print("BATCH RESULTS SUMMARY")
    print("="*50)
    
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] != 'success']
    
    print(f"\nProcessed: {len(results)} videos")
    print(f"Success:   {len(successful)}")
    print(f"Failed:    {len(failed)}")
    
    if successful:
        # Emotion distribution
        from collections import Counter
        emotion_counts = Counter(r['emotion'] for r in successful)
        
        print(f"\n📊 EMOTION DISTRIBUTION:")
        for emotion, count in emotion_counts.most_common():
            pct = count / len(successful) * 100
            bar = "█" * int(pct / 5)
            print(f"   {emotion:8s}: {bar} {count} ({pct:.1f}%)")
        
        # Average confidence
        avg_conf = sum(r['confidence'] for r in successful) / len(successful)
        print(f"\n📈 Average confidence: {avg_conf:.2%}")
    
    if failed:
        print(f"\n⚠️ FAILED FILES:")
        for r in failed:
            print(f"   - {r['file']}: {r['status']}")


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


def print_usage():
    """Print usage information"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║         EMOTION RECOGNITION API - TEST SCRIPT                 ║
╠══════════════════════════════════════════════════════════════╣
║ Usage:                                                        ║
║                                                               ║
║   python test_api.py                                          ║
║       Run all basic tests with dummy data                     ║
║                                                               ║
║   python test_api.py <video_path>                             ║
║       Test with a real video file                             ║
║       Audio is automatically extracted from video             ║
║                                                               ║
║   python test_api.py --batch <folder_path>                    ║
║       Batch test all videos in a folder                       ║
║                                                               ║
║   python test_api.py health                                   ║
║       Test health endpoint only                               ║
║                                                               ║
║   python test_api.py embeddings                               ║
║       Test embeddings endpoint only                           ║
║                                                               ║
╠══════════════════════════════════════════════════════════════╣
║ Examples:                                                     ║
║                                                               ║
║   python test_api.py video.mp4                                ║
║   python test_api.py "C:\\Videos\\emotion_test.mp4"           ║
║   python test_api.py --batch "C:\\CREMA-D\\VideoFlash"        ║
║                                                               ║
╚══════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 1:
        # No arguments - run all tests
        run_all_tests()
        
    elif len(sys.argv) == 2:
        arg = sys.argv[1]
        
        if arg in ['--help', '-h', 'help']:
            print_usage()
        elif arg == 'health':
            test_health()
        elif arg == 'embeddings':
            test_predict_embeddings()
        elif arg == 'audio':
            test_predict_audio()
        elif arg == 'video':
            test_predict_video()
        elif arg == 'multimodal':
            test_predict_multimodal()
        elif os.path.isfile(arg):
            # It's a video file path
            test_with_video(arg)
        elif os.path.isdir(arg):
            # It's a folder path
            test_batch_videos(arg)
        else:
            print(f"❌ Unknown argument or file not found: {arg}")
            print_usage()
            
    elif len(sys.argv) == 3:
        if sys.argv[1] == '--batch':
            test_batch_videos(sys.argv[2])
        else:
            print(f"❌ Unknown argument: {sys.argv[1]}")
            print_usage()
    else:
        print_usage()