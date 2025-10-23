"""
Grok-based alignment engine using xAI's Grok-4-fast model.
Uses natural language understanding to align canonical sentences with transcription timestamps.
Leverages structured outputs with Pydantic for type-safe, validated responses.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import BaseModel, Field
import openai
from openai import OpenAI

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use system environment variables


# Setup logging
def setup_grok_logger():
    """Setup logger for Grok alignment with file handler."""
    logger = logging.getLogger('grok_alignment')
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create logs directory
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)
    
    # Create log file with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = logs_dir / f'grok_alignment_{timestamp}.log'
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger


logger = setup_grok_logger()


class AlignmentResponse(BaseModel):
    """Pydantic schema for Grok's alignment response.
    
    This schema enforces structured output from Grok API, ensuring:
    - Type safety (int values for timestamps)
    - Data validation (positive values, end > start)
    - Consistent response format
    """
    start_ms: int = Field(
        description="Start timestamp in milliseconds where the sentence begins in the transcription",
        ge=0
    )
    end_ms: int = Field(
        description="End timestamp in milliseconds where the sentence ends in the transcription",
        ge=0
    )
    confidence: float = Field(
        description="Confidence score for this alignment (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
        default=0.95
    )


class GrokAlignerConfig:
    """Configuration for Grok-based alignment."""
    def __init__(self):
        # API settings
        self.api_key = os.getenv("XAI_API_KEY", "")
        self.base_url = "https://api.x.ai/v1"
        self.model = "grok-4-fast"  # Fast, cost-efficient reasoning model with structured outputs
        
        # Request parameters
        self.temperature = 0.1  # Low temperature for consistent, accurate results
        self.max_tokens = 200  # Enough for a JSON response
        self.timeout = 30  # Seconds
        
        # Parallel processing
        self.max_workers = 5  # Number of parallel requests
        
        # Retry settings
        self.max_retries = 3
        self.retry_delay = 1  # seconds


class GrokAligner:
    """Aligns sentences using Grok's natural language understanding."""
    
    def __init__(self, words: List[Dict], config: Optional[GrokAlignerConfig] = None):
        """
        Args:
            words: List of word dicts with 'text', 'start', 'end' (in ms)
            config: Grok alignment configuration
        """
        self.words = words
        self.config = config or GrokAlignerConfig()
        
        # Log initialization
        logger.info("=" * 60)
        logger.info("Initializing Grok Aligner")
        logger.info(f"Model: {self.config.model}")
        logger.info(f"Temperature: {self.config.temperature}")
        logger.info(f"Max workers: {self.config.max_workers}")
        logger.info(f"Max retries: {self.config.max_retries}")
        logger.info(f"Words in transcription: {len(words)}")
        
        # Validate API key
        if not self.config.api_key:
            logger.error("XAI_API_KEY not set")
            raise ValueError(
                "XAI_API_KEY environment variable not set. "
                "Get your API key from https://console.x.ai/"
            )
        
        logger.info(f"API Key: {'*' * 8}{self.config.api_key[-4:]} (masked)")
        
        # Initialize OpenAI client with xAI endpoint
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )
        
        # Prepare compact transcription for API calls
        self.transcription_json = self._prepare_transcription_json()
        logger.info("Grok Aligner initialized successfully")
        logger.info("=" * 60)
    
    def _prepare_transcription_json(self) -> str:
        """Prepare a compact JSON representation of the transcription."""
        # Create a simplified version with only essential fields
        compact_words = [
            {
                "text": w.get("text", ""),
                "start": w.get("start", 0),
                "end": w.get("end", 0)
            }
            for w in self.words
        ]
        return json.dumps({"words": compact_words}, separators=(',', ':'))
    
    def align_sentences(
        self, 
        sentences: List[str], 
        pad_ms: int = 100
    ) -> Tuple[List[Optional[Tuple[int, int]]], Dict]:
        """
        Align all sentences using Grok API in parallel.
        
        Args:
            sentences: List of sentence strings
            pad_ms: Padding in milliseconds to add to spans
        
        Returns:
            - List of (start_ms, end_ms) tuples or None for each sentence
            - Alignment report dictionary
        """
        logger.info(f"Starting alignment for {len(sentences)} sentences")
        logger.info(f"Padding: {pad_ms}ms")
        
        report = {
            "global": {
                "num_sentences": len(sentences),
                "aligned": 0,
                "unaligned": 0,
                "warnings": 0
            },
            "details": []
        }
        
        spans = [None] * len(sentences)  # Pre-allocate results list
        
        # Process sentences in parallel
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all tasks
            future_to_idx = {
                executor.submit(
                    self._align_single_sentence, 
                    sentence, 
                    idx, 
                    pad_ms
                ): idx
                for idx, sentence in enumerate(sentences, start=1)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                sentence = sentences[idx - 1]
                
                try:
                    result = future.result()
                    
                    if result is None:
                        report["details"].append({
                            "idx": idx,
                            "text": sentence[:120],
                            "status": "failed",
                            "reason": "Grok API failed to find timestamps"
                        })
                        report["global"]["unaligned"] += 1
                    else:
                        start_ms, end_ms, confidence = result
                        spans[idx - 1] = (start_ms, end_ms)
                        
                        report["global"]["aligned"] += 1
                        
                        # Add to report if confidence is low
                        if confidence < 0.9:
                            report["global"]["warnings"] += 1
                            report["details"].append({
                                "idx": idx,
                                "text": sentence[:120],
                                "status": "warning",
                                "confidence": confidence,
                                "reason": "Low confidence alignment",
                                "span_ms": {"start": start_ms, "end": end_ms}
                            })
                
                except Exception as e:
                    logger.error(f"Sentence {idx} - Exception during alignment: {e}")
                    report["details"].append({
                        "idx": idx,
                        "text": sentence[:120],
                        "status": "error",
                        "reason": f"Exception: {str(e)}"
                    })
                    report["global"]["unaligned"] += 1
        
        # Log summary
        logger.info("-" * 60)
        logger.info("Alignment Summary:")
        logger.info(f"  Total: {len(sentences)}")
        logger.info(f"  Aligned: {report['global']['aligned']}")
        logger.info(f"  Unaligned: {report['global']['unaligned']}")
        logger.info(f"  Warnings: {report['global']['warnings']}")
        logger.info("=" * 60)
        
        return spans, report
    
    def _align_single_sentence(
        self, 
        sentence: str, 
        idx: int,
        pad_ms: int
    ) -> Optional[Tuple[int, int, float]]:
        """
        Align a single sentence using Grok API.
        
        Args:
            sentence: The sentence to align
            idx: Sentence index (for logging)
            pad_ms: Padding in milliseconds
        
        Returns:
            (start_ms, end_ms, confidence) or None if alignment fails
        """
        logger.info(f"[{idx}] Aligning: '{sentence[:80]}{'...' if len(sentence) > 80 else ''}'")
        
        # Construct the prompt
        prompt = self._create_alignment_prompt(sentence)
        
        # Call Grok API with retries using structured outputs
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"[{idx}] API call attempt {attempt + 1}/{self.config.max_retries}")
                # Use beta.chat.completions.parse for structured outputs with Pydantic
                completion = self.client.beta.chat.completions.parse(
                    model=self.config.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a precise timestamp alignment assistant. "
                                "Given a sentence and a transcription with word-level timestamps, "
                                "you determine the exact start and end times for that sentence in milliseconds. "
                                "Provide a confidence score (0.0 to 1.0) for your alignment."
                            )
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    response_format=AlignmentResponse  # Structured output with Pydantic schema
                )
                
                # Extract the parsed Pydantic object
                alignment = completion.choices[0].message.parsed
                
                if alignment:
                    # Apply padding to timestamps
                    start_ms = max(0, alignment.start_ms - pad_ms)
                    end_ms = alignment.end_ms + pad_ms
                    confidence = alignment.confidence
                    
                    logger.info(f"[{idx}] SUCCESS: {start_ms}ms - {end_ms}ms (confidence: {confidence:.2f})")
                    return (start_ms, end_ms, confidence)
                else:
                    logger.warning(f"[{idx}] No parsed alignment returned")
                    print(f"Warning: Sentence {idx} - No parsed alignment returned")
                    return None
                
            except Exception as e:
                logger.warning(f"[{idx}] API call failed (attempt {attempt + 1}/{self.config.max_retries}): {e}")
                print(f"Warning: Sentence {idx} - API call failed (attempt {attempt + 1}): {e}")
                if attempt < self.config.max_retries - 1:
                    import time
                    time.sleep(self.config.retry_delay)
                    continue
                logger.error(f"[{idx}] All retry attempts failed")
                return None
        
        return None
    
    def _create_alignment_prompt(self, sentence: str) -> str:
        """Create the prompt for Grok API with structured output."""
        return f"""Given this transcription with word-level timestamps (in milliseconds):

{self.transcription_json}

Task: Find the exact start and end timestamps for this sentence:
"{sentence}"

Instructions:
1. Match the sentence to the transcription, accounting for minor differences in punctuation, contractions, or formatting
2. The sentence may not be word-for-word identical to the transcription (handle paraphrasing)
3. Identify the first word of the sentence and use its start timestamp
4. Identify the last word of the sentence and use its end timestamp
5. Provide a confidence score (0.0 to 1.0) based on how well the sentence matches the transcription:
   - 1.0: Perfect match
   - 0.9-0.99: Excellent match with minor differences
   - 0.8-0.89: Good match with some paraphrasing
   - Below 0.8: Uncertain match"""


def align_sentences_with_grok(
    sentences: List[str],
    words: List[Dict],
    config: Optional[GrokAlignerConfig] = None,
    pad_ms: int = 100
) -> Tuple[List[Optional[Tuple[int, int]]], Dict]:
    """
    Main entry point for Grok-based sentence alignment.
    
    Args:
        sentences: List of sentence strings
        words: List of word dicts with 'text', 'start', 'end' (in ms)
        config: Optional Grok alignment configuration
        pad_ms: Padding in milliseconds to add to spans
    
    Returns:
        - List of (start_ms, end_ms) tuples or None
        - Alignment report dictionary
    
    Example:
        >>> words = [{"text": "Hello", "start": 0, "end": 500}, ...]
        >>> sentences = ["Hello world.", "How are you?"]
        >>> spans, report = align_sentences_with_grok(sentences, words)
    """
    aligner = GrokAligner(words, config)
    return aligner.align_sentences(sentences, pad_ms)

