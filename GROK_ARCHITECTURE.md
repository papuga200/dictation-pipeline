# Grok Alignment Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DICTATION BUILDER                             │
│                     (with Grok AI Alignment)                         │
└─────────────────────────────────────────────────────────────────────┘
```

## Complete Pipeline Flow

```
┌──────────────┐
│ Audio Input  │
│ (MP3/WAV)    │
└──────┬───────┘
       │
       ↓
┌──────────────────────┐
│ AssemblyAI           │  ← Auto-transcription
│ Transcription        │
└──────┬───────────────┘
       │
       ↓
┌──────────────────────┐
│ Words JSON           │
│ ┌────────────────┐   │
│ │ text: "Hello"  │   │
│ │ start: 0       │   │
│ │ end: 500       │   │
│ └────────────────┘   │
└──────┬───────────────┘
       │
       ├────────────────────────────────┐
       │                                │
       ↓                                ↓
┌──────────────────┐         ┌──────────────────┐
│ Fuzzy Matching   │         │ Grok AI          │  ← NEW!
│ Alignment        │   OR    │ Alignment        │
│                  │         │                  │
│ • Fast           │         │ • AI-Powered     │
│ • Offline        │         │ • Context-Aware  │
│ • Free           │         │ • High Accuracy  │
└──────┬───────────┘         └──────┬───────────┘
       │                            │
       └───────────┬────────────────┘
                   ↓
       ┌──────────────────────┐
       │ Aligned Timestamps   │
       │ ┌────────────────┐   │
       │ │ sentence: ...  │   │
       │ │ start_ms: 220  │   │
       │ │ end_ms: 4260   │   │
       │ └────────────────┘   │
       └──────┬───────────────┘
              │
              ↓
       ┌──────────────────────┐
       │ Audio Builder        │
       │ • Tempo adjust       │
       │ • Repetition         │
       │ • Pauses             │
       └──────┬───────────────┘
              │
              ↓
       ┌──────────────────────┐
       │ Dictation Audio      │
       │ (Final Output)       │
       └──────────────────────┘
```

## Grok Alignment Detailed Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GROK ALIGNER                                 │
└─────────────────────────────────────────────────────────────────────┘

INPUT:
┌──────────────────┐           ┌──────────────────┐
│ Canonical Text   │           │ Transcription    │
│                  │           │ Words JSON       │
│ "As a boy,       │           │ [{text, start,   │
│  Robert Ballard  │           │   end}, ...]     │
│  liked to read   │           │                  │
│  about..."       │           │                  │
└────────┬─────────┘           └────────┬─────────┘
         │                              │
         ↓                              │
┌─────────────────────┐                 │
│ Sentence            │                 │
│ Segmentation        │                 │
│ (NLTK)              │                 │
└────────┬────────────┘                 │
         │                              │
         ↓                              │
┌─────────────────────┐                 │
│ Sentence List       │                 │
│ [s1, s2, ..., s21]  │                 │
└────────┬────────────┘                 │
         │                              │
         └──────────────┬───────────────┘
                        │
                        ↓
         ┌──────────────────────────┐
         │   PARALLEL PROCESSOR     │
         │   (ThreadPoolExecutor)   │
         └──────────────────────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
         ↓              ↓              ↓
    ┌────────┐    ┌────────┐    ┌────────┐
    │Worker 1│    │Worker 2│    │Worker N│
    │        │    │        │    │        │
    │ s1 → API│   │ s2 → API│   │ sN → API│
    │ s6 → API│   │ s7 → API│   │        │
    │ ...    │    │ ...    │    │ ...    │
    └────┬───┘    └────┬───┘    └────┬───┘
         │             │             │
         └─────────────┼─────────────┘
                       │
                       ↓
         ┌─────────────────────────┐
         │   GROK API (xAI)        │
         │   grok-2-1212           │
         │                         │
         │   Natural Language      │
         │   Understanding         │
         └──────────┬──────────────┘
                    │
                    ↓
         ┌─────────────────────────┐
         │   Response Collection   │
         │   • Retry on failure    │
         │   • Parse JSON          │
         │   • Extract timestamps  │
         └──────────┬──────────────┘
                    │
                    ↓
         ┌─────────────────────────┐
         │   Result Aggregation    │
         │   • Merge all results   │
         │   • Generate report     │
         │   • Calculate stats     │
         └──────────┬──────────────┘
                    │
                    ↓
OUTPUT:
┌──────────────────────────────────────┐
│ Aligned Spans + Report               │
│                                      │
│ spans: [(start_ms, end_ms), ...]    │
│                                      │
│ report: {                            │
│   global: {aligned, unaligned, ...}  │
│   details: [...]                     │
│ }                                    │
└──────────────────────────────────────┘
```

