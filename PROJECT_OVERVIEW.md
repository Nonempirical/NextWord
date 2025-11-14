# NextWord - Comprehensive Project Overview

## Executive Summary

**NextWord** is an interactive educational tool that visualizes how Large Language Models (LLMs) generate text one token at a time. It provides a real-time, step-by-step view into the model's decision-making process, showing not just what token was chosen, but the entire probability distribution over possible next tokens. This makes the "black box" of LLM generation transparent and understandable.

---

## Architecture Overview

The project follows a **client-server architecture** with clear separation of concerns:

```
┌─────────────────┐         HTTP/REST          ┌─────────────────┐
│                 │ ◄─────────────────────────► │                 │
│   Frontend      │      (localhost:3001)      │    Backend      │
│   (React/TS)    │                             │  (FastAPI/Py)   │
│                 │                             │                 │
│  - UI Controls  │                             │  - API Server   │
│  - Visualization│                             │  - Model Adapter│
│  - State Mgmt   │                             │  - LLM Inference│
└─────────────────┘                             └─────────────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │  HuggingFace    │
                                                │  Qwen2.5-1.5B   │
                                                │  (PyTorch)      │
                                                └─────────────────┘
```

---

## Core Components

### 1. Backend (Python/FastAPI)

#### **`main.py` - API Server**
The FastAPI application that serves as the HTTP interface between frontend and model.

**Key Responsibilities:**
- **Request Handling**: Validates incoming requests, enforces business rules (top-k clamping, payload size limits)
- **Orchestration**: Coordinates the adapter methods to process requests
- **Response Formatting**: Structures data according to frozen contracts
- **Error Handling**: Catches exceptions and returns user-friendly error messages
- **CORS Management**: Allows frontend (localhost:3001) to make requests

**Endpoints:**
- `GET /healthz`: Health check returning model name, vocab size, contract version
- `POST /next_dist`: Returns probability distribution without choosing a token
- `POST /step`: Returns distribution AND chooses/appends a token (main endpoint)

**Key Features:**
- Eager model loading at startup (prevents first-request delay)
- Context truncation to 512 tokens (keeps last 512 if exceeded)
- Top-k clamping to [5, 30] range
- Contract versioning via headers (`X-NextTokenLens-Contract: v1`)

#### **`adapter_hf.py` - Model Adapter**
The abstraction layer that wraps HuggingFace models and implements the frozen `Adapter` interface.

**Key Responsibilities:**
- **Model Management**: Loads and manages the Qwen2.5-1.5B model in eval mode
- **Tokenization**: Converts text ↔ token IDs, handles context truncation
- **Inference**: Runs forward passes to get logits (raw model outputs)
- **Probability Computation**: Converts logits to probabilities using numerically stable softmax
- **Token Selection**: Implements argmax and stochastic sampling (with temperature/top-p)
- **Display Formatting**: Converts raw tokens to UI-safe display strings

**Core Methods:**

1. **`tokenize(text: str) -> TokenizeResult`**
   - Converts input text into token IDs and token strings
   - Applies 512-token context cap (keeps last 512 if exceeded)
   - Preserves exact token boundaries (important for leading spaces)

2. **`forward_last(ids: List[int], soften_newline_eot: bool) -> List[float]`**
   - Runs model forward pass on token IDs
   - Returns logits for the LAST position only (vocab-sized array)
   - Optional: Can soften newline/EOS token logits (subtract 2.0) to reduce premature endings

3. **`topk(logits: List[float], k: int) -> List[TokenInfo]`**
   - Converts logits to probabilities using `torch.log_softmax` (numerically stable)
   - Extracts top-k tokens by probability
   - Returns sorted list with: `token_id`, `token_text_raw`, `token_text_display`, `prob`, `logprob`
   - Clamps k to [5, 30]

4. **`choose(logits, mode, k, temperature, top_p) -> ChosenToken`**
   - **Argmax mode**: Picks token with highest probability
   - **Stochastic mode**: 
     - Scales logits by temperature
     - Applies top-p (nucleus) filtering
     - Samples from filtered distribution
   - Returns chosen token with probability, log-probability, and surprisal

