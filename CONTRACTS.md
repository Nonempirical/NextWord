# Frozen Contracts Documentation

**IMPORTANT: These contracts are FROZEN and must not be changed after the initial ticket.**

## Adapter Interface (local HF)

The `Adapter` abstract base class defines the following methods:

### `tokenize(text: str) -> TokenizeResult`

Tokenizes input text into token IDs and token strings.

**Returns:**
```python
{
    "ids": List[int],      # List of token IDs
    "tokens": List[str]    # List of token strings (exact, including leading spaces)
}
```

### `forward_last(ids: List[int]) -> List[float]`

Runs forward pass through the model and returns logits for the last position only.

**Parameters:**
- `ids`: List of token IDs

**Returns:**
- `List[float]`: Vocab-sized list of logits (last position only)

### `topk(logits: List[float], k: int) -> List[TokenInfo]`

Gets top-k tokens from logits with probabilities.

**Parameters:**
- `logits`: Vocab-sized list of logits
- `k`: Number of top tokens to return

**Returns:**
- `List[TokenInfo]`: List of token information dictionaries, sorted descending by probability
  - Probabilities sum to ~1 over the full vocabulary
  - Each item: `{token_id: int, token_text: str, prob: float, logprob: float}`

### `choose(logits: List[float], mode: str, k: int, temperature: Optional[float] = None) -> ChosenToken`

Chooses a token from logits based on selection mode.

**Parameters:**
- `logits`: Vocab-sized list of logits
- `mode`: Selection mode - `"argmax"` (MVP supported) or `"stochastic"` (future, can be ignored for now)
- `k`: Top-k constraint (for stochastic mode)
- `temperature`: Optional temperature for stochastic sampling

**Returns:**
- `ChosenToken`: `{token_id: int, token_text: str, prob: float, logprob: float}`

**Note:** MVP supports `mode="argmax"` only. `"stochastic"` mode should be accepted but can be ignored for now.

---

## API Endpoints

### POST /next_dist

Get the distribution of next tokens for a given context.

**Request:**
```json
{
  "context_text": "string",
  "top_k": 10
}
```

**Response:**
```json
{
  "context_len_tokens": 5,
  "topk": [
    {
      "token_id": 123,
      "token_text": " the",
      "prob": 0.45,
      "logprob": -0.7985
    }
  ],
  "coverage_topk": 0.85,
  "last_token": {
    "id": 456,
    "text": "Hello"
  },
  "model_info": {
    "provider": "hf-local",
    "model_name": "gpt2",
    "vocab_size": 50257
  }
}
```

### POST /step

Perform a step: choose a token and return it along with the distribution.

**Request:**
```json
{
  "context_text": "string",
  "top_k": 10,
  "mode": "argmax"
}
```

**Response:**
Same as `/next_dist` plus:
```json
{
  "chosen": {
    "token_id": 123,
    "token_text": " the",
    "prob": 0.45,
    "logprob": -0.7985
  },
  "append_text": " the"
}
```

**Note:** `append_text` is the exact token text to append, including leading space if any.

---

## Session Trace (Client Memory Only)

The session trace is maintained client-side only and is not part of the API.

**TypeScript Types:**
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

**Python Equivalent:**
```python
StepRecord = TypedDict('StepRecord', {
    'idx': int,
    'context_len_before': int,
    'chosen': ChosenToken,
    'topk': List[TokenInfo]
})

Trace = List[StepRecord]
```

---

## Implementation Files

- `contracts.py`: Python type definitions and Adapter interface
- `types.ts`: TypeScript type definitions for client-side use
- `adapter_hf.py`: HuggingFace implementation of the Adapter interface
- `main.py`: FastAPI server implementing the API endpoints

