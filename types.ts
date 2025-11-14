/**
 * FROZEN CONTRACTS - DO NOT CHANGE AFTER INITIAL TICKET
 * 
 * TypeScript type definitions for client-side use.
 * These types must remain stable.
 */

// ============================================================================
// API Request/Response Types
// ============================================================================

export interface TokenInfo {
  token_id: number;
  token_text: string;
  prob: number;
  logprob: number;
}

export interface ChosenToken {
  token_id: number;
  token_text: string;
  prob: number;
  logprob: number;
}

export interface LastToken {
  id: number | null;
  text: string | null;
}

export interface ModelInfo {
  provider: "hf-local";
  model_name: string;
  vocab_size: number;
}

export interface NextDistRequest {
  context_text: string;
  top_k: number;
}

export interface NextDistResponse {
  context_len_tokens: number;
  topk: TokenInfo[];
  coverage_topk: number;
  last_token: LastToken;
  model_info: ModelInfo;
}

export interface StepRequest {
  context_text: string;
  top_k: number;
  mode: "argmax" | "stochastic";
}

export interface StepResponse extends NextDistResponse {
  chosen: ChosenToken;
  append_text: string;
}

// ============================================================================
// Session Trace Types (Client Memory Only)
// ============================================================================

export interface StepRecord {
  idx: number;
  context_len_before: number;
  chosen: ChosenToken;
  topk: TokenInfo[];
}

export type Trace = Array<StepRecord>;

