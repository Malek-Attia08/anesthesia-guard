"""
Emotion Recognition Web UI
=====================================
Uses the EXACT SAME TESTED LOGIC from real_data_test_api.py
All audio extraction and API functions are copied verbatim.
"""

import streamlit as st
import requests
import json
import os
import shutil
import tempfile
import subprocess
import time
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title=" Emotion Recognition",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1E88E5;
        margin-bottom: 2rem;
    }
    .emotion-box {
        padding: 2rem;
        border-radius: 1rem;
        text-align: center;
        color: white;
        font-size: 2rem;
        font-weight: bold;
        margin: 1rem 0;
    }
    .confidence-text {
        font-size: 1.5rem;
        text-align: center;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

EMOTION_COLORS = {
    'angry': '#E53935',
    'disgust': '#8E24AA',
    'fear': '#FF6F00',
    'happy': '#43A047',
    'neutral': '#757575',
    'sad': '#1E88E5',
}

EMOTION_EMOJIS = {
    'angry': '😠',
    'disgust': '🤢',
    'fear': '😨',
    'happy': '😊',
    'neutral': '😐',
    'sad': '😢',
}


# ============================================================
# EXACT COPY FROM real_data_test_api.py - DO NOT MODIFY
# ============================================================

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
            raise RuntimeError(f"FFmpeg failed with code {result.returncode}: {result.stderr}")
        
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
    # Try ffmpeg first
    try:
        audio_path = extract_audio_from_video(video_path)
        return audio_path
    except RuntimeError as e:
        pass  # Will try moviepy
    
    # Fallback to moviepy
    try:
        audio_path = extract_audio_moviepy(video_path)
        return audio_path
    except RuntimeError as e:
        pass
    
    raise RuntimeError("Could not extract audio. Install FFmpeg or MoviePy.")


# ============================================================
# API FUNCTIONS - EXACT SAME LOGIC AS real_data_test_api.py
# ============================================================

def check_api_health() -> bool:
    """Check if API is running."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def predict_emotion(video_path: str, audio_path: str) -> dict:
    """
    Send video and audio to API for prediction.
    EXACT SAME LOGIC as test_with_video() in real_data_test_api.py
    """
    with open(audio_path, 'rb') as audio_f, open(video_path, 'rb') as video_f:
        files = {
            'audio': (os.path.basename(audio_path), audio_f, 'audio/wav'),
            'video': (os.path.basename(video_path), video_f)
        }
        response = requests.post(
            f"{API_URL}/predict/multimodal",
            files=files,
            timeout=120  # 2 minute timeout - same as test script
        )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise RuntimeError(f"API error: {response.status_code} - {response.text}")


# ============================================================
# UI DISPLAY FUNCTIONS
# ============================================================

def display_results(result: dict):
    """Display the prediction results beautifully."""
    pred = result['prediction']
    timing = result['timing']
    
    emotion = pred['emotion']
    confidence = pred['confidence']
    color = EMOTION_COLORS.get(emotion, '#1E88E5')
    emoji = EMOTION_EMOJIS.get(emotion, '🎭')
    
    # Main emotion display
    st.markdown(f"""
    <div class="emotion-box" style="background: {color};">
        {emoji} {emotion.upper()}
    </div>
    <p class="confidence-text">Confidence: <strong>{confidence:.1%}</strong></p>
    """, unsafe_allow_html=True)
    
    # Attributes in columns
    st.markdown("---")
    st.markdown("**📊 ATTRIBUTES:**")
    attr_cols = st.columns(3)
    
    with attr_cols[0]:
        valence_emoji = {"positive": "➕", "negative": "➖", "neutral": "⚖️"}.get(pred['valence'], "")
        st.metric("Valence", f"{valence_emoji} {pred['valence'].title()}")
    
    with attr_cols[1]:
        arousal_emoji = {"high": "⚡", "low": "😴"}.get(pred['arousal'], "")
        st.metric("Arousal", f"{arousal_emoji} {pred['arousal'].title()}")
    
    with attr_cols[2]:
        intensity_emoji = {"high": "🔥", "medium": "🔶", "low": "🔹"}.get(pred['intensity'], "")
        st.metric("Intensity", f"{intensity_emoji} {pred['intensity'].title()}")
    
    # Probability bars - SAME FORMAT AS test_with_video()
    st.markdown("---")
    st.markdown("**📈 ALL PROBABILITIES:**")
    
    probs = pred['probabilities']
    sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    
    for emotion_name, prob in sorted_probs:
        emoji = EMOTION_EMOJIS.get(emotion_name, '🎭')
        
        col_label, col_bar, col_pct = st.columns([2, 6, 1])
        with col_label:
            st.write(f"{emoji} {emotion_name.title()}")
        with col_bar:
            st.progress(prob)
        with col_pct:
            st.write(f"{prob:.1%}")
    
    # Timing info - SAME FORMAT AS test_with_video()
    st.markdown("---")
    st.markdown("**⏱️ TIMING:**")
    timing_col1, timing_col2, timing_col3 = st.columns(3)
    with timing_col1:
        st.metric("Feature Extraction", f"{timing['feature_extraction_ms']:.2f} ms")
    with timing_col2:
        st.metric("Model Inference", f"{timing['inference_ms']:.2f} ms")
    with timing_col3:
        st.metric("Total", f"{timing['total_ms']:.2f} ms")


# ============================================================
# MAIN APP
# ============================================================

def main():
    # Header
    st.markdown('<h1 class="main-header">🎭 Emotion Recognition</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p style="text-align: center; color: #666; font-size: 1.2rem;">'
        'Upload a video to analyze emotions using multimodal AI</p>', 
        unsafe_allow_html=True
    )
    
    # Sidebar - System Status
    with st.sidebar:
        st.header("⚙️ System Status")
        
        # API Status
        api_status = check_api_health()
        if api_status:
            st.success("✅ API Connected")
        else:
            st.error("❌ API Not Running")
            st.code("python -m uvicorn app.main:app --port 8000", language="bash")
        
        # FFmpeg Status
        ffmpeg_path = find_ffmpeg()
        if ffmpeg_path:
            st.success("✅ FFmpeg Found")
            st.caption(f"📍 {ffmpeg_path}")
        else:
            st.warning("⚠️ FFmpeg not in PATH")
            st.caption("Will try MoviePy as fallback")
        
        st.divider()
        
        st.subheader("ℹ️ Supported Emotions")
        for emotion, emoji in EMOTION_EMOJIS.items():
            color = EMOTION_COLORS[emotion]
            st.markdown(f"{emoji} **{emotion.title()}**")
        
        st.divider()
        st.caption("Using same logic as real_data_test_api.py ✅")
    
    # Main content - two columns
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📹 Video Input")
        
        # Input method tabs
        tab1, tab2 = st.tabs(["📤 Upload File", "📁 Enter Path"])
        
        video_path = None
        temp_video_path = None
        
        with tab1:
            uploaded_file = st.file_uploader(
                "Choose a video file",
                type=['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'],
                help="Supported: MP4, AVI, MOV, MKV, WebM, FLV"
            )
            
            if uploaded_file is not None:
                # Save to temp file
                suffix = Path(uploaded_file.name).suffix
                temp_video = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
                temp_video.write(uploaded_file.read())
                temp_video.close()
                video_path = temp_video.name
                temp_video_path = video_path
        
        with tab2:
            file_path_input = st.text_input(
                "Enter full path to video:",
                placeholder=r"C:\Users\ASUS\Downloads\01-01-05-01-01-01-01.mp4"
            )
            if file_path_input:
                if os.path.isfile(file_path_input):
                    video_path = file_path_input
                    st.success("✅ File found!")
                else:
                    st.error("❌ File not found")
        
        # Display video preview
        if video_path and os.path.exists(video_path):
            st.markdown("**🎬 Preview:**")
            
            try:
                st.video(video_path)
            except Exception as e:
                st.warning(f"Cannot preview this format in browser")
                st.info(f"File will still be processed: {video_path}")
            
            # File info - SAME AS test_with_video()
            file_size = os.path.getsize(video_path) / 1024 / 1024
            st.caption(f"📁 File size: {file_size:.2f} MB")
    
    with col2:
        st.subheader("🎯 Analysis Results")
        
        if video_path and os.path.exists(video_path):
            
            # Analyze button
            if not api_status:
                st.warning("⚠️ Start the API first to enable analysis")
                st.button("🔍 Analyze Emotion", disabled=True, use_container_width=True)
            else:
                analyze_clicked = st.button(
                    "🔍 Analyze Emotion", 
                    type="primary", 
                    use_container_width=True
                )
                
                if analyze_clicked:
                    audio_path = None
                    
                    try:
                        # Progress indicators
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # Step 1: Extract audio - SAME AS test_with_video()
                        status_text.text("🔊 Extracting audio from video...")
                        progress_bar.progress(25)
                        
                        audio_path = get_audio_from_video(video_path)
                        audio_size = os.path.getsize(audio_path) / 1024
                        
                        status_text.text(f"✅ Audio extracted ({audio_size:.2f} KB)")
                        progress_bar.progress(50)
                        time.sleep(0.3)
                        
                        # Step 2: Send to API - SAME AS test_with_video()
                        status_text.text("📤 Sending to API...")
                        progress_bar.progress(60)
                        
                        result = predict_emotion(video_path, audio_path)
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Analysis complete!")
                        time.sleep(0.5)
                        
                        # Clear progress indicators
                        status_text.empty()
                        progress_bar.empty()
                        
                        # Store result in session state
                        st.session_state['result'] = result
                        st.session_state['video_analyzed'] = video_path
                        
                    except Exception as e:
                        progress_bar.empty()
                        status_text.empty()
                        st.error(f"❌ Error: {e}")
                        
                        with st.expander("🔍 Error Details"):
                            import traceback
                            st.code(traceback.format_exc())
                        
                    finally:
                        # Cleanup - SAME AS test_with_video()
                        if audio_path and os.path.exists(audio_path):
                            os.unlink(audio_path)
            
            # Display stored results
            if 'result' in st.session_state:
                display_results(st.session_state['result'])
        
        else:
            st.info("👈 Upload or select a video file to begin analysis")
            
            with st.expander("📖 How it works"):
                st.markdown("""
                1. **Upload** a video or enter file path
                2. Click **Analyze Emotion**
                3. Audio is extracted from video (using FFmpeg)
                4. Both audio and video sent to API
                5. AI analyzes multimodal features
                6. View emotion prediction with confidence
                
                **Same process as the test script!**
                """)
    
    # Footer
    st.divider()
    st.markdown(
        '<p style="text-align: center; color: #888;">'
        '🎭 Multimodal Emotion Recognition | '
        '<a href="http://localhost:8000/docs" target="_blank">📚 API Docs</a> | '
        'Using tested logic from real_data_test_api.py ✅'
        '</p>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()