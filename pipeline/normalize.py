"""
Normalization and tokenization utilities for fuzzy text matching.
Handles Unicode, punctuation, contractions, numbers, and quote stripping.
"""

import re
import unicodedata
from typing import List, Tuple
from num2words import num2words


# Common abbreviations that don't end sentences
ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "vs", "etc", "inc", "ltd", 
    "co", "corp", "dept", "est", "fig", "gen", "gov", "hon", "lt", "maj",
    "messrs", "mlle", "mme", "mt", "no", "op", "ord", "p", "pp", "rev", "st",
    "u.s", "u.s.a", "u.k", "a.m", "p.m", "e.g", "i.e", "viz", "approx", "appt"
}

# Unit abbreviations for normalization
UNIT_ABBREVIATIONS = {
    'km': 'kilometers',
    'kilometer': 'kilometers',
    'kilometres': 'kilometers',
    'kilometre': 'kilometers',
    'm': 'meters',
    'meter': 'meters',
    'metres': 'meters',
    'metre': 'meters',
    'cm': 'centimeters',
    'centimeter': 'centimeters',
    'centimetre': 'centimeters',
    'ft': 'feet',
    'foot': 'feet',
    'mi': 'miles',
    'mile': 'miles',
    'lb': 'pounds',
    'lbs': 'pounds',
    'pound': 'pounds',
    'kg': 'kilograms',
    'kilogram': 'kilograms',
    'g': 'grams',
    'gram': 'grams',
    'oz': 'ounces',
    'ounce': 'ounces',
    'in': 'inches',
    'inch': 'inches',
    'yd': 'yards',
    'yard': 'yards',
    'mph': 'miles per hour',
    'kph': 'kilometers per hour',
    'l': 'liters',
    'liter': 'liters',
    'litre': 'liters',
    'ml': 'milliliters',
}


def strip_embedded_quotes(text: str) -> str:
    """
    Remove quotation marks that are embedded within sentences.
    Example: '"Hello," he said, "world."' -> 'Hello, he said, world.'
    
    Preserves sentence structure while removing quote punctuation.
    """
    # Replace various quote types with nothing
    text = text.replace('"', '')
    text = text.replace('"', '')
    text = text.replace('"', '')
    text = text.replace("'", "")
    text = text.replace("'", "")
    text = text.replace("'", "")
    # Keep straight quotes for now, will handle in normalization
    text = text.replace('"', '')
    
    return text


def normalize_token(token: str) -> str:
    """
    Normalize a single token for fuzzy matching.
    
    Steps:
    1. NFKC Unicode normalization
    2. Lowercase
    3. Curly quotes -> straight quotes
    4. Collapse in-word hyphens (re-enter -> reenter)
    5. Strip punctuation except in-word apostrophes
    6. Clean whitespace
    """
    if not token:
        return ""
    
    # Unicode normalization
    token = unicodedata.normalize("NFKC", token)
    
    # Lowercase
    token = token.lower()
    
    # Normalize quotes
    token = token.replace("'", "'").replace("'", "'")
    token = token.replace(""", '"').replace(""", '"')
    
    # Normalize dashes to spaces or hyphens
    token = token.replace("—", " ").replace("–", "-")
    
    # Collapse in-word hyphens (ice-breaking -> icebreaking)
    token = re.sub(r'(?<=\w)-(?=\w)', '', token)
    
    # Remove dots from acronyms (U.S. -> US)
    if token.isupper() or re.match(r'^[A-Z]\.([A-Z]\.)+$', token):
        token = token.replace('.', '')
    
    # Strip punctuation except in-word apostrophes
    # Keep apostrophes that are between word characters
    token = re.sub(r"[^\w'\s]", " ", token)
    
    # Remove standalone apostrophes
    token = re.sub(r"\s'\s", " ", token)
    token = re.sub(r"^'\s", "", token)
    token = re.sub(r"\s'$", "", token)
    
    # Clean whitespace
    token = re.sub(r'\s+', ' ', token).strip()
    
    return token


def tokenize(text: str) -> List[str]:
    """
    Tokenize normalized text into words.
    Returns list of tokens, preserving apostrophes in contractions.
    """
    normalized = normalize_token(text)
    # Split on whitespace, keep contractions together
    tokens = re.findall(r"\w[\w']*", normalized)
    return [t for t in tokens if t]


def generate_contraction_variants(token: str) -> List[List[str]]:
    """
    Generate dual forms for contractions.
    
    Examples:
        "don't" -> [["don't"], ["do", "not"]]
        "i'm" -> [["i'm"], ["i", "am"]]
        "we'll" -> [["we'll"], ["we", "will"]]
    """
    token = token.lower()
    
    # Common contraction mappings
    contractions = {
        "don't": ["do", "not"],
        "doesnt": ["does", "not"],
        "didn't": ["did", "not"],
        "won't": ["will", "not"],
        "can't": ["can", "not"],
        "cannot": ["can", "not"],
        "couldn't": ["could", "not"],
        "shouldn't": ["should", "not"],
        "wouldn't": ["would", "not"],
        "i'm": ["i", "am"],
        "you're": ["you", "are"],
        "we're": ["we", "are"],
        "they're": ["they", "are"],
        "he's": ["he", "is"],
        "she's": ["she", "is"],
        "it's": ["it", "is"],
        "that's": ["that", "is"],
        "there's": ["there", "is"],
        "here's": ["here", "is"],
        "what's": ["what", "is"],
        "who's": ["who", "is"],
        "i'll": ["i", "will"],
        "you'll": ["you", "will"],
        "we'll": ["we", "will"],
        "they'll": ["they", "will"],
        "he'll": ["he", "will"],
        "she'll": ["she", "will"],
        "i've": ["i", "have"],
        "you've": ["you", "have"],
        "we've": ["we", "have"],
        "they've": ["they", "have"],
        "i'd": ["i", "would"],
        "you'd": ["you", "would"],
        "he'd": ["he", "would"],
        "she'd": ["she", "would"],
        "we'd": ["we", "would"],
        "they'd": ["they", "would"],
    }
    
    # Remove apostrophes for lookup
    lookup = token.replace("'", "")
    
    if lookup in contractions:
        return [[token], contractions[lookup]]
    
    return [[token]]