**Technical Details:**
- Uses PyTorch tensors throughout computation (only converts to Python at the end)
- Employs `torch.log_softmax` for numerical stability (prevents overflow/underflow)
- Preserves exact token strings using `decode(clean_up_tokenization_spaces=False)`
- Creates display-safe labels for invisible characters (spaces → ␠, newlines → ⏎\n, etc.)

#### **`contracts.py` - Type Definitions**
Frozen type definitions that ensure API stability. These contracts must never change after initial implementation.

**Key Types:**
- `TokenizeResult`: `{ids: List[int], tokens: List[str]}`
- `TokenInfo`: Token with id, text, prob, logprob
- `ChosenToken`: Chosen token with id, text, prob, logprob, surprisal
- `StepRequest/Response`: API request/response structures

---

### 2. Frontend (React/TypeScript)

#### **`src/App.tsx` - Main Application Component**
The React component that manages all UI state and user interactions.

**State Management:**
- `contextText`: User-editable initial context
- `topK`: Number of top candidates to show (5-30)
- `mode`: Selection mode ("argmax" or "stochastic")
- `temperature`: Sampling temperature (0.2-1.5, only for stochastic)
- `topP`: Nucleus sampling threshold (0.7-1.0, only for stochastic)
- `softenNewlineEot`: Hidden dev toggle for logit bias
- `viewMode`: "inspect" (token chips) or "collapsed" (plain text)
- `trace`: Array of `StepRecord` objects (session history)
- `renderedText`: Accumulated generated text (context + all appended tokens)
- `isLoading/isWorking`: Loading states for UX feedback
- `expandedTokenIdx`: Which token chip is currently expanded
- `pulsingTokenIdx`: Which token chip is currently pulsing (animation)

**Key User Flows:**

1. **Initial Setup:**
   - User types initial context in textarea
   - Sets top-k, mode, temperature/top-p (if stochastic)
   - Clicks "STEP" button

2. **Step Execution:**
   - Button disabled, loading state activated
   - POST request to `/step` with current `renderedText`
   - Response contains: chosen token, top-k distribution, metadata
   - New `StepRecord` appended to `trace`
   - `append_text` appended to `renderedText`
   - New token chip rendered in Inspect mode
   - Chip auto-expanded, briefly pulses, auto-scrolls into view

3. **Token Chip Interaction:**
   - Click chip to expand/collapse
   - Expanded chip shows vertical list of top-k candidates
   - Each candidate shows: probability bar, token text, probability, token ID
   - Chosen token highlighted (blue border, bold text)
   - Surprisal bar under chip (red, width ∝ surprisal)
   - Hover tooltip shows surprisal and probability

4. **View Switching:**
   - **Inspect → Collapsed**: Hides token rail, shows plain `renderedText`
   - **Collapsed → Inspect**: Rebuilds token rail from `trace` (no network call)

**UI Features:**
- **Token Chips**: Visual representation of each generated token
  - Shows display-safe token text (spaces visible as ␠)
  - Token ID label (small gray text)
  - Surprisal bar (red bar under chip, width indicates unpredictability)
  - Pulse animation on new tokens (200-500ms)
  
- **Top-k List**: Expandable panel showing probability distribution
  - Vertical gradient bars (width ∝ probability, opacity ∝ probability)
  - Color-blind friendly (neutral gray with opacity)
  - Chosen token highlighted
  - Footer shows coverage (Σprob) and count (N)

- **UX Guardrails:**
  - "Working..." text after 2s delay
  - Toast notification after 5s delay
  - Error boundaries prevent white screen crashes
  - Defensive null checks prevent undefined errors

#### **`src/api.ts` - API Client**
Handles all HTTP communication with the backend.

**Key Features:**
- **Response Normalization**: Sanitizes all numeric fields (converts to Number, provides fallbacks)
- **Type Safety**: Validates response structure before returning
- **Error Handling**: Parses backend error responses and throws structured errors

**Functions:**
- `performStep(request)`: Main API call, normalizes response before returning
- `getNextDist(request)`: Alternative endpoint (not used in current UI)

#### **`src/types.ts` - TypeScript Type Definitions**
Mirrors Python contracts for type safety across the stack.

#### **`src/ErrorBoundary.tsx` - Error Recovery**
React Error Boundary that catches rendering errors and displays a fallback UI instead of a white screen.

---

