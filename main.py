"""
NextWord API Server

FastAPI server implementing the frozen API contracts.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

from contracts import (
    TokenInfo,
    ChosenToken,
    ModelInfo,
    LastToken,
    NextDistRequest,
    NextDistResponse,
    StepRequest,
    StepResponse
)
from adapter_hf import HuggingFaceAdapter

app = FastAPI(title="NextWord API", version="1.0.0")

# CORS middleware for client access (enable for localhost:3001 during dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],  # Frontend proxy → backend
    allow_credentials=True,
    allow_methods=["POST", "GET"],  # Only POST and GET
    allow_headers=["Content-Type"],  # Only Content-Type header
)

# Add contract version header to all responses
@app.middleware("http")
async def add_contract_version_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-NextTokenLens-Contract"] = CONTRACT_VERSION
    return response

# Global exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions and return error format."""
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": str(exc),
            "hint": "An unexpected error occurred"
        }
    )

# Global adapter instance (initialize on startup)
adapter: Optional[HuggingFaceAdapter] = None
MODEL_NAME = "Qwen/Qwen2.5-1.5B"  # Qwen2.5-1.5B model

# Performance defaults
CONTEXT_CAP_TOKENS = 512  # Internal context cap (no UI yet)
TOP_K_DEFAULT = 10  # Default top-k value
TOP_K_MIN = 5  # Minimum top-k (server clamps to this)
TOP_K_MAX = 30  # Maximum top-k (server clamps to this)
THROUGHPUT_TARGET_MS = 400  # Target: ≤ 400ms per Step
MAX_PAYLOAD_SIZE = 50000  # Max payload size in chars (prevent paste bombs)

# Contract version
CONTRACT_VERSION = "v1"


@app.on_event("startup")
async def startup_event():
    """Initialize the adapter on startup."""
    global adapter
    try:
        adapter = HuggingFaceAdapter(MODEL_NAME, device="cpu")
        print(f"Loaded model: {MODEL_NAME}")
    except Exception as e:
        print(f"Error loading model: {e}")
        raise


# Pydantic models for request/response validation
class NextDistRequestModel(BaseModel):
    context_text: str = Field(..., max_length=MAX_PAYLOAD_SIZE)
    top_k: int = Field(default=TOP_K_DEFAULT, ge=1, le=1000)  # Will be clamped server-side


class StepRequestModel(BaseModel):
    context_text: str = Field(..., max_length=MAX_PAYLOAD_SIZE)
    top_k: int = Field(..., ge=1)  # Will be clamped server-side to [5, 30]
    mode: Literal["argmax", "stochastic"] = "stochastic"  # Default to stochastic
    temperature: Optional[float] = Field(default=0.8, ge=0.2, le=1.5)
    top_p: Optional[float] = Field(default=0.95, ge=0.7, le=1.0)
    soften_newline_eot: Optional[bool] = Field(default=False)  # Hidden dev toggle


class TokenInfoModel(BaseModel):
    token_id: int
    token_text: str
    prob: float
    logprob: float


class ChosenTokenModel(BaseModel):
    token_id: int
    token_text: str
    prob: float
    logprob: float


class LastTokenModel(BaseModel):
    id: Optional[int] = None
    text: Optional[str] = None


class ModelInfoModel(BaseModel):
    provider: Literal["hf-local"]
    model_name: str
    vocab_size: int


class NextDistResponseModel(BaseModel):
    context_len_tokens: int
    topk: List[TokenInfoModel]
    coverage_topk: float
    last_token: LastTokenModel
    model_info: ModelInfoModel
    contract_version: str = CONTRACT_VERSION


class StepResponseModel(NextDistResponseModel):
    chosen: ChosenTokenModel
    append_text: str
    used_top_k: int


@app.post("/next_dist", response_model=NextDistResponseModel)
async def next_dist(request: NextDistRequestModel):
    """
    POST /next_dist
    
    Same as /step but without choosing/appending.
    Returns distribution only (no chosen token or append_text).
    
    Request: { "context_text": string, "top_k": number }
    Response: Same fields as /step minus chosen and append_text.
    """
    if adapter is None:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Adapter not initialized", "hint": "Server startup may have failed"}
        )
    
    try:
        # Validation: reject empty top_k or huge inputs
        if request.top_k is None or request.top_k < 1:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "top_k must be a positive integer",
                    "hint": "Provide a top_k value between 1 and 30 (will be clamped to [5, 30])"
                }
            )
        
        if len(request.context_text) > MAX_PAYLOAD_SIZE:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"Input too large (max {MAX_PAYLOAD_SIZE} characters)",
                    "hint": "Reduce the size of your context_text input"
                }
            )
        
        # Clamp top_k to [5, 30]
        clamped_top_k = max(TOP_K_MIN, min(TOP_K_MAX, request.top_k))
        
        # Handle empty context (BOS) - allow empty string
        context_text = request.context_text if request.context_text else ""
        
        # Tokenize context_text; truncate to last 512 IDs (done in adapter.tokenize)
        tokenize_result = adapter.tokenize(context_text)
        context_ids = tokenize_result["ids"]
        context_tokens = tokenize_result["tokens"]
        
        # Compute context_len_tokens (after truncation in adapter)
        context_len = len(context_ids)
        
        # Run forward; get last logits → probs
        logits = adapter.forward_last(context_ids, soften_newline_eot=False)  # /next_dist doesn't support this toggle
        
        # Build topk (k clamped to [5, 30])
        topk = adapter.topk(logits, clamped_top_k)
        
        # Calculate coverage_topk (sum of top-k probabilities)
        coverage_topk = sum(token["prob"] for token in topk)
        
        # last_token: if context had ≥1 token, set {id, text} to the final context token; otherwise null
        last_token: LastToken = {
            "id": context_ids[-1] if context_ids else None,
            "text": context_tokens[-1] if context_tokens else None
        }
        
        # Include minimal model_info
        model_info: ModelInfo = {
            "provider": "hf-local",
            "model_name": adapter.model_name,
            "vocab_size": adapter.vocab_size
        }
        
        return NextDistResponseModel(
            contract_version=CONTRACT_VERSION,
            context_len_tokens=context_len,
            topk=[TokenInfoModel(**token) for token in topk],
            coverage_topk=coverage_topk,
            last_token=LastTokenModel(**last_token),
            model_info=ModelInfoModel(**model_info)
        )
    
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e), "hint": "Check your input parameters"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e), "hint": "Internal server error occurred"}
        )


