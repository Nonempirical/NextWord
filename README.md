# NextWord - LLM Token Visualization

A software for displaying the next token from an LLM to visualize how they work.

## Frozen Contracts

### Adapter Interface (local HF)

The adapter must implement the following interface:

- `tokenize(text: str) -> TokenizeResult`
  - Returns object with keys: `"ids"` (int[]) and `"tokens"` (string[])

- `forward_last(ids: list[int]) -> list[float]`
  - Returns: `logits: float[]` (vocab-sized, last position only)

- `topk(logits: list[float], k: int) -> list[dict]`
  - Returns: `[{ "token_id": int, "token_text": str, "prob": float, "logprob": float }]`
  - Sorted descending by probability
  - Probabilities sum to ~1 over vocab

- `choose(logits: list[float], mode: str, k: int, temperature: float | None = None) -> dict`
  - Returns: `{ "token_id": int, "token_text": str, "prob": float, "logprob": float }`
  - MVP supports mode: `"argmax"`
  - Future: `"stochastic"` mode (ignored for now)

### API Endpoints

#### POST /next_dist

**Request:**
```json
{
  "context_text": string,
  "top_k": number
}
```

**Response:**
```json
{
  "context_len_tokens": number,
  "topk": [
    {
      "token_id": number,
      "token_text": string,
      "prob": number,
      "logprob": number
    }
  ],
  "coverage_topk": number,
  "last_token": {
    "id": number | null,
    "text": string | null
  },
  "model_info": {
    "provider": "hf-local",
    "model_name": string,
    "vocab_size": number
  },
  "contract_version": "v1"
}
```

**Headers:**
- `X-NextTokenLens-Contract: v1` (contract version header)

#### POST /step

**Request:**
```json
{
  "context_text": string,
  "top_k": number,
  "mode": "argmax" | "stochastic"
}
```

**Response:**
Same as `/next_dist` plus:
```json
{
  "chosen": {
    "token_id": number,
    "token_text": string,
    "prob": number,
    "logprob": number
  },
  "append_text": string,
  "contract_version": "v1"
}
```

**Headers:**
- `X-NextTokenLens-Contract: v1` (contract version header)

**Note**: If `top_k` is outside [5, 30], the server clamps it and the response reflects the used value.

### Session Trace (Client Memory Only)

```typescript
type StepRecord = {
  idx: number;
  context_len_before: number;
  chosen: {
    token_id: number;
    token_text: string;
    prob: number;
    logprob: number;
  };
  topk: Array<{
    token_id: number;
    token_text: string;
    prob: number;
    logprob: number;
  }>;
};

type Trace = Array<StepRecord>;
```

## Model & Performance Defaults

- **Model**: `distilgpt2` (fastest CPU baseline)
- **Context Cap**: 512 tokens (internal, truncates from beginning if exceeded)
- **Top-k Default**: 10
- **Top-k Range**: 5-30 (server clamps to this range)
- **Throughput Target**: ≤ 400ms per Step
- **Time Budget**: 
  - If step exceeds 2s, UI shows non-blocking "Working…" state
  - If step exceeds 5s, UI shows gentle "Try again" toast (MVP guardrail)

## BOS (Beginning of Sequence) Behavior

If `context_text` is empty, the server treats it as BOS (beginning of sequence) and returns the distribution at the tokenizer's start token. The `/step` endpoint will append the argmax token normally, allowing generation to start from an empty context.

## Unicode & Token Encoding

Responses preserve token strings exactly as decoded, including:
- Leading spaces (e.g., `" the"` vs `"the"`)
- Non-printable bytes (displayed with safe fallback like `⟦U+XXXX⟧` in tooltips)
- Unicode characters (emojis, special characters, etc.)

The tokenizer's round-trip decode (`convert_ids_to_tokens` → `convert_tokens_to_string`) ensures token boundary semantics are respected.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Backend

```bash
uvicorn main:app --reload
```

The server will start on `http://localhost:8000` by default.

**Note**: CORS is enabled for `http://localhost:3001` during development (frontend proxy → backend).

### Frontend

```bash
npm run dev
```

The frontend will be available at `http://localhost:3001` and will proxy API requests to the backend.

**Note**: If ports collide, change one; ensure CORS origin matches the frontend port.

### API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Health Check

The server exposes `/healthz` (or `/health`) returning model name and vocab size. The model loads eagerly at startup so the first STEP isn't slow.

## Performance Notes

- Softmax calculations use PyTorch's numerically stable implementation (log-sum-exp trick)
- Context is automatically truncated to 512 tokens if longer (keeps the last 512 tokens)
- Default top-k is 10, but can be adjusted up to 30 for MVP

## Frontend UI

The project includes a React-based frontend for visualizing token generation.

### Setup Frontend

```bash
# Install frontend dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:3000` and will proxy API requests to the backend at `http://localhost:8000`.

### UI Features

- **Top Bar Controls:**
  - Context textarea (editable)
  - Top-k input (min 5, max 30, default 10)
  - Mode select (Argmax/Stochastic - MVP: Argmax only)
  - STEP button
  - View toggle (Inspect ↔ Collapsed)

- **Inspect Mode:**
  - Horizontal scrollable token rail
  - Token chips showing literal token text (including leading spaces)
  - Expandable chips showing top-k candidates with probability bars
  - Auto-scroll to newest token
  - Pulse animation for newly appended tokens

- **Collapsed Mode:**
  - Plain text view of full generated string
  - Click to toggle back to Inspect mode

### Build for Production

```bash
npm run build
```

## Dev Runbook

**Backend:**
```bash
uvicorn main:app --reload
```

**Frontend:**
```bash
npm run dev
```

Frontend runs on port 3001, backend on port 8000. If ports collide, change one; ensure CORS origin matches.

## MVP Acceptance Checklist

✅ **Typing text → press STEP:**
- You see a ranked list of top-k with Σprob coverage
- Exactly one token is appended to the output string
- In Inspect, a new token chip appears on the right, auto-expanded with a vertical gradient list of the candidates
- The chosen row is highlighted
- The chip pulses briefly
- The horizontal rail auto-scrolls to keep the newest chip visible

✅ **Toggling Collapsed:**
- Shows the same text as concatenating chosen tokens
- Clicking returns to Inspect with the same chips (no network calls)

✅ **Edge Cases:**
- Empty context works (BOS)
- Long inputs get truncated to last 512 tokens (and context_len_tokens reflects this)
- Requests with top_k outside bounds are clamped and reported back as used value

## Test Prompts (QA Pass)

- **Short**: "The capital of France is"
- **Unicode**: "Emoji test: 🔥 The"
- **Empty**: "" (BOS)
- **Long** (force truncation): paste ~1000 tokens and confirm context_len_tokens=512

**Verify:**
- Descending probabilities
- Σprob(top-k) shown
- Chosen candidate highlighted
- Chip count equals steps
- Collapsed text equals join of all chosen tokens

## Automated QA Testing

An automated test script is available to verify the backend functionality:

```bash
# Install test dependency (if not already installed)
pip install requests

# Make sure backend is running: uvicorn main:app --reload

# Run automated tests
python test_qa.py
```

The test script verifies:
- Health check endpoint
- Empty context (BOS) handling
- Short prompt generation
- Unicode/emoji preservation
- Context truncation to 512 tokens
- Top-k clamping [5, 30]
- Multiple sequential steps
- Response structure matches contract
- Error handling

See `QA_TEST.md` for detailed manual testing instructions.