## Data Flow: Complete Request-Response Cycle

### Example: User clicks "STEP" with context "The capital of France is"

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER ACTION                                                  │
│    - Context: "The capital of France is"                        │
│    - Top-k: 10                                                  │
│    - Mode: stochastic (temp=0.8, top-p=0.95)                    │
│    - Click "STEP"                                               │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. FRONTEND: handleStep()                                       │
│    - Disable button, set isLoading=true                         │
│    - Start 2s/5s timeout timers                                 │
│    - Call performStep({                                         │
│        context_text: "The capital of France is",                │
│        top_k: 10,                                               │
│        mode: "stochastic",                                      │
│        temperature: 0.8,                                        │
│        top_p: 0.95                                              │
│      })                                                         │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. HTTP REQUEST                                                 │
│    POST http://localhost:8000/step                              │
│    Content-Type: application/json                               │
│    Body: {                                                      │
│      "context_text": "The capital of France is",                │
│      "top_k": 10,                                               │
│      "mode": "stochastic",                                      │
│      "temperature": 0.8,                                        │
│      "top_p": 0.95                                              │
│    }                                                            │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. BACKEND: main.py /step endpoint                              │
│    - Validate request (top_k, payload size)                     │
│    - Clamp top_k to [5, 30] → used_top_k = 10                   │
│    - Handle empty context (BOS) if needed                       │
│    - Call adapter.tokenize("The capital of France is")          │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. ADAPTER: tokenize()                                          │
│    - Tokenizer encodes text → [1234, 5678, 9012, ...]          │
│    - Check length: 5 tokens (within 512 limit)                  │
│    - Convert IDs back to tokens → ["The", " capital", " of",    │
│                                    " France", " is"]            │
│    - Return {ids: [...], tokens: [...]}                         │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. BACKEND: Forward pass                                        │
│    - Call adapter.forward_last(context_ids)                     │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. ADAPTER: forward_last()                                      │
│    - Convert IDs to PyTorch tensor                              │
│    - Run model.forward(input_ids)                               │
│    - Extract logits[0, -1, :] (last position, vocab-sized)      │
│    - Returns: [2.3, -1.5, 0.8, ..., 4.2] (50257 floats)        │
│      (one logit per vocabulary token)                           │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. BACKEND: Get top-k distribution                              │
│    - Call adapter.topk(logits, k=10)                            │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 9. ADAPTER: topk()                                              │
│    - Convert logits to tensor                                   │
│    - Apply torch.log_softmax(logits) → log_probs                │
│    - Use torch.topk(log_probs, k=10) → top 10 indices           │
│    - For each top token:                                        │
│      * token_id = index                                         │
│      * prob = exp(log_prob)                                     │
│      * logprob = log_prob                                       │
│      * token_text_raw = decode([token_id],                      │
│                                clean_up_tokenization_spaces=False)│
│      * token_text_display = make_token_display(raw)             │
│    - Sort by prob descending                                    │
│    - Return: [                                                  │
│        {token_id: 1234, token_text_raw: " Paris",               │
│         token_text_display: "␠Paris", prob: 0.45, ...},        │
│        {token_id: 5678, token_text_raw: " the", ...},           │
│        ...                                                      │
│      ]                                                          │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 10. BACKEND: Choose token                                       │
│     - Call adapter.choose(logits, mode="stochastic",            │
│                           k=10, temp=0.8, top_p=0.95)           │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 11. ADAPTER: choose() - Stochastic Mode                         │
│     - Scale logits: logits / 0.8 (temperature)                  │
│     - Apply softmax → probabilities                             │
│     - Apply top-p filtering:                                    │
│       * Sort probs descending                                   │
│       * Cumulative sum until ≥ 0.95                             │
│       * Keep only tokens in that set                            │
│       * Renormalize                                             │
│     - Sample: torch.multinomial(filtered_probs, 1)              │
│     - Get chosen token_id, prob, logprob                        │
│     - Compute surprisal = -log(prob + 1e-12)                    │
│     - Return: {                                                 │
│         token_id: 1234,                                         │
│         token_text_raw: " Paris",                               │
│         token_text_display: "␠Paris",                           │
│         prob: 0.45,                                             │
│         logprob: -0.7985,                                       │
│         surprisal: 0.7985                                       │
│       }                                                         │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 12. BACKEND: Assemble response                                  │
│     - Ensure chosen token is in topk (insert if missing)        │
│     - Calculate coverage_topk = Σ prob(top-k)                   │
│     - Build last_token info                                     │
│     - Create StepResponseModel with all fields                  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 13. HTTP RESPONSE                                               │
│     Status: 200 OK                                              │
│     Headers: X-NextTokenLens-Contract: v1                       │
│     Body: {                                                     │
│       "context_len_tokens": 5,                                  │
│       "topk": [...],  // 10 items                               │
│       "coverage_topk": 0.85,                                    │
│       "chosen": {token_id: 1234, token_text_raw: " Paris", ...},│
│       "append_text": " Paris",                                  │
│       "used_top_k": 10,                                         │
│       "last_token": {id: 9012, text: " is"},                    │
│       "model_info": {...},                                      │
│       "contract_version": "v1"                                  │
│     }                                                           │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 14. FRONTEND: API Client Normalization                          │
│     - Receive JSON response                                     │
│     - Normalize all fields:                                     │
│       * Convert all numbers with Number()                       │
│       * Provide fallbacks for missing fields                    │
│       * Validate structure (topk is array, chosen exists)       │
│     - Return sanitized StepResponse                             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 15. FRONTEND: State Update                                      │
│     - Clear timeout timers                                      │
│     - Create new StepRecord:                                    │
│       {                                                         │
│         idx: 0,                                                 │
│         context_len_before: 5,                                  │
│         chosen: {...},                                          │
│         topk: [...]                                             │
│       }                                                         │
│     - Append to trace: setTrace([...trace, newRecord])          │
│     - Append to renderedText: "The capital of France is Paris"  │
│     - Set expandedTokenIdx = 0 (auto-expand new chip)           │
│     - Set pulsingTokenIdx = 0 (trigger pulse animation)         │
│     - Clear pulsing after 400ms                                 │
│     - Re-enable button                                          │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 16. FRONTEND: UI Rendering                                      │
│     - React re-renders with new trace                           │
│     - New token chip appears in token rail                      │
│     - Chip shows "␠Paris" with token ID label                   │
│     - Surprisal bar rendered (red, width based on surprisal)    │
│     - Chip auto-expanded, showing top-k list                    │
│     - Top-k list shows 10 candidates with probability bars      │
│     - " Paris" highlighted (chosen token)                       │
│     - Auto-scroll to keep new chip visible                      │
│     - Pulse animation plays (400ms)                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Concepts Explained

