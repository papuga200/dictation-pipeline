"""
Fuzzy alignment engine with anchored, monotonic matching.
Implements composite scoring with fallback strategies.
"""

from typing import List, Dict, Tuple, Optional, Any
from rapidfuzz import fuzz
import re
from .normalize import (
    normalize_token, tokenize, generate_contraction_variants,
    compute_token_idf, extract_anchors, are_numbers_equivalent,
    normalize_unit
)


# Stopwords for token weighting
STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
    'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
    'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
}


class AlignmentConfig:
    """Configuration for alignment parameters."""
    def __init__(self):
        # Window parameters
        self.window_tokens = 4000
        self.elastic_gap = 10
        
        # Scoring thresholds
        self.min_accept = 0.85
        self.warn_accept = 0.78
        self.token_ratio_cutoff = 92
        
        # Coverage requirements
        self.coverage_min = 0.80
        self.small_sentence_coverage_min = 0.67
        
        # Scoring weights
        self.weight_token_sim = 0.50
        self.weight_coverage = 0.25
        self.weight_gap_penalty = 0.20
        self.weight_anchor_bonus = 0.08
        self.weight_bigram_bonus = 0.05
        
        # Fallback parameters
        self.fallback_expand_window = 1000
        self.fallback_elastic_gap = 18
        self.fallback_token_ratio = 88


class CandidateSpan:
    """Represents a candidate alignment span with scoring."""
    def __init__(self, start_idx: int, end_idx: int):
        self.start_idx = start_idx
        self.end_idx = end_idx
        self.token_sim = 0.0
        self.coverage = 0.0
        self.gap_penalty = 0.0
        self.anchor_bonus = 0.0
        self.bigram_bonus = 0.0
        self.total_score = 0.0
        self.matched_tokens = []
        self.aligned_pairs = []
    
    def compute_total_score(self, config: AlignmentConfig):
        """Compute composite score."""
        self.total_score = (
            config.weight_token_sim * self.token_sim +
            config.weight_coverage * self.coverage -
            config.weight_gap_penalty * self.gap_penalty +
            config.weight_anchor_bonus * self.anchor_bonus +
            config.weight_bigram_bonus * self.bigram_bonus
        )
        return self.total_score