## Grok API Request Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                    SINGLE SENTENCE PROCESSING                     │
└──────────────────────────────────────────────────────────────────┘

1. PREPARE PROMPT
┌─────────────────────────────────────────────────────────────────┐
│ System Message:                                                  │
│ "You are a precise timestamp alignment assistant..."             │
│                                                                  │
│ User Message:                                                    │
│ "Given this transcription:                                       │
│  {words: [{text: 'As', start: 320, end: 440}, ...]}             │
│                                                                  │
│  Find timestamps for:                                            │
│  'As a boy, Robert Ballard liked to read about shipwrecks.'     │
│                                                                  │
│  Respond with JSON:                                              │
│  {start_ms: <value>, end_ms: <value>, confidence: <0-1>}"       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
2. API REQUEST
┌─────────────────────────────────────────────────────────────────┐
│ POST https://api.x.ai/v1/chat/completions                       │
│                                                                  │
│ Headers:                                                         │
│   Authorization: Bearer <XAI_API_KEY>                            │
│   Content-Type: application/json                                │
│                                                                  │
│ Body:                                                            │
│   model: "grok-2-1212"                                           │
│   messages: [system, user]                                       │
│   temperature: 0.1                                               │
│   max_tokens: 200                                                │
│   response_format: {type: "json_object"}                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
3. GROK PROCESSING
┌─────────────────────────────────────────────────────────────────┐
│ Grok AI Analysis:                                                │
│ • Parse transcription structure                                  │
│ • Understand sentence meaning                                    │
│ • Match semantically with words                                  │
│ • Find first word (start time)                                   │
│ • Find last word (end time)                                      │
│ • Calculate confidence                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
4. API RESPONSE
┌─────────────────────────────────────────────────────────────────┐
│ {                                                                │
│   "id": "chatcmpl-...",                                          │
│   "choices": [{                                                  │
│     "message": {                                                 │
│       "content": "{                                              │
│         \"start_ms\": 220,                                       │
│         \"end_ms\": 4260,                                        │
│         \"confidence\": 0.98                                     │
│       }"                                                         │
│     }                                                            │
│   }]                                                             │
│ }                                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
5. PARSE & VALIDATE
┌─────────────────────────────────────────────────────────────────┐
│ • Parse JSON response                                            │
│ • Extract start_ms, end_ms, confidence                           │
│ • Validate values (non-negative, end > start)                    │
│ • Add padding (default: 100ms)                                   │
│ • Return (start_ms, end_ms, confidence)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
6. RETRY LOGIC (if needed)
┌─────────────────────────────────────────────────────────────────┐
│ On failure:                                                      │
│ • Attempt 1: Immediate retry                                     │
│ • Attempt 2: Wait 1s, retry                                      │
│ • Attempt 3: Wait 1s, retry                                      │
│ • All failed: Return None                                        │
└─────────────────────────────────────────────────────────────────┘
```

## Parallel Processing Model

```
TIME ─────────────────────────────────────────────────────────────→

Worker 1:  [──S1──][──S6──][──S11─][──S16─]
Worker 2:    [──S2──][──S7──][──S12─][──S17─]
Worker 3:      [──S3──][──S8──][──S13─][──S18─]
Worker 4:        [──S4──][──S9──][──S14─][──S19─]
Worker 5:          [──S5──][──S10─][──S15─][──S20─]

Legend:
[──SN──] = API call for sentence N (1-3 seconds each)

