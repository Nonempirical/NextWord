"""
HuggingFace Adapter Implementation

Implements the Adapter interface for local HuggingFace models.
"""
import math
import torch
import unicodedata
from typing import List, Literal, Optional
from transformers import AutoTokenizer, AutoModelForCausalLM

from contracts import (
    Adapter,
    TokenizeResult,
    TokenInfo,
    ChosenToken
)


def make_token_display(raw_text: str) -> str:
    """
    Convert raw token text to a display-safe label.
    
    Rules:
    - ' ' (space) → ␠ space
    - '\n' → ⏎ \\n
    - '\t' → ⇥ \\t
    - Any token consisting only of Unicode whitespace → ␠×N (count, e.g., ␠×3)
    - Any non-printable chars (category Cc) → ⟦U+000A⟧ etc.
    - Otherwise: show the literal token (including leading spaces)
    """
    if not raw_text:
        return raw_text
    
    # Check if token consists only of Unicode whitespace
    if raw_text.isspace():
        # Count spaces and show as ␠×N
        space_count = raw_text.count(' ')
        if space_count == len(raw_text):
            if space_count == 1:
                return '␠'
            return f'␠×{space_count}'
        # Mixed whitespace - show count
        return f'␠×{len(raw_text)}'
    
    # Replace non-printable control characters first, then whitespace
    display_chars = []
    for char in raw_text:
        cat = unicodedata.category(char)
        if cat == 'Cc':  # Control character
            if char == '\n':
                display_chars.append('⏎\\n')
            elif char == '\t':
                display_chars.append('⇥\\t')
            elif char == '\r':
                display_chars.append('␍\\r')
            else:
                # Format as ⟦U+XXXX⟧
                code_point = ord(char)
                display_chars.append(f'⟦U+{code_point:04X}⟧')
        elif char == ' ':
            display_chars.append('␠')
        else:
            display_chars.append(char)
    
    return ''.join(display_chars)