### 1. **Tokens vs. Words**
LLMs don't work with words directly—they use **tokens**, which are subword units. For example:
- "The capital of France is" → tokens: `["The", " capital", " of", " France", " is"]`
- Notice the leading space in `" capital"`—this is preserved exactly
- Tokens can be parts of words: "capitalization" might become `["capital", "ization"]`

### 2. **Logits → Probabilities**
- **Logits**: Raw model outputs (unbounded real numbers)
- **Softmax**: Converts logits to probabilities (sums to 1.0)
- **Log-probabilities**: `log(prob)` - useful for numerical stability
- **Surprisal**: `-log(prob)` - measures how "surprising" a token is (higher = less expected)

### 3. **Argmax vs. Stochastic Sampling**
- **Argmax**: Always picks the highest-probability token (deterministic, predictable)
- **Stochastic**: Samples from the distribution (more creative, varied)
  - **Temperature**: Controls randomness (lower = more conservative, higher = more creative)
  - **Top-p (Nucleus)**: Filters to smallest set of tokens whose cumulative probability ≥ p

### 4. **Context Truncation**
- Models have limited context windows (512 tokens here)
- If input exceeds limit, we keep the **last** 512 tokens (most recent context)
- This ensures the model always sees the most relevant recent information

### 5. **Display vs. Raw Tokens**
- **Raw tokens**: Exact decoded strings (preserves spaces, newlines, etc.)
- **Display tokens**: UI-safe labels (spaces → ␠, newlines → ⏎\n)
- Raw tokens used for concatenation (correct text generation)
- Display tokens used for visualization (human-readable)

---

## Session Trace (Client-Side Memory)

The frontend maintains a **trace** of all steps taken in the current session:

```typescript
type Trace = Array<StepRecord>

type StepRecord = {
  idx: number;                    // Step index (0, 1, 2, ...)
  context_len_before: number;     // How many tokens before this step
  chosen: ChosenToken;            // The token that was selected
  topk: Array<TokenInfo>;         // The top-k distribution shown
}
```

**Why client-side only?**
- Allows view switching without network calls
- Enables rebuilding the UI from history
- Reduces server state management complexity

**How it works:**
1. Each STEP adds a new `StepRecord` to `trace`
2. Token chips are rendered from `trace.map(record => record.chosen)`
3. Expanding a chip shows `record.topk` (the distribution from that step)
4. Collapsed view shows `renderedText` (accumulated string)
5. Editing context resets `trace` (new session)

---

## Error Handling & Resilience

### Backend Error Handling
- **Validation Errors** (400): Invalid top_k, payload too large
- **Server Errors** (500): Model not loaded, unexpected exceptions
- **Structured Responses**: All errors return `{status: "error", message: "...", hint: "..."}`

### Frontend Error Handling
- **API Client Normalization**: Converts all fields to correct types, provides fallbacks
- **Defensive Rendering**: Null checks before calling `.toFixed()`, array checks before mapping
- **Error Boundary**: Catches React rendering errors, shows fallback UI
- **Loading States**: Prevents double-submission, shows progress feedback
- **Timeout Handling**: "Working..." after 2s, toast after 5s

---

## Performance Optimizations

1. **Eager Model Loading**: Model loads at server startup (not on first request)
2. **Numerical Stability**: Uses `log_softmax` instead of `softmax` + `log` (prevents overflow)
3. **Tensor Operations**: Keeps computations in PyTorch until final conversion
4. **Context Truncation**: Limits input size to prevent memory issues
5. **Top-k Clamping**: Prevents expensive computations with huge k values

---

## Future Enhancements (Not Yet Implemented)

- **KV Cache**: Reuse attention keys/values across steps for faster inference
- **Streaming**: Stream tokens as they're generated (not just one at a time)
- **Multiple Models**: Switch between different models in the UI
- **Export/Import**: Save and load session traces
- **Advanced Sampling**: Top-k sampling, repetition penalty, etc.

---

## Testing

### Automated Tests (`test_qa.py`)
- Health check verification
- Empty context (BOS) handling
- Unicode/emoji preservation
- Context truncation
- Top-k clamping
- Multiple sequential steps
- Response structure validation
- Error handling

### Manual Testing
- Short prompts
- Unicode inputs
- Empty context
- Long inputs (truncation)
- View switching
- Token chip interactions

---

## File Structure

```
NextWord/
├── Backend (Python)
│   ├── main.py              # FastAPI server, endpoints
│   ├── adapter_hf.py        # HuggingFace model adapter
│   ├── contracts.py         # Frozen type definitions
│   ├── requirements.txt     # Python dependencies
│   └── test_qa.py          # Automated test suite
│
├── Frontend (TypeScript/React)
│   ├── src/
│   │   ├── App.tsx          # Main React component
│   │   ├── App.css          # Styles
│   │   ├── api.ts           # API client with normalization
│   │   ├── types.ts         # TypeScript type definitions
│   │   ├── ErrorBoundary.tsx # Error recovery component
│   │   ├── main.tsx         # React entry point
│   │   └── index.css        # Global styles
│   ├── package.json         # Node dependencies
│   └── vite.config.ts       # Vite build configuration
│
└── Documentation
    ├── README.md            # Quick start guide
    ├── CONTRACTS.md         # Detailed contract documentation
    ├── QA_TEST.md           # Manual testing guide
    └── PROJECT_OVERVIEW.md  # This file
```

---

## Summary

NextWord is a **pedagogical tool** that makes LLM token generation transparent. By showing the probability distribution at each step, users can understand:

- How models make decisions
- Why certain tokens are more likely than others
- The difference between deterministic (argmax) and stochastic sampling
- How context influences predictions
- The role of temperature and top-p in generation

The architecture is designed for **stability** (frozen contracts), **clarity** (clear separation of concerns), and **resilience** (defensive programming, error handling). The UI provides rich visual feedback while the backend handles the complex model inference efficiently.