Without parallel: 21 sentences × 2s = 42 seconds
With 5 workers:   21 sentences / 5 × 2s ≈ 8.4 seconds
Actual (overhead): ~10-15 seconds
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          DATA FLOW                               │
└─────────────────────────────────────────────────────────────────┘

INPUT DATA:
┌────────────────────┐
│ canonical.txt      │
├────────────────────┤
│ "As a boy, Robert  │
│  Ballard liked to  │
│  read about ship-  │
│  wrecks. He read   │
│  a lot..."         │
└──────┬─────────────┘
       │
       ↓ segment_sentences()
       │
┌──────┴─────────────┐
│ sentences: list    │
├────────────────────┤
│ [                  │
│   "As a boy, ...", │
│   "He read a ...", │
│   ...              │
│ ]                  │
└──────┬─────────────┘
       │
       ↓
       │
┌──────┴─────────────┐    ┌────────────────────┐
│ Grok Aligner       │◄───│ transcription.json │
│                    │    ├────────────────────┤
│ Config:            │    │ words: [           │
│ • workers: 5       │    │   {text, start,    │
│ • temp: 0.1        │    │    end, conf},     │
│ • retries: 3       │    │   ...              │
│                    │    │ ]                  │
└──────┬─────────────┘    └────────────────────┘
       │
       ↓ align_sentences()
       │
┌──────┴──────────────────────────────────────┐
│ ThreadPoolExecutor                           │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐         │
│ │Worker 1 │ │Worker 2 │ │Worker N │         │
│ │         │ │         │ │         │         │
│ │ • Build │ │ • Build │ │ • Build │         │
│ │   prompt│ │   prompt│ │   prompt│         │
│ │ • Call  │ │ • Call  │ │ • Call  │         │
│ │   API   │ │   API   │ │   API   │         │
│ │ • Parse │ │ • Parse │ │ • Parse │         │
│ │ • Retry │ │ • Retry │ │ • Retry │         │
│ └────┬────┘ └────┬────┘ └────┬────┘         │
│      │           │           │              │
│      └───────────┴───────────┴──────────────┤
│                  │                          │
│                  ↓                          │
│         as_completed()                      │
└─────────────────┬───────────────────────────┘
                  │
                  ↓
OUTPUT DATA:
┌─────────────────┴───────────────────────────┐
│ spans: List[Optional[Tuple[int, int]]]     │
├─────────────────────────────────────────────┤
│ [                                           │
│   (220, 4260),    # Sentence 1              │
│   (4700, 7140),   # Sentence 2              │
│   (8060, 12260),  # Sentence 3              │
│   None,           # Sentence 4 (failed)     │
│   ...                                       │
│ ]                                           │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────┴───────────────────────────┐
│ report: Dict                                │
├─────────────────────────────────────────────┤
│ {                                           │
│   "global": {                               │
│     "num_sentences": 21,                    │
│     "aligned": 19,                          │
│     "unaligned": 2,                         │
│     "warnings": 3                           │
│   },                                        │
│   "details": [                              │
│     {idx: 4, status: "failed", ...},        │
│     {idx: 7, status: "warning", ...}        │
│   ]                                         │
│ }                                           │
└─────────────────────────────────────────────┘
```

## Component Responsibilities

```
┌─────────────────────────────────────────────────────────────────┐
│                      COMPONENT DIAGRAM                           │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────┐
│   GrokAlignerConfig      │
├──────────────────────────┤
│ Responsibilities:        │
│ • Store API settings     │
│ • Store processing opts  │
│ • Provide defaults       │
│                          │
│ Properties:              │
│ • api_key               │
│ • base_url              │
│ • model                 │
│ • temperature           │
│ • max_workers           │
│ • max_retries           │
└────────────┬─────────────┘
             │
             ↓
┌──────────────────────────┐
│   GrokAligner            │
├──────────────────────────┤
│ Responsibilities:        │
│ • Coordinate alignment   │
│ • Manage parallel proc   │
│ • Handle OpenAI client   │
│ • Generate reports       │
│                          │
│ Methods:                 │
│ • align_sentences()      │
│ • _align_single()        │
│ • _create_prompt()       │
│ • _prepare_json()        │
└────────────┬─────────────┘
             │
             ↓
