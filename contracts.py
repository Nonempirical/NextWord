"""
FROZEN CONTRACTS - DO NOT CHANGE AFTER INITIAL TICKET

This module defines the frozen contracts for the NextWord project.
These interfaces and types must remain stable.
"""
from typing import Protocol, TypedDict, List, Literal, Optional
from abc import ABC, abstractmethod


# ============================================================================
# Adapter Interface (local HF)
# ============================================================================

class TokenizeResult(TypedDict):
    """Result of tokenize operation."""
    ids: List[int]
    tokens: List[str]


class TokenInfo(TypedDict):
    """Information about a token."""
    token_id: int
    token_text: str
    prob: float
    logprob: float


class ChosenToken(TypedDict):
    """Result of choose operation."""
    token_id: int
    token_text: str
    prob: float
    logprob: float
    surprisal: float


class Adapter(ABC):
    """
    Adapter interface for local HuggingFace models.
    
    All methods must be implemented by concrete adapters.
    """
    
    @abstractmethod
    def tokenize(self, text: str) -> TokenizeResult:
        """
        Tokenize text into token IDs and token strings.
        
        Args:
            text: Input text to tokenize
            
        Returns:
            Dictionary with 'ids' (list of int) and 'tokens' (list of str)
        """
        pass
    
    @abstractmethod
    def forward_last(self, ids: List[int]) -> List[float]:
        """
        Run forward pass and return logits for the last position only.
        
        Args:
            ids: List of token IDs
            
        Returns:
            Vocab-sized list of logits (floats) for the last position
        """
        pass
    
    @abstractmethod
    def topk(self, logits: List[float], k: int) -> List[TokenInfo]:
        """
        Get top-k tokens from logits.
        
        Args:
            logits: Vocab-sized list of logits
            k: Number of top tokens to return
            
        Returns:
            List of TokenInfo dictionaries, sorted descending by probability.
            Probabilities should sum to ~1 over the full vocabulary.
        """
        pass
    
    @abstractmethod
    def choose(
        self, 
        logits: List[float], 
        mode: Literal["argmax", "stochastic"], 
        k: int,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None
    ) -> ChosenToken:
        """
        Choose a token from logits based on mode.
        
        Args:
            logits: Vocab-sized list of logits
            mode: Selection mode - "argmax" (MVP) or "stochastic" (future)
            k: Top-k constraint (for stochastic mode)
            temperature: Optional temperature for stochastic sampling
            
        Returns:
            ChosenToken dictionary with token_id, token_text, prob, logprob
            
        Note:
            MVP supports mode="argmax" only. "stochastic" mode should be
            accepted but can be ignored for now.
        """
        pass


# ============================================================================
# API Request/Response Types
# ============================================================================

class NextDistRequest(TypedDict):
    """Request for POST /next_dist endpoint."""
    context_text: str
    top_k: int


class ModelInfo(TypedDict):
    """Model information."""
    provider: Literal["hf-local"]
    model_name: str
    vocab_size: int


class LastToken(TypedDict, total=False):
    """Last token information (id and text can be null)."""
    id: Optional[int]
    text: Optional[str]


class NextDistResponse(TypedDict):
    """Response for POST /next_dist endpoint."""
    context_len_tokens: int
    topk: List[TokenInfo]
    coverage_topk: float
    last_token: LastToken
    model_info: ModelInfo
    contract_version: str


class StepRequest(TypedDict):
    """Request for POST /step endpoint."""
    context_text: str
    top_k: int
    mode: Literal["argmax", "stochastic"]


class StepResponse(NextDistResponse):
    """Response for POST /step endpoint (extends NextDistResponse)."""
    chosen: ChosenToken
    append_text: str
    # contract_version inherited from NextDistResponse


# ============================================================================
# Client-Side Session Trace Types
# ============================================================================

class StepRecord(TypedDict):
    """
    StepRecord for client-side session trace.
    
    Note: This is for client memory only, not part of the API.
    """
    idx: int
    context_len_before: int
    chosen: ChosenToken
    topk: List[TokenInfo]


# Trace = Array<StepRecord> (just a type alias in TypeScript)
# In Python, this would be: List[StepRecord]