def number_to_words(num: int) -> List[str]:
    """
    Convert number to various spoken forms.
    
    Examples:
        1912 -> ["1912", "nineteen twelve", "one thousand nine hundred twelve"]
        3 -> ["3", "three", "third"]
        21 -> ["21", "twenty one", "twenty first"]
    """
    variants = [str(num)]
    
    try:
        # Cardinal form
        cardinal = num2words(num, to='cardinal')
        variants.append(cardinal)
        
        # Ordinal form
        ordinal = num2words(num, to='ordinal')
        variants.append(ordinal)
        
        # Special handling for years (1000-2099)
        if 1000 <= num <= 2099:
            century = num // 100
            remainder = num % 100
            if remainder == 0:
                year_form = num2words(century) + " hundred"
            else:
                year_form = num2words(century) + " " + num2words(remainder)
            variants.append(year_form)
    except:
        pass
    
    return variants


def normalize_number_tokens(tokens: List[str]) -> List[str]:
    """
    Normalize number tokens to include word equivalents.
    Returns a list where number tokens are replaced with possible variants.
    """
    result = []
    for token in tokens:
        # Check if token is a number
        clean = re.sub(r'[,\.]', '', token)
        if clean.isdigit():
            num = int(clean)
            variants = number_to_words(num)
            # For now, just use the cardinal form
            result.append(variants[1] if len(variants) > 1 else token)
        else:
            result.append(token)
    return result


def compute_token_idf(tokens: List[str], all_words: List[str]) -> dict:
    """
    Compute inverse document frequency for tokens.
    Higher IDF = more distinctive/rare word.
    """
    from collections import Counter
    word_counts = Counter(all_words)
    total = len(all_words)
    
    idf = {}
    for token in set(tokens):
        freq = word_counts.get(token, 1)
        idf[token] = 1.0 / (1.0 + freq / total)
    
    return idf


def extract_anchors(tokens: List[str], idf_scores: dict, max_anchors: int = 3) -> List[Tuple[int, str]]:
    """
    Extract distinctive anchor tokens from a sentence.
    
    Returns:
        List of (index, token) tuples for anchor words.
    
    Anchors are:
    - Proper nouns (capitalized in original)
    - Numbers
    - Rare/long content words (high IDF, length >= 5)
    - Never stopwords
    """
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
        'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
        'my', 'your', 'his', 'her', 'its', 'our', 'their'
    }
    
    candidates = []
    for idx, token in enumerate(tokens):
        if token.lower() in stopwords:
            continue
        
        # Numbers are always good anchors
        if re.match(r'\d+', token):
            candidates.append((idf_scores.get(token, 1.0) + 1.0, idx, token))
            continue
        
        # Long, rare words
        if len(token) >= 5:
            score = idf_scores.get(token, 0.5)
            candidates.append((score, idx, token))
    
    # Sort by score descending, take top anchors
    candidates.sort(reverse=True)
    anchors = [(idx, token) for _, idx, token in candidates[:max_anchors]]
    anchors.sort(key=lambda x: x[0])  # Re-sort by position
    
    return anchors


def normalize_unit(token: str) -> str:
    """
    Normalize unit abbreviations to full forms.
    Examples: "km" -> "kilometers", "m" -> "meters"
    """
    clean = token.lower().rstrip('s.')
    return UNIT_ABBREVIATIONS.get(clean, token)


def are_numbers_equivalent(num1: str, num2: str) -> bool:
    """
    Check if two strings represent equivalent numbers.
    Handles: "1912" vs "nineteen twelve", "3rd" vs "third", "6000" vs "6,000"
    """
    # Remove commas, spaces from numbers for direct comparison
    clean1 = num1.replace(',', '').replace(' ', '')
    clean2 = num2.replace(',', '').replace(' ', '')
    
    # Direct numeric comparison (handles "6000" vs "6,000")
    if clean1.replace('.', '').isdigit() and clean2.replace('.', '').isdigit():
        try:
            if float(clean1) == float(clean2):
                return True
        except:
            pass
    
    # Try to extract numbers
    digits1 = re.sub(r'[^\d]', '', num1)
    digits2 = re.sub(r'[^\d]', '', num2)
    
    if digits1 and digits2:
        if digits1 == digits2:
            return True
    
    # Try converting to numbers and generating variants
    try:
        if digits1:
            n1 = int(digits1)
            variants1 = set(v.replace(' ', '').replace('-', '').replace(',', '') for v in number_to_words(n1))
        else:
            variants1 = {num1.replace(' ', '').replace('-', '').replace(',', '')}
        
        if digits2:
            n2 = int(digits2)
            variants2 = set(v.replace(' ', '').replace('-', '').replace(',', '') for v in number_to_words(n2))
        else:
            variants2 = {num2.replace(' ', '').replace('-', '').replace(',', '')}
        
        # Check for any overlap
        if variants1 & variants2:
            return True
    except:
        pass
    
    return False

