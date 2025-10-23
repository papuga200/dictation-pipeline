"""
Streamlit GUI for Dictation Builder.
Allows uploading canonical text, words JSON, and audio.
Includes manual time adjustment feature for sentence alignment.
"""

import streamlit as st
import json
import tempfile
from pathlib import Path
import traceback
import base64
import streamlit.components.v1 as components
from pydub import AudioSegment
from dotenv import load_dotenv

# Load environment variables from .env file (for XAI_API_KEY, etc.)
load_dotenv()

from pipeline.builder import DictationBuilder
from pipeline.segmentation import segment_sentences
from pipeline.normalize import strip_embedded_quotes
from pipeline.audio import get_audio_info

# Try to import AssemblyAI module (optional)
try:
    from pipeline.assemblyai_transcribe import AssemblyAITranscriber, test_api_key
    ASSEMBLYAI_AVAILABLE = True
except ImportError:
    ASSEMBLYAI_AVAILABLE = False


# Page configuration
st.set_page_config(
    page_title="Dictation Builder",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'builder' not in st.session_state:
    st.session_state.builder = None
if 'sentences' not in st.session_state:
    st.session_state.sentences = []
if 'alignment_results' not in st.session_state:
    st.session_state.alignment_results = None
if 'manual_adjustments' not in st.session_state:
    st.session_state.manual_adjustments = {}
if 'audio_duration_ms' not in st.session_state:
    st.session_state.audio_duration_ms = 0
if 'audio_file_bytes' not in st.session_state:
    st.session_state.audio_file_bytes = None
if 'seek_to_time_ms' not in st.session_state:
    st.session_state.seek_to_time_ms = None
if 'canonical_text_data' not in st.session_state:
    st.session_state.canonical_text_data = None
if 'assemblyai_api_key' not in st.session_state:
    st.session_state.assemblyai_api_key = ""
if 'auto_transcribed_json' not in st.session_state:
    st.session_state.auto_transcribed_json = None
if 'use_auto_transcribe' not in st.session_state:
    st.session_state.use_auto_transcribe = False


def format_time(ms):
    """Format milliseconds as MM:SS.mmm"""
    total_sec = ms / 1000.0
    minutes = int(total_sec // 60)
    seconds = total_sec % 60
    return f"{minutes:02d}:{seconds:06.3f}"


def parse_time(time_str):
    """Parse MM:SS.mmm to milliseconds"""
    try:
        if ':' in time_str:
            parts = time_str.split(':')
            minutes = int(parts[0])
            seconds = float(parts[1])
            return int((minutes * 60 + seconds) * 1000)
        else:
            return int(float(time_str) * 1000)
    except:
        return 0


def create_audio_player(audio_bytes, duration_ms, seek_to_ms=None):
    """Create custom HTML5 audio player with timestamp display and seek capability"""
    
    # Encode audio to base64 for embedding
    audio_b64 = base64.b64encode(audio_bytes).decode()
    
    # Determine audio type from bytes
    audio_type = "audio/mpeg"  # Default to MP3
    if audio_bytes[:4] == b'RIFF':
        audio_type = "audio/wav"
    elif audio_bytes[:4] == b'fLaC':
        audio_type = "audio/flac"
    
    # Convert seek time to seconds
    seek_to_sec = (seek_to_ms / 1000.0) if seek_to_ms else 0
    
    html = f"""
    <div style="border: 2px solid #4CAF50; padding: 20px; border-radius: 10px; background-color: #f9f9f9;">
        <h4 style="margin-top: 0; color: #4CAF50;">🎵 Audio Player</h4>
        
        <audio id="audioPlayer" preload="metadata">
            <source src="data:{audio_type};base64,{audio_b64}" type="{audio_type}">
            Your browser does not support the audio element.
        </audio>
        
        <div style="margin-top: 15px; text-align: center;">
            <button onclick="playPause()" style="padding: 12px 24px; font-size: 16px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 5px;">
                ▶ Play/Pause
            </button>
        </div>
        
        <div style="margin-top: 10px; text-align: center;">
            <span style="font-weight: bold; margin-right: 10px;">Large Steps:</span>
            <button onclick="skipBack(5)" style="padding: 10px 18px; font-size: 14px; background-color: #2196F3; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 3px;">
                ⏪ -5s
            </button>
            <button onclick="skipBack(1)" style="padding: 10px 18px; font-size: 14px; background-color: #2196F3; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 3px;">
                -1s
            </button>
            <button onclick="skipForward(1)" style="padding: 10px 18px; font-size: 14px; background-color: #2196F3; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 3px;">
                +1s
            </button>
            <button onclick="skipForward(5)" style="padding: 10px 18px; font-size: 14px; background-color: #2196F3; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 3px;">
                +5s ⏩
            </button>
        </div>
        
        <div style="margin-top: 10px; text-align: center;">
            <span style="font-weight: bold; margin-right: 10px;">Fine Control:</span>
            <button onclick="skipBack(0.5)" style="padding: 8px 14px; font-size: 13px; background-color: #FF9800; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 3px;">
                ⏪ -500ms
            </button>
            <button onclick="skipBack(0.1)" style="padding: 8px 14px; font-size: 13px; background-color: #FF9800; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 3px;">
                -100ms
            </button>
            <button onclick="skipForward(0.1)" style="padding: 8px 14px; font-size: 13px; background-color: #FF9800; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 3px;">
                +100ms
            </button>
            <button onclick="skipForward(0.5)" style="padding: 8px 14px; font-size: 13px; background-color: #FF9800; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 3px;">
                +500ms ⏩
            </button>
            <select onchange="changeSpeed(this.value)" style="padding: 8px; font-size: 14px; border-radius: 5px; margin-left: 15px;">
                <option value="0.5">0.5x</option>
                <option value="0.75">0.75x</option>
                <option value="1.0" selected>1.0x</option>
                <option value="1.25">1.25x</option>
                <option value="1.5">1.5x</option>
            </select>
        </div>
        
        <div style="margin-top: 20px; text-align: center; font-size: 24px; font-family: 'Courier New', monospace; font-weight: bold; color: #333;">
            <span id="currentTime">00:00.000</span> / <span id="duration">00:00.000</span>
        </div>
        
        <input type="range" id="seekbar" value="0" min="0" max="1000" 
               style="width: 100%; margin-top: 15px; height: 8px; cursor: pointer;" 
               oninput="seek(this.value)">
        
        <div style="margin-top: 10px; text-align: center; color: #666; font-size: 12px;">
            <span id="statusMessage"></span>
        </div>
    </div>
    
    <script>
        const audio = document.getElementById('audioPlayer');
        const currentTimeDisplay = document.getElementById('currentTime');
        const durationDisplay = document.getElementById('duration');
        const seekbar = document.getElementById('seekbar');
        const statusMessage = document.getElementById('statusMessage');
        
        function formatTime(ms) {{
            const totalSeconds = Math.floor(ms / 1000);
            const minutes = Math.floor(totalSeconds / 60);
            const seconds = totalSeconds % 60;
            const milliseconds = Math.floor(ms % 1000);
            return `${{minutes.toString().padStart(2, '0')}}:${{seconds.toString().padStart(2, '0')}}.${{milliseconds.toString().padStart(3, '0')}}`;
        }}
        
        function playPause() {{
            if (audio.paused) {{
                audio.play();
                statusMessage.textContent = 'Playing...';
            }} else {{
                audio.pause();
                statusMessage.textContent = 'Paused';
            }}
        }}
        
        function skipBack(seconds) {{
            audio.currentTime = Math.max(0, audio.currentTime - seconds);
        }}
        
        function skipForward(seconds) {{
            audio.currentTime = Math.min(audio.duration, audio.currentTime + seconds);
        }}
        
        function changeSpeed(rate) {{
            audio.playbackRate = parseFloat(rate);
            statusMessage.textContent = `Playback speed: ${{rate}}x`;
            setTimeout(() => {{ statusMessage.textContent = ''; }}, 2000);
        }}
        
        function seek(value) {{
            const time = (value / 1000) * audio.duration;
            audio.currentTime = time;
        }}
        
        function seekToTime(seconds) {{
            audio.currentTime = seconds;
            audio.pause();  // Start paused, not playing
            statusMessage.textContent = `Jumped to ${{formatTime(seconds * 1000)}} (paused)`;
            setTimeout(() => {{ statusMessage.textContent = ''; }}, 3000);
        }}
        
        audio.addEventListener('loadedmetadata', function() {{
            durationDisplay.textContent = formatTime(audio.duration * 1000);
            seekbar.max = 1000;
            
            // Seek to initial position if specified
            const seekTo = {seek_to_sec};
            if (seekTo > 0) {{
                seekToTime(seekTo);
            }}
        }});
        
        audio.addEventListener('timeupdate', function() {{
            const currentMs = audio.currentTime * 1000;
            currentTimeDisplay.textContent = formatTime(currentMs);
            if (audio.duration > 0) {{
                seekbar.value = (audio.currentTime / audio.duration) * 1000;
            }}
        }});
        
        audio.addEventListener('ended', function() {{
            statusMessage.textContent = 'Audio finished';
        }});
        
        // Keyboard shortcuts
        document.addEventListener('keydown', function(e) {{
            if (e.code === 'Space') {{
                e.preventDefault();
                playPause();
            }} else if (e.code === 'ArrowLeft') {{
                e.preventDefault();
                skipBack(5);
            }} else if (e.code === 'ArrowRight') {{
                e.preventDefault();
                skipForward(5);
            }}
        }});
    </script>
    """
    
    components.html(html, height=400)


# Header
st.title("🎧 Dictation Builder")
st.markdown("""
Build dictation audio from source recordings with word-level timestamps.
- 🤖 **Auto-transcribe** with AssemblyAI or upload existing JSON
- Adjusts tempo to 0.92× (pitch preserved)
- Repeats each sentence 3× with configurable pauses
- Supports manual time adjustment for sentence alignment
- Outputs compressed MP3 for smaller file sizes
""")

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # AssemblyAI API Key Section
    if ASSEMBLYAI_AVAILABLE:
        with st.expander("🤖 AssemblyAI Auto-Transcription", expanded=False):
            st.markdown("""
            Enable automatic transcription to skip manual JSON upload.
            Get your API key from [AssemblyAI](https://www.assemblyai.com/).
            """)
            
            api_key_input = st.text_input(
                "AssemblyAI API Key",
                value=st.session_state.assemblyai_api_key,
                type="password",
                help="Your AssemblyAI API key (kept secure in session)"
            )
            
            if api_key_input != st.session_state.assemblyai_api_key:
                st.session_state.assemblyai_api_key = api_key_input
            
            # Test API key button
            if st.session_state.assemblyai_api_key:
                if st.button("🔑 Test API Key"):
                    valid, message = test_api_key(st.session_state.assemblyai_api_key)
                    if valid:
                        st.success(message)
                    else:
                        st.error(message)
            
            st.caption("💡 With a valid API key, you can auto-transcribe audio instead of uploading JSON.")
    else:
        st.info("📦 Install `assemblyai` package to enable auto-transcription:\n```\npip install assemblyai\n```")
    
    st.divider()
    
    tempo = st.slider("Tempo", min_value=0.5, max_value=2.0, value=0.92, step=0.01, 
                      help="Playback speed multiplier (1.0 = normal, 0.92 = 92% speed)")
    
    st.divider()
    
    # Dynamic repetitions section
    st.subheader("🔄 Repetitions")
    use_dynamic_reps = st.checkbox(
        "Enable dynamic repetitions based on chunk length",
        value=True,
        help="Automatically adjust repetitions: shorter chunks get fewer repeats, longer chunks get more"
    )
    
    if use_dynamic_reps:
        threshold_seconds = st.slider(
            "Long chunk threshold (seconds)",
            min_value=1.0,
            max_value=10.0,
            value=4.5,
            step=0.5,
            help="Chunks shorter than this get SHORT repeats, longer chunks get LONG repeats"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            short_chunk_repeats = st.number_input(
                f"Short chunks (< {threshold_seconds}s)",
                min_value=1,
                max_value=10,
                value=3,
                step=1,
                help=f"Repetitions for chunks shorter than {threshold_seconds} seconds"
            )
        with col2:
            long_chunk_repeats = st.number_input(
                f"Long chunks (≥ {threshold_seconds}s)",
                min_value=1,
                max_value=10,
                value=5,
                step=1,
                help=f"Repetitions for chunks {threshold_seconds} seconds or longer"
            )
        
        # Override repeats for backwards compatibility
        repeats = short_chunk_repeats  # Default fallback
    else:
        # Fixed repetitions
        repeats = st.number_input("Repeats per sentence", min_value=1, max_value=10, value=3, step=1)
        threshold_seconds = 4.5
        short_chunk_repeats = repeats
        long_chunk_repeats = repeats
    
    st.divider()
    
    pause_ms = st.number_input("Pause between repeats (ms)", min_value=0, max_value=60000, value=10000, step=500)
    inter_pause_ms = st.number_input("Pause between sentences (ms)", min_value=0, max_value=60000, value=10000, step=500)
    pad_ms = st.number_input("Audio padding (ms)", min_value=0, max_value=500, value=100, step=10,
                              help="Padding added to start/end of each sentence clip")
    fade_ms = st.number_input("Fade in/out (ms)", min_value=0, max_value=50, value=8, step=1,
                               help="Fade duration to prevent clicks")
    
    st.divider()
    
    with st.expander("Advanced Alignment Settings"):
        min_accept = st.slider("Min acceptance score", 0.0, 1.0, 0.82, 0.01)
        warn_accept = st.slider("Warning threshold", 0.0, 1.0, 0.75, 0.01)
        window_tokens = st.number_input("Search window (tokens)", 100, 10000, 4000, 100)

# Main content
tab1, tab2, tab3 = st.tabs(["📤 Upload & Configure", "✏️ Review & Adjust", "📥 Build & Download"])

# Tab 1: Upload
with tab1:
    st.header("Step 1: Upload Files")
    
    # Canonical text (full width for better visibility)
    st.subheader("Canonical Text")
    canonical_text = st.text_area(
        "Paste or type the exact text students should transcribe",
        height=500,
        help="This is the reference text. Embedded quotes will be stripped for alignment."
    )
    
    st.divider()
    
    # Check if auto-transcription is available
    can_auto_transcribe = (
        ASSEMBLYAI_AVAILABLE and 
        st.session_state.assemblyai_api_key and 
        len(st.session_state.assemblyai_api_key.strip()) > 0
    )
    
    # Mode selection
    if can_auto_transcribe:
        transcribe_mode = st.radio(
            "Transcription Mode",
            ["🤖 Auto-transcribe with AssemblyAI", "📄 Upload JSON manually"],
            help="Choose whether to automatically transcribe or upload existing JSON"
        )
        use_auto = transcribe_mode.startswith("🤖")
    else:
        use_auto = False
        st.info("💡 Add your AssemblyAI API key in the sidebar to enable automatic transcription!")
    
    st.divider()
    
    # File uploaders based on mode
    if use_auto:
        # Auto-transcription mode: Only need audio file
        st.subheader("Audio File")
        audio_file = st.file_uploader(
            "Source Audio",
            type=['wav', 'mp3', 'm4a', 'flac'],
            help="Audio will be automatically transcribed using AssemblyAI"
        )
        words_file = None  # Not needed in auto mode
        
        if audio_file:
            st.success("✅ Audio file uploaded. Click 'Auto-Transcribe & Load' to begin.")
    else:
        # Manual mode: Need both JSON and audio
        col1, col2 = st.columns(2)
        
        with col1:
            words_file = st.file_uploader(
                "Word Timestamps JSON",
                type=['json'],
                help="JSON file with word-level timestamps (supports AssemblyAI format)"
            )
        
        with col2:
            audio_file = st.file_uploader(
                "Source Audio",
                type=['wav', 'mp3', 'm4a', 'flac'],
                help="Original audio recording"
            )
    
    st.divider()
    
    # Preview/Transcribe button
    if use_auto and canonical_text and audio_file:
        # Auto-transcription mode
        if st.button("🤖 Auto-Transcribe & Load", type="primary", use_container_width=True):
            with st.spinner("Transcribing audio with AssemblyAI... This may take a few minutes."):
                try:
                    # Save canonical text
                    st.session_state.canonical_text_data = canonical_text
                    
                    # Save audio to temp file
                    audio_bytes = audio_file.read()
                    st.session_state.audio_file_bytes = audio_bytes
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(audio_file.name).suffix) as tmp:
                        tmp.write(audio_bytes)
                        tmp_audio_path = Path(tmp.name)
                    
                    try:
                        # Get audio duration
                        audio_info = get_audio_info(tmp_audio_path)
                        st.session_state.audio_duration_ms = audio_info['duration_ms']
                        
                        # Create transcriber
                        transcriber = AssemblyAITranscriber(st.session_state.assemblyai_api_key)
                        
                        # Progress callback
                        progress_placeholder = st.empty()
                        def progress_callback(status):
                            progress_placeholder.info(status)
                        
                        # Transcribe
                        transcript_data = transcriber.transcribe_audio(
                            tmp_audio_path,
                            progress_callback=progress_callback
                        )
                        
                        # Store transcription result
                        st.session_state.auto_transcribed_json = transcript_data
                        st.session_state.words_data = transcript_data
                        
                        # Segment sentences
                        sentences = segment_sentences(canonical_text, strip_quotes=True)
                        st.session_state.sentences = sentences
                        
                        progress_placeholder.empty()
                        st.success(f"✅ Transcription complete! Found {len(transcript_data['words'])} words and {len(sentences)} sentences.")
                        
                        # Show preview
                        st.subheader("Sentence Preview")
                        for idx, sent in enumerate(sentences[:10], start=1):
                            st.markdown(f"**{idx}.** {sent[:100]}{'...' if len(sent) > 100 else ''}")
                        
                        if len(sentences) > 10:
                            st.info(f"... and {len(sentences) - 10} more sentences")
                        
                        # Show transcribed text preview
                        with st.expander("📝 View Transcribed Text"):
                            st.text_area("AssemblyAI Transcription", transcript_data['text'], height=200)
                            st.caption(f"Duration: {transcript_data.get('audio_duration', 0):.1f} seconds | Words: {len(transcript_data['words'])}")
                        
                    finally:
                        tmp_audio_path.unlink()
                    
                    audio_file.seek(0)
                    
                except Exception as e:
                    st.error(f"Transcription error: {str(e)}")
                    st.code(traceback.format_exc())
    
    elif not use_auto and canonical_text and words_file and audio_file:
        # Preview button
        if st.button("🔍 Preview Sentences & Load for Adjustment", type="primary", use_container_width=True):
            with st.spinner("Analyzing..."):
                try:
                    # Save canonical text
                    st.session_state.canonical_text_data = canonical_text
                    
                    # Segment sentences
                    sentences = segment_sentences(canonical_text, strip_quotes=True)
                    st.session_state.sentences = sentences
                    
                    # Load words JSON
                    words_data = json.loads(words_file.read())
                    st.session_state.words_data = words_data
                    words_file.seek(0)  # Reset for later use
                    
                    # Get audio duration and save bytes
                    audio_bytes = audio_file.read()
                    st.session_state.audio_file_bytes = audio_bytes
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as tmp:
                        tmp.write(audio_bytes)
                        tmp_path = Path(tmp.name)
                    
                    try:
                        audio_info = get_audio_info(tmp_path)
                        st.session_state.audio_duration_ms = audio_info['duration_ms']
                    finally:
                        tmp_path.unlink()
                    
                    audio_file.seek(0)  # Reset for later use
                    
                    st.success(f"✅ Found {len(sentences)} sentences. Go to 'Review & Adjust' tab to review alignment.")
                    
                    # Show preview
                    st.subheader("Sentence Preview")
                    for idx, sent in enumerate(sentences[:10], start=1):
                        st.markdown(f"**{idx}.** {sent[:100]}{'...' if len(sent) > 100 else ''}")
                    
                    if len(sentences) > 10:
                        st.info(f"... and {len(sentences) - 10} more sentences")
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.code(traceback.format_exc())

# Tab 2: Review & Adjust
with tab2:
    st.header("Step 2: Review Alignment & Make Adjustments")
    
    if not st.session_state.sentences:
        st.info("👈 Please upload files and preview sentences in the Upload tab first.")
    else:
        st.markdown(f"""
        **Total sentences:** {len(st.session_state.sentences)}  
        **Audio duration:** {format_time(st.session_state.audio_duration_ms)}
        """)
        
        # Audio Player
        if st.session_state.audio_file_bytes:
            create_audio_player(
                st.session_state.audio_file_bytes,
                st.session_state.audio_duration_ms,
                st.session_state.seek_to_time_ms
            )
            st.caption("💡 **Tip:** Use the audio player to find exact timestamps. Click '🎯 Jump' buttons below to jump to sentence positions (paused). Use fine control buttons (±100ms/±500ms) for precision. Keyboard shortcuts: Space=Play/Pause, Arrow keys=Skip ±5s")
            
            # Reset seek after displaying
            if st.session_state.seek_to_time_ms is not None:
                st.session_state.seek_to_time_ms = None
        
        # Display canonical text
        if 'canonical_text_data' in st.session_state:
            with st.expander("📄 View Full Canonical Text", expanded=False):
                # Use markdown/code block for black text display
                st.markdown("**Canonical Text (Reference):**")
                st.markdown(
                    f"""<div style="
                        background-color: #f0f0f0; 
                        padding: 20px; 
                        border-radius: 5px; 
                        border: 1px solid #ccc;
                        font-family: 'Arial', sans-serif;
                        font-size: 16px;
                        line-height: 1.6;
                        color: #000000;
                        max-height: 500px;
                        overflow-y: auto;
                        white-space: pre-wrap;
                    ">{st.session_state.canonical_text_data}</div>""",
                    unsafe_allow_html=True
                )
        
        st.divider()
        
        # Run automatic alignment
        if st.button("🔄 Run Automatic Alignment", type="primary"):
            with st.spinner("Aligning sentences to word timestamps (using Grok AI + fuzzy fallback)..."):
                try:
                    from pipeline.builder import DictationBuilder
                    
                    # Create config with hybrid mode (Grok + fuzzy fallback)
                    config = {
                        'pad_ms': pad_ms,
                        'alignment': {
                            'method': 'hybrid',  # Use Grok AI with fuzzy fallback
                            'min_accept': min_accept,
                            'warn_accept': warn_accept,
                            'window_tokens': window_tokens
                        }
                    }
                    
                    builder = DictationBuilder(config)
                    words = st.session_state.words_data['words']
                    
                    # Perform hybrid alignment (Grok first, fuzzy fallback)
                    spans, report = builder._perform_alignment(
                        st.session_state.sentences, 
                        words, 
                        'hybrid'
                    )
                    
                    st.session_state.alignment_results = {
                        'spans': spans,
                        'report': report
                    }
                    
                    # Show method breakdown if available
                    if 'methods' in report.get('global', {}):
                        methods = report['global']['methods']
                        st.success(f"✅ Alignment complete! Grok: {methods.get('grok', 0)}, Fuzzy: {methods.get('fuzzy', 0)}")
                    else:
                        st.success("✅ Alignment complete!")
                    
                except Exception as e:
                    st.error(f"Alignment error: {str(e)}")
                    st.code(traceback.format_exc())
        
        # Display alignment results with manual adjustment
        if st.session_state.alignment_results:
            st.subheader("Alignment Results")
            
            report = st.session_state.alignment_results['report']
            spans = st.session_state.alignment_results['spans']
            
            # Summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("✅ Aligned", report['global']['aligned'])
            with col2:
                st.metric("⚠️ Warnings", report['global'].get('warnings', 0))
            with col3:
                st.metric("❌ Failed", report['global']['unaligned'])
            
            st.divider()
            
            # Show each sentence with adjustment controls
            st.subheader("Manual Time Adjustments")
            st.markdown("Review and adjust sentence boundaries. Times are in MM:SS.mmm format or seconds.")
            
            # Filter options
            filter_opt = st.radio(
                "Show:",
                ["All sentences", "Only warnings/failures", "Only manual adjustments"],
                horizontal=True
            )
            
            # Determine which sentences to show
            show_indices = set(range(len(st.session_state.sentences)))
            
            if filter_opt == "Only warnings/failures":
                show_indices = set()
                for detail in report['details']:
                    show_indices.add(detail['idx'] - 1)
            elif filter_opt == "Only manual adjustments":
                show_indices = set(st.session_state.manual_adjustments.keys())
                if not show_indices:
                    st.info("No manual adjustments yet.")
            
            # Sort sentences by priority: failed first, then warnings, then good, then by index
            def get_sentence_priority(idx):
                sent_num = idx + 1
                for detail in report['details']:
                    if detail['idx'] == sent_num:
                        if detail.get('status') == 'not_aligned':
                            return (0, idx)  # Failed - highest priority
                        elif detail.get('status') in ['warning', 'low_score']:
                            return (1, idx)  # Warning - medium priority
                return (2, idx)  # Good - lowest priority
            
            sorted_indices = sorted(show_indices, key=get_sentence_priority)
            
            # Display sentences with section headers
            current_section = None
            
            for idx in sorted_indices:
                if idx >= len(st.session_state.sentences):
                    continue
                
                sent = st.session_state.sentences[idx]
                span = spans[idx]
                sent_num = idx + 1
                
                # Determine status and score
                status = "good"
                score = 0.0
                status_detail = None
                
                for detail in report['details']:
                    if detail['idx'] == sent_num:
                        status_detail = detail
                        score = detail.get('score', 0.0)
                        if detail.get('status') == 'not_aligned' or detail.get('status') == 'failed':
                            status = "failed"
                        elif detail.get('status') in ['warning', 'low_score']:
                            status = "warning"
                        break
                
                # If no detail found and span exists, it's a good alignment
                if status_detail is None:
                    if span:
                        score = 1.0  # Assume perfect if not flagged
                    else:
                        # No span and no detail = failed alignment
                        status = "failed"
                        score = 0.0
                
                # Check if manually adjusted
                is_adjusted = idx in st.session_state.manual_adjustments
                
                # Determine status badge and color
                if status == "failed":
                    status_badge = "🔴 FAILED"
                    status_color = "#ff4444"
                elif status == "warning":
                    status_badge = "⚠️ WARNING"
                    status_color = "#ffaa00"
                else:
                    status_badge = "✅ GOOD"
                    status_color = "#44ff44"
                
                # Show section header when status changes
                if current_section != status:
                    current_section = status
                    if status == "failed":
                        st.markdown("### 🔴 Failed Alignments (Requires Manual Adjustment)")
                    elif status == "warning":
                        st.markdown("### ⚠️ Warning - Low Quality Scores")
                    else:
                        st.markdown("### ✅ Good Alignments")
                    st.markdown("")
                
                # Container for each sentence with colored border
                border_color = status_color if status != "good" else "#cccccc"
                
                with st.container():
                    # Header row: sentence number, status badge, score
                    header_cols = st.columns([0.5, 2, 1.5, 6])
                    
                    with header_cols[0]:
                        st.markdown(f"### {sent_num}")
                    
                    with header_cols[1]:
                        st.markdown(f"<span style='background-color: {status_color}; color: black; padding: 4px 12px; border-radius: 4px; font-weight: bold; font-size: 0.85em;'>{status_badge}</span>", unsafe_allow_html=True)
                    
                    with header_cols[2]:
                        st.markdown(f"**Score:** {score:.3f}")
                    
                    with header_cols[3]:
                        if is_adjusted:
                            st.markdown("✏️ *Manually adjusted*")
                    
                    # Full sentence text (no truncation)
                    st.markdown(f"**Text:** {sent}")
                    
                    # Time adjustment row with jump buttons
                    time_cols = st.columns([1.5, 1.5, 1.5, 0.8])
                    
                    with time_cols[0]:
                        if span:
                            default_start = format_time(span[0])
                        else:
                            default_start = "00:00.000"
                        
                        if is_adjusted:
                            default_start = format_time(st.session_state.manual_adjustments[idx]['start_ms'])
                        
                        start_input = st.text_input(
                            "Start Time (MM:SS.mmm)",
                            value=default_start,
                            key=f"start_{idx}"
                        )
                    
                    with time_cols[1]:
                        if span:
                            default_end = format_time(span[1])
                        else:
                            default_end = "00:05.000"
                        
                        if is_adjusted:
                            default_end = format_time(st.session_state.manual_adjustments[idx]['end_ms'])
                        
                        end_input = st.text_input(
                            "End Time (MM:SS.mmm)",
                            value=default_end,
                            key=f"end_{idx}"
                        )
                    
                    with time_cols[2]:
                        # Jump to start button
                        jump_col1, jump_col2 = st.columns(2)
                        with jump_col1:
                            if span and st.button("🎯 Jump Start", key=f"jump_start_{idx}", help="Jump audio to sentence start"):
                                st.session_state.seek_to_time_ms = span[0]
                                st.rerun()
                        with jump_col2:
                            if span and st.button("🎯 Jump End", key=f"jump_end_{idx}", help="Jump audio to sentence end"):
                                st.session_state.seek_to_time_ms = max(0, span[1] - 2000)  # Jump 2s before end
                                st.rerun()
                    
                    with time_cols[3]:
                        st.write("")  # Spacer for alignment
                        if st.button("💾 Save", key=f"save_{idx}", help="Save manual adjustment", type="primary" if status == "failed" else "secondary"):
                            start_ms = parse_time(start_input)
                            end_ms = parse_time(end_input)
                            
                            if start_ms >= end_ms:
                                st.error(f"Invalid times for sentence {sent_num}")
                            else:
                                st.session_state.manual_adjustments[idx] = {
                                    'sentence_idx': sent_num,
                                    'start_ms': start_ms,
                                    'end_ms': end_ms
                                }
                                st.success(f"✅ Saved adjustment for sentence {sent_num}")
                                st.rerun()
                    
                    # Show reason if available
                    if status_detail and status_detail.get('reason'):
                        st.caption(f"ℹ️ {status_detail['reason']}")
                    
                    st.markdown("---")
            
            # Show manual adjustments summary
            if st.session_state.manual_adjustments:
                st.info(f"📝 {len(st.session_state.manual_adjustments)} manual adjustment(s) saved")
                if st.button("🗑️ Clear All Manual Adjustments"):
                    st.session_state.manual_adjustments = {}
                    st.rerun()

# Tab 3: Build & Download
with tab3:
    st.header("Step 3: Build Dictation Audio")
    
    if not st.session_state.sentences:
        st.info("👈 Please complete steps 1 and 2 first.")
    elif not st.session_state.alignment_results:
        st.warning("⚠️ Please run automatic alignment in the Review & Adjust tab first.")
    else:
        # Build summary text based on repetition mode
        if use_dynamic_reps:
            rep_summary = f"Dynamic (< {threshold_seconds}s: {short_chunk_repeats}×, ≥ {threshold_seconds}s: {long_chunk_repeats}×)"
        else:
            rep_summary = f"Fixed ({repeats}×)"
        
        st.markdown(f"""
        **Ready to build:**
        - {len(st.session_state.sentences)} sentences
        - {len(st.session_state.manual_adjustments)} manual adjustments
        - Tempo: {tempo}× | Repetitions: {rep_summary} | Pauses: {pause_ms}ms
        """)
        
        # Output filename customization
        st.subheader("📝 Output Files")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            custom_filename = st.text_input(
                "Base filename (without extension)",
                value="dictation_final",
                help="This will be used as the base name for all output files (audio, manifest, report)"
            )
        with col2:
            st.write("")  # Spacer
            st.write("")  # Spacer
            if st.button("🔄 Reset", help="Reset to default filename"):
                custom_filename = "dictation_final"
                st.rerun()
        
        # Sanitize filename (remove invalid characters)
        import re
        custom_filename = re.sub(r'[<>:"/\\|?*]', '_', custom_filename)
        if not custom_filename:
            custom_filename = "dictation_final"
        
        st.caption(f"📁 Files will be named: `{custom_filename}.mp3`, `{custom_filename}_manifest.json`, `{custom_filename}_report.json`")
        
        st.divider()
        
        # Output directory selection
        use_custom_output = st.checkbox("Specify custom output directory", value=False)
        
        output_dir = None
        if use_custom_output:
            output_dir_str = st.text_input(
                "Output directory path",
                value=str(Path.home() / "dictation_output"),
                help="Full path to output directory"
            )
            output_dir = Path(output_dir_str)
        
        st.divider()
        
        if st.button("🚀 Build Dictation Audio", type="primary"):
            with st.spinner("Building dictation audio... This may take several minutes."):
                try:
                    # Prepare configuration
                    config = {
                        'tempo': tempo,
                        'repeats': repeats,
                        'pause_ms': pause_ms,
                        'inter_sentence_pause_ms': inter_pause_ms,
                        'pad_ms': pad_ms,
                        'fade_ms': fade_ms,
                        'dynamic_repetitions': {
                            'enabled': use_dynamic_reps,
                            'threshold_seconds': threshold_seconds,
                            'short_chunk_repeats': short_chunk_repeats,
                            'long_chunk_repeats': long_chunk_repeats
                        },
                        'alignment': {
                            'min_accept': min_accept,
                            'warn_accept': warn_accept,
                            'window_tokens': window_tokens
                        }
                    }
                    
                    # Prepare manual adjustments list
                    manual_adj_list = [
                        adj for adj in st.session_state.manual_adjustments.values()
                    ]
                    
                    # Get file bytes (need to re-read from uploader)
                    # Note: We need the user to keep files uploaded
                    st.info("⏳ Processing... Building audio with FFmpeg...")
                    
                    # Build
                    builder = DictationBuilder(config)
                    
                    # We need to save uploaded files temporarily
                    with tempfile.TemporaryDirectory() as tmpdir:
                        tmp_path = Path(tmpdir)
                        
                        # Save audio
                        audio_tmp = tmp_path / 'audio.tmp'
                        if hasattr(audio_file, 'getvalue'):
                            # Uploaded file
                            audio_tmp.write_bytes(audio_file.getvalue())
                        else:
                            # Use cached audio bytes
                            audio_tmp.write_bytes(st.session_state.audio_file_bytes)
                        
                        # Save words JSON
                        words_tmp = tmp_path / 'words.json'
                        if st.session_state.auto_transcribed_json:
                            # Use auto-transcribed JSON
                            words_tmp.write_text(json.dumps(st.session_state.auto_transcribed_json, indent=2))
                        elif words_file:
                            # Use uploaded JSON file
                            words_tmp.write_bytes(words_file.getvalue())
                        else:
                            # Use words_data from session state (loaded earlier)
                            if 'words_data' in st.session_state:
                                words_tmp.write_text(json.dumps(st.session_state.words_data, indent=2))
                            else:
                                raise ValueError("No words JSON available. Please complete Step 1 first.")
                        
                        # Build
                        result = builder.build(
                            canonical_text=canonical_text,
                            words_json=words_tmp,
                            audio_file=audio_tmp,
                            output_dir=output_dir,
                            manual_adjustments=manual_adj_list
                        )
                    
                    st.success("✅ Build complete!")
                    
                    # Load and display results
                    audio_bytes = result['audio'].read_bytes()
                    manifest_bytes = result['manifest'].read_bytes()
                    report_bytes = result['report'].read_bytes()
                    
                    # Convert WAV to MP3 for smaller file size
                    st.info("🔄 Converting to MP3 for download...")
                    try:
                        # Load WAV and convert to MP3
                        audio_segment = AudioSegment.from_wav(result['audio'])
                        mp3_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                        mp3_temp_path = mp3_temp.name
                        mp3_temp.close()  # Close file handle before export
                        audio_segment.export(mp3_temp_path, format="mp3", bitrate="192k")
                        mp3_bytes = Path(mp3_temp_path).read_bytes()
                        Path(mp3_temp_path).unlink()  # Clean up temp file
                        
                        # Show file size comparison
                        wav_size_mb = len(audio_bytes) / (1024 * 1024)
                        mp3_size_mb = len(mp3_bytes) / (1024 * 1024)
                        reduction_pct = ((wav_size_mb - mp3_size_mb) / wav_size_mb) * 100
                        st.success(f"✅ MP3 conversion complete! Original: {wav_size_mb:.2f} MB → MP3: {mp3_size_mb:.2f} MB ({reduction_pct:.1f}% smaller)")
                        
                        # Audio player with MP3
                        st.subheader("🎵 Preview Dictation Audio")
                        st.audio(mp3_bytes, format='audio/mp3')
                        
                        # Download buttons
                        st.subheader("📥 Download Files")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.download_button(
                                "⬇️ Download Audio (MP3)",
                                data=mp3_bytes,
                                file_name=f"{custom_filename}.mp3",
                                mime="audio/mpeg"
                            )
                        
                    except Exception as e:
                        st.warning(f"⚠️ MP3 conversion failed, falling back to WAV: {str(e)}")
                        # Fallback to WAV if MP3 conversion fails
                        st.subheader("🎵 Preview Dictation Audio")
                        st.audio(audio_bytes, format='audio/wav')
                        
                        # Download buttons
                        st.subheader("📥 Download Files")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.download_button(
                                "⬇️ Download Audio (WAV)",
                                data=audio_bytes,
                                file_name=f"{custom_filename}.wav",
                                mime="audio/wav"
                            )
                    
                    with col2:
                        st.download_button(
                            "⬇️ Download Manifest",
                            data=manifest_bytes,
                            file_name=f"{custom_filename}_manifest.json",
                            mime="application/json"
                        )
                    
                    with col3:
                        st.download_button(
                            "⬇️ Download Report",
                            data=report_bytes,
                            file_name=f"{custom_filename}_report.json",
                            mime="application/json"
                        )
                    
                    # Display summary
                    st.divider()
                    st.subheader("📊 Summary")
                    
                    manifest = json.loads(manifest_bytes.decode('utf-8'))
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Total Duration", f"{manifest['total_duration_ms']/1000:.1f}s")
                    with col2:
                        st.metric("Sentences Processed", len([s for s in manifest['sentences'] if s.get('output_offsets_ms')]))
                    with col3:
                        avg_quality = sum(s['quality']['score'] for s in manifest['sentences']) / len(manifest['sentences'])
                        st.metric("Avg Quality Score", f"{avg_quality:.2f}")
                    
                    # Show repetition breakdown if dynamic repetitions were used
                    if use_dynamic_reps:
                        st.divider()
                        st.subheader("🔄 Repetition Breakdown")
                        
                        # Count sentences by repetition count
                        rep_counts = {}
                        for sent in manifest['sentences']:
                            if 'num_repeats' in sent:
                                reps = sent['num_repeats']
                                rep_counts[reps] = rep_counts.get(reps, 0) + 1
                        
                        # Display breakdown
                        if rep_counts:
                            rep_col1, rep_col2 = st.columns(2)
                            with rep_col1:
                                st.metric(f"{short_chunk_repeats}× repeats (short chunks)", rep_counts.get(short_chunk_repeats, 0))
                            with rep_col2:
                                st.metric(f"{long_chunk_repeats}× repeats (long chunks)", rep_counts.get(long_chunk_repeats, 0))
                            
                            # Show breakdown by sentence
                            with st.expander("📊 View detailed breakdown"):
                                for sent in manifest['sentences']:
                                    if 'num_repeats' in sent and 'original_duration_seconds' in sent:
                                        chunk_type = "Short" if sent['original_duration_seconds'] < threshold_seconds else "Long"
                                        st.markdown(f"**Sentence {sent['idx']}** ({sent['original_duration_seconds']:.1f}s): {sent['num_repeats']}× repeats ({chunk_type})")
                    
                    # Show file locations if custom output
                    if output_dir:
                        st.info(f"📁 Files saved to: {output_dir.resolve()}")
                    
                except Exception as e:
                    st.error(f"❌ Build failed: {str(e)}")
                    st.code(traceback.format_exc())
                    
                    # Show debug info
                    with st.expander("Debug Information"):
                        st.write("Config:", config)
                        st.write("Manual adjustments:", manual_adj_list)

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
    Dictation Builder v1.0 | Built with Streamlit
</div>
""", unsafe_allow_html=True)