class HuggingFaceAdapter(Adapter):
    """
    Adapter for local HuggingFace models.
    
    Implements the frozen Adapter interface.
    """
    
    # Constants
    CONTEXT_CAP_TOKENS = 512  # Context cap: keep last 512 tokens if exceeded
    TOP_K_MIN = 5  # Minimum k value
    TOP_K_MAX = 30  # Maximum k value
    
    def __init__(self, model_name: str, device: str = "cpu"):
        """
        Initialize the HuggingFace adapter.
        
        Args:
            model_name: HuggingFace model identifier (e.g., "gpt2")
            device: Device to run model on ("cpu" or "cuda")
        """
        self.model_name = model_name
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        # Force CPU FP32: load to CPU, eval()
        self.model.to(device)
        self.model.eval()  # Set to evaluation mode
        # Disable gradients for inference
        for param in self.model.parameters():
            param.requires_grad = False
        
        # Ensure pad token is set
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
    
    def tokenize(self, text: str) -> TokenizeResult:
        """
        Tokenize text into token IDs and token strings.
        
        Returns {ids, tokens} where:
        - ids: list[int] - token IDs
        - tokens: list[str] - decoded token strings (preserves leading spaces)
        
        Context cap: if tokenized length > 512, keep last 512 IDs.
        """
        # Tokenize and get IDs
        encoded = self.tokenizer.encode(text, add_special_tokens=False)
        ids = encoded
        
        # Context cap: if tokenized length > 512, keep last 512 IDs
        if len(ids) > self.CONTEXT_CAP_TOKENS:
            ids = ids[-self.CONTEXT_CAP_TOKENS:]
        
        # Get exact token strings (preserves leading spaces, etc.)
        # Recalculate tokens after potential truncation
        token_objects = self.tokenizer.convert_ids_to_tokens(ids)
        # Convert token objects to strings, handling special tokens
        tokens = [self.tokenizer.convert_tokens_to_string([token]) for token in token_objects]
        
        return {
            "ids": ids,
            "tokens": tokens
        }
    
    def forward_last(self, ids: List[int], soften_newline_eot: bool = False) -> List[float]:
        """
        Run forward pass and return logits for the last position only.
        
        Args:
            ids: List of token IDs
            soften_newline_eot: If True, subtract ~2.0 from newline and EOT logits
        
        Returns vocab-sized list of logits.
        """
        # Convert to tensor
        input_ids = torch.tensor([ids], device=self.device)
        
        # Forward pass
        with torch.no_grad():
            outputs = self.model(input_ids)
            logits = outputs.logits[0, -1, :]  # Last position only
        
        # Apply soft logit bias if requested
        if soften_newline_eot:
            # Identify IDs for '\n' and eos_token_id
            newline_encoded = self.tokenizer.encode('\n', add_special_tokens=False)
            newline_id = newline_encoded[0] if newline_encoded else None
            eos_id = self.tokenizer.eos_token_id
            
            # Subtract ~2.0 from their logits (not -inf)
            if newline_id is not None:
                logits[newline_id] -= 2.0
            if eos_id is not None:
                logits[eos_id] -= 2.0
        
        # Convert to list of floats (contract requires List[float])
        return logits.cpu().tolist()
    
    def topk(self, logits: List[float], k: int) -> List[TokenInfo]:
        """
        Get top-k tokens from logits.
        
        Returns list sorted descending by probability.
        Probabilities sum to ~1 over full vocabulary.
        
        Uses log_softmax for numerical stability, keeps everything as tensors until the end.
        
        Clamps k to [5, 30] in the adapter.
        """
        # Clamp k to [5, 30] in the adapter
        k = max(self.TOP_K_MIN, min(self.TOP_K_MAX, k))
        
        # Convert to tensor once - keep as tensor until the very end
        logits_tensor = torch.tensor(logits, dtype=torch.float32)
        
        # Compute log_probs using log_softmax (numerically stable)
        log_probs = torch.log_softmax(logits_tensor, dim=-1)
        
        # Get top-k directly from log_probs (more efficient)
        topk_log_probs, topk_ids = torch.topk(log_probs, k, dim=-1)
        
        # Convert to Python/JSON only at the very end
        result = []
        for i in range(k):
            token_id = int(topk_ids[i].item())
            # Get exact token string using convert_ids_to_tokens (preserves token semantics)
            token_obj = self.tokenizer.convert_ids_to_tokens([token_id])[0]
            # Use decode with clean_up_tokenization_spaces=False for raw text
            token_text_raw = self.tokenizer.decode([token_id], clean_up_tokenization_spaces=False)
            # Create display version
            token_text_display = make_token_display(token_text_raw)
            
            # Convert logprob and prob at the very end
            logprob = float(topk_log_probs[i].item())
            prob = float(torch.exp(topk_log_probs[i]).item())
            
            result.append({
                "token_id": token_id,
                "token_text": token_text_raw,  # Keep for backward compatibility
                "token_text_raw": token_text_raw,
                "token_text_display": token_text_display,
                "prob": prob,
                "logprob": logprob
            })
        
        # Sort by prob desc (should already be sorted from topk, but ensure)
        result.sort(key=lambda x: x["prob"], reverse=True)
        
        # Note: coverage_topk = Σ prob is calculated by the caller (main.py)
        # This method returns the sorted list of top-k items
        
        return result
    
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
        
        MVP: argmax over full vocab (not just within top-k).
        Returns same fields: {token_id, token_text, prob, logprob}
        
        Uses log_softmax for numerical stability, keeps everything as tensors until the end.
        
        Clamps k to [5, 30] in the adapter (for future stochastic mode).
        """
        # Clamp k to [5, 30] in the adapter (for future use in stochastic mode)
        k = max(self.TOP_K_MIN, min(self.TOP_K_MAX, k))
        
        # Convert to tensor once - keep as tensor until the very end
        logits_tensor = torch.tensor(logits, dtype=torch.float32)
        
        # Compute log_probs using log_softmax (numerically stable)
        log_probs = torch.log_softmax(logits_tensor, dim=-1)
        
        if mode == "argmax":
            # MVP: argmax over full vocab (not just within top-k)
            # Use argmax on log_probs (equivalent to argmax on probs, but more stable)
            chosen_idx = torch.argmax(log_probs).item()
            chosen_logprob = log_probs[chosen_idx].item()
            
            # Convert to Python/JSON only at the very end
            token_id = int(chosen_idx)
            # Get exact token string using convert_ids_to_tokens (preserves token semantics)
            token_obj = self.tokenizer.convert_ids_to_tokens([token_id])[0]
            # Use decode with clean_up_tokenization_spaces=False for raw text
            token_text_raw = self.tokenizer.decode([token_id], clean_up_tokenization_spaces=False)
            # Create display version
            token_text_display = make_token_display(token_text_raw)
            
            # Convert logprob and prob at the very end
            logprob = float(chosen_logprob)
            prob = float(math.exp(chosen_logprob))
            # Compute surprisal = -log(prob + epsilon)
            surprisal = float(-math.log(prob + 1e-12))
            
            return {
                "token_id": token_id,
                "token_text": token_text_raw,  # Keep for backward compatibility
                "token_text_raw": token_text_raw,
                "token_text_display": token_text_display,
                "prob": prob,
                "logprob": logprob,
                "surprisal": surprisal
            }
        
        elif mode == "stochastic":
            # Stochastic sampling with temperature and top-p
            # Start from last logits
            logits_scaled = logits_tensor / (temperature if temperature is not None and temperature > 0 else 1.0)
            
            # Convert to probs
            probs = torch.softmax(logits_scaled, dim=-1)
            
            # Apply nucleus (top-p) filter if specified
            if top_p is not None and top_p < 1.0:
                # Sort probabilities in descending order
                sorted_probs, sorted_indices = torch.sort(probs, descending=True)
                # Compute cumulative probabilities
                cumsum_probs = torch.cumsum(sorted_probs, dim=-1)
                # Find the smallest set with cumulative >= top_p
                # Create a mask for tokens to keep
                mask = cumsum_probs <= top_p
                # Always keep at least the top token
                if not mask.any():
                    mask[0] = True
                # Create full mask for original indices
                filtered_probs = torch.zeros_like(probs)
                filtered_probs[sorted_indices[mask]] = sorted_probs[mask]
                # Renormalize
                filtered_probs = filtered_probs / filtered_probs.sum()
                probs = filtered_probs
            
            # Sample 1 token from the distribution
            chosen_idx = torch.multinomial(probs, num_samples=1).item()
            chosen_prob = probs[chosen_idx].item()
            chosen_logprob = torch.log(probs[chosen_idx] + 1e-10).item()  # Add small epsilon for numerical stability
            
            # Convert to Python/JSON only at the very end
            token_id = int(chosen_idx)
            # Get exact token string using convert_ids_to_tokens (preserves token semantics)
            token_obj = self.tokenizer.convert_ids_to_tokens([token_id])[0]
            # Use decode with clean_up_tokenization_spaces=False for raw text
            token_text_raw = self.tokenizer.decode([token_id], clean_up_tokenization_spaces=False)
            # Create display version
            token_text_display = make_token_display(token_text_raw)
            
            # Compute surprisal = -log(prob + epsilon)
            surprisal = float(-math.log(chosen_prob + 1e-12))
            
            return {
                "token_id": token_id,
                "token_text": token_text_raw,  # Keep for backward compatibility
                "token_text_raw": token_text_raw,
                "token_text_display": token_text_display,
                "prob": float(chosen_prob),
                "logprob": float(chosen_logprob),
                "surprisal": surprisal
            }
        
        else:
            raise ValueError(f"Unsupported mode: {mode}")
    
    @property
    def vocab_size(self) -> int:
        """Get vocabulary size."""
        return self.tokenizer.vocab_size

