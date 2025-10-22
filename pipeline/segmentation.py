"""
Sentence segmentation with robust abbreviation handling.
"""

import re
import nltk
from typing import List
from .normalize import ABBREVIATIONS, strip_embedded_quotes


def ensure_nltk_data():
    """Download required NLTK data if not present."""
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    
    try:
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        nltk.download('punkt_tab', quiet=True)


def segment_sentences(text: str, strip_quotes: bool = True) -> List[str]:
    """
    Segment text into sentences using NLTK with custom abbreviation handling.
    
    Args:
        text: Input text to segment
        strip_quotes: If True, remove embedded quotation marks from sentences
    
    Returns:
        List of sentence strings
    """
    ensure_nltk_data()
    
    # Strip embedded quotes if requested (per Q4)
    if strip_quotes:
        text = strip_embedded_quotes(text)
    
    # Preprocess: handle ellipses
    text = text.replace('...', ' <ELLIPSIS> ')
    
    # Use NLTK sentence tokenizer
    try:
        sentences = nltk.sent_tokenize(text)
    except Exception as e:
        # Fallback to simple split on periods
        sentences = re.split(r'[.!?]+', text)
    
    # Post-process
    result = []
    for sent in sentences:
        # Restore ellipses
        sent = sent.replace('<ELLIPSIS>', '...')
        
        # Clean up whitespace
        sent = ' '.join(sent.split())
        sent = sent.strip()
        
        if sent:
            # Ensure sentence ends with punctuation
            if sent and sent[-1] not in '.!?':
                sent += '.'
            result.append(sent)
    
    return result


def is_sentence_boundary(text: str, pos: int) -> bool:
    """
    Check if position in text is a true sentence boundary.
    Handles abbreviations like Mr., Dr., U.S., etc.
    """
    if pos >= len(text) - 1:
        return True
    
    # Get text before the period
    before = text[:pos].lower().strip().split()
    if not before:
        return True
    
    last_word = before[-1].rstrip('.')
    
    # Check if it's a known abbreviation
    if last_word in ABBREVIATIONS:
        return False
    
    # Check if it's a single capital letter (initials)
    if len(last_word) == 1 and last_word.isupper():
        return False
    
    # Check if next character is lowercase (likely not a new sentence)
    if pos + 1 < len(text) and text[pos + 1].islower():
        return False
    
    return True


def split_sentences_advanced(text: str) -> List[str]:
    """
    Advanced sentence splitting with manual boundary detection.
    Fallback if NLTK fails.
    """
    # Find all potential sentence boundaries
    boundaries = []
    for match in re.finditer(r'[.!?]', text):
        pos = match.start()
        if is_sentence_boundary(text, pos):
            boundaries.append(pos + 1)
    
    # Split at boundaries
    sentences = []
    start = 0
    for end in boundaries:
        sent = text[start:end].strip()
        if sent:
            sentences.append(sent)
        start = end
    
    # Don't forget the last part
    if start < len(text):
        sent = text[start:].strip()
        if sent:
            sentences.append(sent)
    
    return sentences