class SentenceAligner:
    """Aligns sentences to word-level timestamps using fuzzy matching."""
    
    def __init__(self, words: List[Dict], config: Optional[AlignmentConfig] = None):
        """
        Args:
            words: List of word dicts with 'text', 'start', 'end' (in ms)
            config: Alignment configuration
        """
        self.words = words
        self.config = config or AlignmentConfig()
        
        # Normalize word tokens
        self.normalized_words = [normalize_token(w.get('text', '')) for w in words]
        
        # Compute IDF scores for all words
        all_tokens = []
        for w in self.normalized_words:
            all_tokens.extend(tokenize(w))
        self.idf_scores = compute_token_idf(all_tokens, all_tokens)
    
    def align_sentences(self, sentences: List[str], pad_ms: int = 100) -> Tuple[List[Optional[Tuple[int, int]]], Dict]:
        """
        Align all sentences to word timestamps.
        
        Returns:
            - List of (start_ms, end_ms) tuples or None for each sentence
            - Alignment report dictionary
        """
        report = {
            "global": {
                "num_sentences": len(sentences),
                "aligned": 0,
                "unaligned": 0,
                "warnings": 0
            },
            "details": []
        }
        
        spans = []
        cursor = 0  # Monotonicity cursor
        
        for idx, sentence in enumerate(sentences, start=1):
            # Tokenize sentence
            sent_tokens = tokenize(sentence)
            
            if not sent_tokens:
                spans.append(None)
                report["details"].append({
                    "idx": idx,
                    "text": sentence[:120],
                    "status": "empty",
                    "reason": "no tokens after normalization"
                })
                report["global"]["unaligned"] += 1
                continue
            
            # Extract anchors
            anchors = extract_anchors(sent_tokens, self.idf_scores)
            
            # Try to align
            result = self._align_single_sentence(
                sent_tokens, anchors, cursor, idx, sentence
            )
            
            if result is None:
                spans.append(None)
                report["details"].append({
                    "idx": idx,
                    "text": sentence[:120],
                    "status": "failed",
                    "score": 0.0,
                    "reason": "no viable span found"
                })
                report["global"]["unaligned"] += 1
            else:
                span, score, status, note = result
                start_idx, end_idx = span
                
                # Convert to milliseconds
                start_ms = max(0, self.words[start_idx]['start'] - pad_ms)
                end_ms = self.words[end_idx]['end'] + pad_ms
                
                spans.append((start_ms, end_ms))
                
                # Update cursor for monotonicity
                cursor = end_idx + 1
                
                # Record in report
                if status == "ok":
                    report["global"]["aligned"] += 1
                elif status == "warning":
                    report["global"]["aligned"] += 1
                    report["global"]["warnings"] += 1
                    report["details"].append({
                        "idx": idx,
                        "text": sentence[:120],
                        "status": "warning",
                        "score": score,
                        "note": note,
                        "span": {"start_idx": start_idx, "end_idx": end_idx}
                    })
                elif status == "fallback":
                    report["global"]["aligned"] += 1
                    report["global"]["warnings"] += 1
                    report["details"].append({
                        "idx": idx,
                        "text": sentence[:120],
                        "status": "fallback",
                        "score": score,
                        "note": note,
                        "span": {"start_idx": start_idx, "end_idx": end_idx}
                    })
        
        return spans, report
    
    def _align_single_sentence(
        self, 
        sent_tokens: List[str], 
        anchors: List[Tuple[int, str]], 
        cursor: int,
        sent_idx: int,
        original_text: str
    ) -> Optional[Tuple[Tuple[int, int], float, str, str]]:
        """
        Align a single sentence to the word stream.
        
        Returns:
            ((start_idx, end_idx), score, status, note) or None
        """
        # Phase 1: Normal search
        result = self._search_for_span(sent_tokens, anchors, cursor, elastic_gap=self.config.elastic_gap)
        
        if result and result[1] >= self.config.min_accept:
            return (result[0], result[1], "ok", "good match")
        
        if result and result[1] >= self.config.warn_accept:
            return (result[0], result[1], "warning", "acceptable but low score")
        
        # Phase 2: Fallback - expand window and relax parameters
        config_fallback = AlignmentConfig()
        config_fallback.window_tokens = self.config.window_tokens + self.config.fallback_expand_window
        config_fallback.elastic_gap = self.config.fallback_elastic_gap
        config_fallback.token_ratio_cutoff = self.config.fallback_token_ratio
        
        old_config = self.config
        self.config = config_fallback
        
        result_fb = self._search_for_span(sent_tokens, anchors, cursor, elastic_gap=config_fallback.elastic_gap)
        
        self.config = old_config
        
        if result_fb and result_fb[1] >= self.config.warn_accept:
            return (result_fb[0], result_fb[1], "fallback", "found with expanded search")
        
        # No viable span found
        return None
    
    def _search_for_span(
        self, 
        sent_tokens: List[str], 
        anchors: List[Tuple[int, str]], 
        cursor: int,
        elastic_gap: int
    ) -> Optional[Tuple[Tuple[int, int], float]]:
        """
        Search for best matching span in word stream.
        
        Returns:
            ((start_idx, end_idx), score) or None
        """
        search_end = min(len(self.normalized_words), cursor + self.config.window_tokens)
        
        # If we have anchors, narrow search around them
        anchor_positions = []
        if anchors:
            for i in range(cursor, min(cursor + 500, search_end)):
                word_tok = tokenize(self.normalized_words[i])
                for _, anchor_token in anchors:
                    if word_tok and tokenize(anchor_token)[0] in word_tok:
                        anchor_positions.append(i)
                        break
        
        # If anchors found nearby, restrict search
        if anchor_positions:
            search_start = max(cursor, min(anchor_positions) - 50)
            search_end = min(len(self.normalized_words), max(anchor_positions) + 150)
        else:
            search_start = cursor
        
        best_candidate = None
        best_score = -1.0
        
        # Generate candidate spans
        for start_idx in range(search_start, search_end):
            # Quick first-token filter
            first_match = self._tokens_match(sent_tokens[0], self.normalized_words[start_idx])
            
            # Also allow starting on an anchor
            anchor_match = any(
                self._tokens_match(anchor_tok, self.normalized_words[start_idx])
                for _, anchor_tok in anchors
            )
            
            if not (first_match or anchor_match):
                continue
            
            # Try different end points within elastic gap
            expected_end = start_idx + len(sent_tokens) - 1
            for end_idx in range(
                max(start_idx, expected_end - elastic_gap),
                min(search_end, expected_end + elastic_gap + 1)
            ):
                if end_idx >= len(self.normalized_words):
                    break
                
                candidate = self._score_span(sent_tokens, start_idx, end_idx, anchors)
                
                if candidate.total_score > best_score:
                    best_score = candidate.total_score
                    best_candidate = (start_idx, end_idx)
        
        if best_candidate:
            return (best_candidate, best_score)
        
        return None
    
    def _score_span(
        self, 
        sent_tokens: List[str], 
        start_idx: int, 
        end_idx: int,
        anchors: List[Tuple[int, str]]
    ) -> CandidateSpan:
        """Score a candidate span using composite scoring function."""
        candidate = CandidateSpan(start_idx, end_idx)
        
        span_tokens = self.normalized_words[start_idx:end_idx + 1]
        
        # Token similarity with weighted average
        similarities = []
        weights = []
        matched_count = 0
        
        for sent_tok in sent_tokens:
            best_sim = 0.0
            best_match = None
            
            # First try single token matches
            for span_tok in span_tokens:
                if self._tokens_match(sent_tok, span_tok, threshold=self.config.token_ratio_cutoff):
                    sim = fuzz.ratio(sent_tok, span_tok) / 100.0
                    if sim > best_sim:
                        best_sim = sim
                        best_match = span_tok
            
            # If no match and token looks compound (hyphenated or long), try matching consecutive words
            if best_sim < 0.85 and ('-' in sent_tok or len(sent_tok) > 8):
                for j in range(len(span_tokens) - 1):
                    # Try 2-word combination
                    combined2 = span_tokens[j] + span_tokens[j+1]
                    if self._tokens_match(sent_tok.replace('-', ''), combined2):
                        best_sim = 0.95  # High score for compound match
                        matched_count += 1
                        break
                    
                    # Try 3-word combination if available
                    if j < len(span_tokens) - 2:
                        combined3 = span_tokens[j] + span_tokens[j+1] + span_tokens[j+2]
                        if self._tokens_match(sent_tok.replace('-', ''), combined3):
                            best_sim = 0.95
                            matched_count += 1
                            break
            
            if best_sim > 0:
                matched_count += 1
            
            similarities.append(best_sim)
            
            # Weight calculation
            weight = self._get_token_weight(sent_tok)
            weights.append(weight)
        
        # Weighted token similarity
        if sum(weights) > 0:
            candidate.token_sim = sum(s * w for s, w in zip(similarities, weights)) / sum(weights)
        
        # Coverage
        candidate.coverage = matched_count / len(sent_tokens) if sent_tokens else 0.0
        
        # Gap penalty
        expected_len = len(sent_tokens)
        actual_len = len(span_tokens)
        extra_tokens = max(0, actual_len - expected_len)
        missing_tokens = len(sent_tokens) - matched_count
        candidate.gap_penalty = 0.02 * extra_tokens + 0.03 * missing_tokens
        
        # Anchor bonus
        if anchors:
            anchors_found = sum(
                1 for _, anchor_tok in anchors
                if any(self._tokens_match(anchor_tok, span_tok) for span_tok in span_tokens)
            )
            if anchors_found == len(anchors):
                candidate.anchor_bonus = 1.0
            else:
                candidate.anchor_bonus = anchors_found / len(anchors)
        
        # Bigram bonus
        candidate.bigram_bonus = self._compute_bigram_bonus(sent_tokens, span_tokens)
        
        # Compute total
        candidate.compute_total_score(self.config)
        
        return candidate
    
    def _tokens_match(self, tok1: str, tok2: str, threshold: int = None) -> bool:
        """Check if two tokens match using fuzzy similarity."""
        if threshold is None:
            threshold = self.config.token_ratio_cutoff
        
        # Exact match
        if tok1 == tok2:
            return True
        
        # Fuzzy match
        if fuzz.ratio(tok1, tok2) >= threshold:
            return True
        
        # Number equivalence (handles "6000" vs "6,000")
        if are_numbers_equivalent(tok1, tok2):
            return True
        
        # Hyphen variants: "deep-sea" vs "deepsea" vs "deep sea"
        dehyphen1 = tok1.replace('-', '').replace(' ', '')
        dehyphen2 = tok2.replace('-', '').replace(' ', '')
        if dehyphen1 == dehyphen2 and len(dehyphen1) > 3:
            return True
        
        # Unit normalization: "km" vs "kilometers"
        unit1 = normalize_unit(tok1)
        unit2 = normalize_unit(tok2)
        if unit1 == unit2 and unit1 != tok1:  # Changed by normalization
            return True
        
        # Contraction variants
        variants1 = generate_contraction_variants(tok1)
        variants2 = generate_contraction_variants(tok2)
        
        for v1_list in variants1:
            for v2_list in variants2:
                if v1_list == v2_list:
                    return True
        
        return False
    
    def _get_token_weight(self, token: str) -> float:
        """Get weight for token based on type."""
        if token.lower() in STOPWORDS:
            return 0.5
        
        # Numerals and proper nouns
        if re.match(r'\d+', token):
            return 1.25
        
        # Content words
        return 1.0
    
    def _compute_bigram_bonus(self, sent_tokens: List[str], span_tokens: List[str]) -> float:
        """Compute bigram matching bonus."""
        if len(sent_tokens) < 2:
            return 0.0
        
        bigrams = [(sent_tokens[i], sent_tokens[i + 1]) for i in range(len(sent_tokens) - 1)]
        span_str = ' '.join(span_tokens)
        
        matches = 0
        for bg in bigrams[:5]:  # Cap at 5 bigrams
            bg_str = ' '.join(bg)
            if bg_str in span_str:
                matches += 1
        
        return min(0.05, matches * 0.01)


def align_sentences_to_words(
    sentences: List[str],
    words: List[Dict],
    config: Optional[AlignmentConfig] = None,
    pad_ms: int = 100
) -> Tuple[List[Optional[Tuple[int, int]]], Dict]:
    """
    Main entry point for sentence alignment.
    
    Args:
        sentences: List of sentence strings
        words: List of word dicts with 'text', 'start', 'end'
        config: Optional alignment configuration
        pad_ms: Padding in milliseconds to add to spans
    
    Returns:
        - List of (start_ms, end_ms) tuples or None
        - Alignment report dictionary
    """
    aligner = SentenceAligner(words, config)
    return aligner.align_sentences(sentences, pad_ms)

