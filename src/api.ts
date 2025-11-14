import type { NextDistRequest, NextDistResponse, StepRequest, StepResponse } from './types';

const API_BASE = 'http://localhost:8000';

export async function getNextDist(request: NextDistRequest): Promise<NextDistResponse> {
  const response = await fetch(`${API_BASE}/next_dist`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ status: 'error', message: response.statusText }));
    throw errorData;
  }

  return response.json();
}

// Normalize and sanitize token info
function normalizeTokenInfo(item: any) {
  return {
    token_id: Number(item.token_id ?? -1),
    token_text: String(item.token_text ?? ''),
    token_text_raw: item.token_text_raw ? String(item.token_text_raw) : String(item.token_text ?? ''),
    token_text_display: item.token_text_display ? String(item.token_text_display) : String(item.token_text ?? ''),
    prob: Number(item.prob ?? 0),
    logprob: Number(item.logprob ?? 0),
    surprisal: item.surprisal !== undefined ? Number(item.surprisal ?? 0) : undefined,
  };
}

// Normalize and sanitize step response
function normalizeStepResponse(data: any): StepResponse {
  // Validate required fields
  if (!data || !Array.isArray(data.topk) || !data.chosen) {
    throw new Error('Invalid response: missing topk or chosen');
  }

  return {
    ...data,
    context_len_tokens: Number(data.context_len_tokens ?? 0),
    topk: data.topk.map(normalizeTokenInfo),
    chosen: normalizeTokenInfo(data.chosen),
    coverage_topk: Number(data.coverage_topk ?? 0),
    used_top_k: Number(data.used_top_k ?? 10),
    append_text: String(data.append_text ?? ''),
    last_token: data.last_token || { id: null, text: null },
    model_info: data.model_info || { provider: 'hf-local', model_name: '', vocab_size: 0 },
    contract_version: String(data.contract_version ?? 'v1'),
  };
}

export async function performStep(request: StepRequest): Promise<StepResponse> {
  const response = await fetch(`${API_BASE}/step`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ status: 'error', message: response.statusText }));
    throw errorData;
  }

  const data = await response.json();
  return normalizeStepResponse(data);
}

