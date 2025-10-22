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

from pipeline.builder import DictationBuilder
from pipeline.segmentation import segment_sentences
from pipeline.normalize import strip_embedded_quotes
from pipeline.audio import get_audio_info


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


# Header
st.title("🎧 Dictation Builder")
st.markdown("""
Build dictation audio from source recordings with word-level timestamps.
- Adjusts tempo to 0.92× (pitch preserved)
- Repeats each sentence 3× with configurable pauses
- Supports manual time adjustment for sentence alignment
""")

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    tempo = st.slider("Tempo", min_value=0.5, max_value=2.0, value=0.92, step=0.01, 
                      help="Playback speed multiplier (1.0 = normal, 0.92 = 92% speed)")
    repeats = st.number_input("Repeats per sentence", min_value=1, max_value=5, value=3, step=1)
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
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Canonical Text")
        canonical_text = st.text_area(
            "Paste or type the exact text students should transcribe",
            height=300,
            help="This is the reference text. Embedded quotes will be stripped for alignment."
        )
    
    with col2:
        st.subheader("Supporting Files")
        
        words_file = st.file_uploader(
            "Word Timestamps JSON",
            type=['json'],
            help="JSON file with word-level timestamps (supports AssemblyAI format)"
        )
        
        audio_file = st.file_uploader(
            "Source Audio",
            type=['wav', 'mp3', 'm4a', 'flac'],
            help="Original audio recording"
        )
    
    if canonical_text and words_file and audio_file:
        st.divider()
        
        # Preview button
        if st.button("🔍 Preview Sentences & Load for Adjustment", type="primary"):
            with st.spinner("Analyzing..."):
                try:
                    # Segment sentences
                    sentences = segment_sentences(canonical_text, strip_quotes=True)
                    st.session_state.sentences = sentences
                    
                    # Load words JSON
                    words_data = json.loads(words_file.read())
                    st.session_state.words_data = words_data
                    words_file.seek(0)  # Reset for later use
                    
                    # Get audio duration
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as tmp:
                        tmp.write(audio_file.read())
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
        
        st.divider()
        
        # Run automatic alignment
        if st.button("🔄 Run Automatic Alignment", type="primary"):
            with st.spinner("Aligning sentences to word timestamps..."):
                try:
                    from pipeline.alignment import align_sentences_to_words, AlignmentConfig
                    
                    words = st.session_state.words_data['words']
                    
                    config = AlignmentConfig()
                    config.min_accept = min_accept
                    config.warn_accept = warn_accept
                    config.window_tokens = window_tokens
                    
                    spans, report = align_sentences_to_words(
                        st.session_state.sentences, words, config, pad_ms
                    )
                    
                    st.session_state.alignment_results = {
                        'spans': spans,
                        'report': report
                    }
                    
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
                    
                    # Time adjustment row
                    time_cols = st.columns([2, 2, 1])
                    
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
        st.markdown(f"""
        **Ready to build:**
        - {len(st.session_state.sentences)} sentences
        - {len(st.session_state.manual_adjustments)} manual adjustments
        - Tempo: {tempo}× | Repeats: {repeats}× | Pauses: {pause_ms}ms
        """)
        
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
                        audio_tmp.write_bytes(audio_file.getvalue())
                        
                        # Save words JSON
                        words_tmp = tmp_path / 'words.json'
                        words_tmp.write_bytes(words_file.getvalue())
                        
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
                    
                    # Audio player
                    st.subheader("🎵 Preview Dictation Audio")
                    st.audio(audio_bytes, format='audio/wav')
                    
                    # Download buttons
                    st.subheader("📥 Download Files")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.download_button(
                            "⬇️ Download Audio (WAV)",
                            data=audio_bytes,
                            file_name="dictation_final.wav",
                            mime="audio/wav"
                        )
                    
                    with col2:
                        st.download_button(
                            "⬇️ Download Manifest",
                            data=manifest_bytes,
                            file_name="final_manifest.json",
                            mime="application/json"
                        )
                    
                    with col3:
                        st.download_button(
                            "⬇️ Download Report",
                            data=report_bytes,
                            file_name="alignment_report.json",
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

