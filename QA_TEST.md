# Quick QA Test Script (Manual)

## Setup

1. **Start Backend:**
   ```bash
   uvicorn main:app --reload
   ```
   - Server should start on `http://localhost:8000`
   - Model should load (Qwen/Qwen2.5-1.5B)
   - Check `/healthz` returns: `{"model_name": "Qwen/Qwen2.5-1.5B", "vocab_size": <positive integer>, "contract_version": "v1"}`

2. **Start Frontend:**
   ```bash
   npm run dev
   ```
   - Frontend should start on `http://localhost:3000`
   - UI should load with all controls visible

## Test Cases

### Test 1: Empty Context (BOS)

**Steps:**
1. Leave context textarea empty
2. Set top-k to 10
3. Click STEP

**Verify:**
- ✅ Request succeeds
- ✅ `context_len_tokens` is 0 (or very small if BOS token is added)
- ✅ New token chip appears in Inspect mode
- ✅ Chip is auto-expanded showing top-k candidates
- ✅ Chosen token is highlighted
- ✅ `renderedText` starts with the chosen token
- ✅ Collapsed view shows the generated text

### Test 2: Short Prompt

**Steps:**
1. Enter: `"The capital of France is"`
2. Set top-k to 10
3. Click STEP

**Verify:**
- ✅ Request succeeds
- ✅ `context_len_tokens` reflects the tokenized length (~6-7 tokens)
- ✅ New token chip appears with literal token text (may include leading space like `" Paris"`)
- ✅ Top-k list shows 10 candidates sorted by probability (descending)
- ✅ Chosen token is highlighted in the list
- ✅ Σprob(top-k) is displayed in footer (should be < 1.0, typically 0.7-0.95)
- ✅ Chip pulses briefly (400ms)
- ✅ Horizontal rail auto-scrolls to show newest chip
- ✅ `append_text` is plausible (often `" Paris"` with leading space)
- ✅ Collapsed view shows: `"The capital of France is" + append_text`

### Test 3: Unicode/Emoji Test

**Steps:**
1. Enter: `"Emoji test: 🔥 The"`
2. Set top-k to 10
3. Click STEP

**Verify:**
- ✅ Request succeeds
- ✅ Token chips preserve Unicode characters exactly
- ✅ Emoji appears correctly in token chips
- ✅ Top-k candidates may include Unicode tokens
- ✅ Token text is preserved exactly (no corruption)
- ✅ Collapsed view shows correct Unicode rendering

### Test 4: Multiple Steps

**Steps:**
1. Enter: `"The capital of France is"`
2. Click STEP multiple times (3-5 times)

**Verify:**
- ✅ Each STEP adds a new chip to the right
- ✅ Horizontal rail grows and auto-scrolls
- ✅ Each chip can be expanded independently
- ✅ Only one chip expanded at a time (expanding another collapses previous)
- ✅ Chosen tokens are highlighted in their respective lists
- ✅ `renderedText` accumulates correctly
- ✅ Collapsed view shows full generated text
- ✅ Chip count equals number of steps

### Test 5: Context Truncation

**Steps:**
1. Paste a very long text (~1000+ tokens, e.g., repeat a sentence many times)
2. Click STEP

**Verify:**
- ✅ `context_len_tokens` shows 512 (not the full length)
- ✅ Only last 512 tokens are used
- ✅ Request succeeds
- ✅ Generated token is based on the truncated context

### Test 6: Top-k Clamping

**Steps:**
1. Set top-k to 3 (below minimum)
2. Click STEP
3. Check if `used_top_k` is shown as 5

**Then:**
1. Set top-k to 50 (above maximum)
2. Click STEP
3. Check if `used_top_k` is shown as 30

**Verify:**
- ✅ Server clamps top-k to [5, 30]
- ✅ UI shows "(used: X)" next to input when clamped
- ✅ Response contains correct number of top-k candidates
- ✅ `used_top_k` field in response matches displayed value

### Test 7: Timeout Behavior

**Steps:**
1. Set top-k to 30 (maximum, slower)
2. Click STEP
3. Watch button state

**Verify:**
- ✅ Button shows "Processing..." immediately
- ✅ After 2s, button shows "Working…"
- ✅ After 5s, toast appears: "Model slow; try again or reduce top-k."
- ✅ Toast auto-dismisses after 5 seconds
- ✅ Request completes successfully (if under timeout)

### Test 8: View Toggle

**Steps:**
1. Generate 3-5 tokens using STEP
2. Toggle to Collapsed view
3. Verify text matches concatenated tokens
4. Click collapsed text to return to Inspect
5. Verify all chips are still present

**Verify:**
- ✅ Collapsed view shows `renderedText` exactly
- ✅ Text matches: `contextText + all chosen tokens`
- ✅ Clicking collapsed text toggles back to Inspect
- ✅ All chips are rebuilt from trace (no network calls)
- ✅ Expanded state is preserved (if any chip was expanded)

### Test 9: Error Handling

**Steps:**
1. Stop the backend server
2. Try to click STEP
3. Verify error message appears

**Verify:**
- ✅ Error message is displayed
- ✅ UI remains stable (doesn't crash)
- ✅ Button is re-enabled
- ✅ Can retry after fixing backend

### Test 10: Probability Verification

**Steps:**
1. Enter any prompt
2. Click STEP
3. Expand the chip and inspect top-k list

**Verify:**
- ✅ Probabilities are sorted descending
- ✅ All probabilities are between 0 and 1
- ✅ Σprob(top-k) is displayed in footer
- ✅ Coverage is typically 0.7-0.95 (not 1.0, since it's top-k not full vocab)
- ✅ Chosen token has highest probability (for argmax mode)
- ✅ Chosen token is highlighted (thicker border, bold labels)

## Expected Results Summary

- ✅ Empty context works (BOS)
- ✅ Short prompts generate plausible tokens
- ✅ Unicode/emoji preserved correctly
- ✅ Multiple steps accumulate correctly
- ✅ Long contexts truncate to 512 tokens
- ✅ Top-k clamping works and is displayed
- ✅ Timeout feedback appears appropriately
- ✅ View toggle works without network calls
- ✅ Error handling is graceful
- ✅ Probabilities are correct and sorted

## Quick Verification Checklist

- [ ] Backend starts and loads model
- [ ] Frontend connects to backend
- [ ] Empty context (BOS) works
- [ ] Short prompt generates token
- [ ] Unicode preserved
- [ ] Multiple steps work
- [ ] Truncation to 512 tokens
- [ ] Top-k clamping visible
- [ ] Timeout feedback works
- [ ] View toggle works
- [ ] Error handling works
- [ ] Probabilities sorted and correct