┌──────────────────────────┐
│   OpenAI Client          │
├──────────────────────────┤
│ Responsibilities:        │
│ • HTTP communication     │
│ • Request formatting     │
│ • Response parsing       │
│ • Error handling         │
│                          │
│ Provided by:             │
│ • openai library         │
└────────────┬─────────────┘
             │
             ↓
┌──────────────────────────┐
│   xAI Grok API           │
├──────────────────────────┤
│ Responsibilities:        │
│ • NLP understanding      │
│ • Timestamp matching     │
│ • Confidence scoring     │
│ • JSON response          │
│                          │
│ Endpoint:                │
│ • api.x.ai/v1            │
└──────────────────────────┘
```

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     ERROR HANDLING                               │
└─────────────────────────────────────────────────────────────────┘

API CALL
   │
   ↓
┌────────────────┐
│ Try API call   │
└───┬────────────┘
    │
    ├─ SUCCESS ──→ Parse JSON ──→ Extract data ──→ RETURN result
    │
    ├─ JSON Error ──┐
    │               │
    ├─ Timeout ─────┤
    │               │
    ├─ Rate Limit ──┤
    │               ↓
    ├─ Network ─────→ Check retry count
    │                    │
    │                    ├─ < max_retries ──→ Wait & RETRY
    │                    │
    │                    └─ >= max_retries ──→ Log error
    │                                          RETURN None
    │
    └─ Other Error ──→ Log error ──→ RETURN None

RESULT COLLECTION
   │
   ↓
Check each sentence result
   │
   ├─ Has span ──→ Add to aligned count
   │               Add span to output
   │
   └─ No span ───→ Add to unaligned count
                   Add error to report
                   Set span = None
```

## Configuration & Tuning

```
┌─────────────────────────────────────────────────────────────────┐
│                  CONFIGURATION OPTIONS                           │
└─────────────────────────────────────────────────────────────────┘

┌───────────────────┬─────────────┬──────────────────────────────┐
│ Parameter         │ Default     │ Effect                       │
├───────────────────┼─────────────┼──────────────────────────────┤
│ max_workers       │ 5           │ Parallel API calls           │
│                   │             │ ↑ = faster, more $$         │
│                   │             │ ↓ = slower, less $$         │
├───────────────────┼─────────────┼──────────────────────────────┤
│ temperature       │ 0.1         │ Response variation           │
│                   │             │ ↑ = more creative           │
│                   │             │ ↓ = more consistent         │
├───────────────────┼─────────────┼──────────────────────────────┤
│ max_retries       │ 3           │ Failure tolerance            │
│                   │             │ ↑ = more robust             │
│                   │             │ ↓ = fail faster             │
├───────────────────┼─────────────┼──────────────────────────────┤
│ timeout           │ 30          │ Request timeout (seconds)    │
│                   │             │ ↑ = wait longer             │
│                   │             │ ↓ = fail faster             │
├───────────────────┼─────────────┼──────────────────────────────┤
│ pad_ms            │ 100         │ Timestamp padding (ms)       │
│                   │             │ ↑ = more buffer             │
│                   │             │ ↓ = tighter fit             │
└───────────────────┴─────────────┴──────────────────────────────┘
```

## File Organization

```
project/
│
├── pipeline/
│   ├── __init__.py
│   ├── alignment.py           ← Existing fuzzy matching
│   ├── grok_alignment.py      ← NEW: Grok alignment
│   ├── segmentation.py
│   ├── audio.py
│   └── ...
│
├── demo_grok_alignment.py     ← Demo script
├── compare_alignment_methods.py ← Comparison tool
├── setup_grok.py              ← Setup wizard
│
├── GROK_ALIGNMENT_README.md   ← Main docs
├── GROK_ALIGNMENT_GUIDE.md    ← Detailed guide
├── GROK_QUICKSTART.md         ← Quick reference
├── GROK_IMPLEMENTATION_SUMMARY.md ← This summary
├── GROK_ARCHITECTURE.md       ← Architecture (this file)
│
└── requirements.txt           ← Updated with openai
```

---

This architecture provides a scalable, maintainable, and production-ready solution for AI-powered text-to-timestamp alignment using xAI's Grok API.