@app.post("/step", response_model=StepResponseModel)
async def step(request: StepRequestModel):
    """
    POST /step
    
    Accept context + top_k + mode, return top-k distribution and the chosen token.
    
    Request: { "context_text": string, "top_k": number, "mode": "argmax" | "stochastic" }
    MVP: treat "stochastic" as "argmax"; just accept it.
    
    Logic:
    1. Tokenize context_text; truncate to last 512 IDs; compute context_len_tokens
    2. Run forward; get last logits → probs
    3. Build topk (k clamped to [5, 30]); ensure chosen appears in topk
    4. If argmax isn't in top-k, insert it and drop the last entry to keep length k
    5. last_token: if context had ≥1 token, set {id, text} to the final context token; otherwise null
    6. append_text is exact decoded token for chosen.token_id
    """
    if adapter is None:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Adapter not initialized", "hint": "Server startup may have failed"}
        )
    
    try:
        # Validation: reject empty top_k or huge inputs
        if request.top_k is None or request.top_k < 1:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "top_k must be a positive integer",
                    "hint": "Provide a top_k value between 1 and 30 (will be clamped to [5, 30])"
                }
            )
        
        if len(request.context_text) > MAX_PAYLOAD_SIZE:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"Input too large (max {MAX_PAYLOAD_SIZE} characters)",
                    "hint": "Reduce the size of your context_text input"
                }
            )
        
        # Clamp top_k to [5, 30]
        clamped_top_k = max(TOP_K_MIN, min(TOP_K_MAX, request.top_k))
        used_top_k = clamped_top_k
        
        # Handle empty context (BOS) - allow empty string
        context_text = request.context_text if request.context_text else ""
        
        # 1. Tokenize context_text; truncate to last 512 IDs (done in adapter.tokenize)
        tokenize_result = adapter.tokenize(context_text)
        context_ids = tokenize_result["ids"]
        context_tokens = tokenize_result["tokens"]
        
        # Compute context_len_tokens (after truncation in adapter)
        context_len = len(context_ids)
        
        # 2. Run forward; get last logits → probs
        logits = adapter.forward_last(context_ids, soften_newline_eot=request.soften_newline_eot)
        
        # 3. Build topk (k clamped to [5, 30])
        # Note: topk is from unfiltered distribution (for pedagogical chart)
        topk = adapter.topk(logits, clamped_top_k)
        
        # Choose token (argmax or stochastic with temperature and top-p)
        chosen = adapter.choose(
            logits, 
            request.mode, 
            clamped_top_k,
            temperature=request.temperature if request.mode == "stochastic" else None,
            top_p=request.top_p if request.mode == "stochastic" else None
        )
        
        # Ensure chosen appears in topk: if argmax isn't in top-k, insert it and drop the last entry
        chosen_in_topk = any(t["token_id"] == chosen["token_id"] for t in topk)
        if not chosen_in_topk:
            topk = [chosen] + topk[:-1]  # Insert chosen at front, drop last to keep length k
        
        # Calculate coverage_topk (sum of top-k probabilities)
        coverage_topk = sum(token["prob"] for token in topk)
        
        # last_token: if context had ≥1 token, set {id, text} to the final context token; otherwise null
        last_token: LastToken = {
            "id": context_ids[-1] if context_ids else None,
            "text": context_tokens[-1] if context_tokens else None
        }
        
        # Include minimal model_info
        model_info: ModelInfo = {
            "provider": "hf-local",
            "model_name": adapter.model_name,
            "vocab_size": adapter.vocab_size
        }
        
        # append_text is exact decoded token for chosen.token_id (use raw token)
        append_text = chosen.get("token_text_raw", chosen["token_text"])
        
        return StepResponseModel(
            contract_version=CONTRACT_VERSION,
            context_len_tokens=context_len,
            topk=[TokenInfoModel(**token) for token in topk],
            coverage_topk=coverage_topk,
            last_token=LastTokenModel(**last_token),
            model_info=ModelInfoModel(**model_info),
            chosen=ChosenTokenModel(**chosen),
            append_text=append_text,
            used_top_k=used_top_k
        )
    
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e), "hint": "Check your input parameters"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e), "hint": "Internal server error occurred"}
        )


@app.get("/healthz")
async def healthz():
    """
    Health check endpoint.
    
    Returns model name, vocab size, and contract version.
    Model loads eagerly at startup so the first STEP isn't slow.
    """
    if adapter is None:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": "Model not loaded",
                "hint": "Server startup may have failed"
            }
        )
    
    return {
        "model_name": adapter.model_name,
        "vocab_size": adapter.vocab_size,
        "contract_version": CONTRACT_VERSION
    }

