import { useState, useRef, useEffect } from 'react';
import { performStep } from './api';
import type { StepRecord, Trace } from './types';
import './App.css';

type ViewMode = 'inspect' | 'collapsed';
type SelectionMode = 'argmax' | 'stochastic';

function App() {
  const [contextText, setContextText] = useState('');
  const [topK, setTopK] = useState(10);
  const [mode, setMode] = useState<SelectionMode>('stochastic');  // Default to stochastic
  const [temperature, setTemperature] = useState(0.8);
  const [topP, setTopP] = useState(0.95);
  const [softenNewlineEot, setSoftenNewlineEot] = useState(false);  // Hidden dev toggle
  const [viewMode, setViewMode] = useState<ViewMode>('inspect');
  const [trace, setTrace] = useState<Trace>([]);
  const [renderedText, setRenderedText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isWorking, setIsWorking] = useState(false); // For "Working..." state after 2s
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [expandedTokenIdx, setExpandedTokenIdx] = useState<number | null>(null);
  const [pulsingTokenIdx, setPulsingTokenIdx] = useState<number | null>(null);
  const [usedTopK, setUsedTopK] = useState<number | null>(null); // Track used_top_k from response
  
  const tokenRailRef = useRef<HTMLDivElement>(null);
  
  // Initialize renderedText with contextText on mount
  useEffect(() => {
    setRenderedText(contextText);
  }, []);
  
  // Update renderedText when contextText changes and there's no trace
  useEffect(() => {
    if (trace.length === 0) {
      setRenderedText(contextText);
    }
  }, [contextText, trace.length]);

  // Auto-scroll to keep newest chip visible when new token arrives
  useEffect(() => {
    if (viewMode === 'inspect' && tokenRailRef.current && trace.length > 0) {
      const rail = tokenRailRef.current;
      rail.scrollLeft = rail.scrollWidth;
    }
  }, [trace.length, viewMode]);

  const handleStep = async () => {
    if (isLoading) return;
    
    // Disable STEP while in flight
    setIsLoading(true);
    setIsWorking(false);
    setError(null);
    setToast(null);
    
    // Time budget tracking
    let timeout2s: NodeJS.Timeout | null = null;
    let timeout5s: NodeJS.Timeout | null = null;
    
    // If /step > 2s, show "Working…" on the button
    timeout2s = setTimeout(() => {
      setIsWorking(true);
    }, 2000);
    
    // If > 5s, toast: "Model slow; try again or reduce top-k."
    timeout5s = setTimeout(() => {
      setToast("Model slow; try again or reduce top-k.");
      // Auto-dismiss toast after 5 seconds
      setTimeout(() => {
        setToast(null);
      }, 5000);
    }, 5000);

    try {
      // POST /step with renderedText (empty contextText allowed for BOS)
      const response = await performStep({
        context_text: renderedText,
        top_k: topK,
        mode: mode,
        temperature: mode === 'stochastic' ? temperature : undefined,
        top_p: mode === 'stochastic' ? topP : undefined,
        soften_newline_eot: softenNewlineEot,
      });
      
      // Clear timeouts on success
      if (timeout2s) clearTimeout(timeout2s);
      if (timeout5s) clearTimeout(timeout5s);

      // Store used_top_k from response
      setUsedTopK(response.used_top_k ?? topK);

      // Validate response before setting state (normalization already done in api.ts, but double-check)
      if (!Array.isArray(response.topk) || !response.chosen) {
        throw new Error('Invalid response: missing topk or chosen');
      }

      // On success: append new StepRecord to trace
      const newRecord: StepRecord = {
        idx: trace.length,
        context_len_before: Number(response.context_len_tokens ?? 0),
        chosen: response.chosen,
        topk: response.topk,
      };

      setTrace([...trace, newRecord]);
      
      // Append res.append_text to renderedText
      setRenderedText(prev => prev + response.append_text);
      
      // Auto-expand the newest chip and show the vertical gradient list
      const newTokenIdx = trace.length;
      setExpandedTokenIdx(newTokenIdx);
      
      // Brief pulse on the chip (200-500ms) - using 400ms
      setPulsingTokenIdx(newTokenIdx);
      setTimeout(() => {
        setPulsingTokenIdx(null);
      }, 400);
    } catch (err) {
      // Clear timeouts on error
      if (timeout2s) clearTimeout(timeout2s);
      if (timeout5s) clearTimeout(timeout5s);
      
      // Handle error response format
      if (err && typeof err === 'object' && 'status' in err) {
        const errorObj = err as any;
        setError(errorObj.message || 'Unknown error occurred');
      } else {
        setError(err instanceof Error ? err.message : 'Unknown error occurred');
      }
    } finally {
      // Re-enable STEP
      setIsLoading(false);
      setIsWorking(false);
    }
  };

  const handleTokenClick = (idx: number) => {
    if (expandedTokenIdx === idx) {
      setExpandedTokenIdx(null);
    } else {
      setExpandedTokenIdx(idx);
    }
  };

  const handleCollapsedClick = () => {
    setViewMode('inspect');
  };

  // Use raw token for concatenation, display token for rendering
  const tokens = trace.map((record) => 
    record.chosen.token_text_raw || record.chosen.token_text
  );
  const tokenDisplays = trace.map((record) => 
    record.chosen.token_text_display || record.chosen.token_text
  );
  
  // Calculate max surprisal in session for normalization (or use fixed range 0-10)
  const SURPRISAL_MAX = 10;  // Fixed range max

  return (
    <div className="app">
      {/* Top bar controls */}
      <div className="top-bar">
        <div className="control-group">
          <label htmlFor="context">Context</label>
          <textarea
            id="context"
            value={contextText}
            onChange={(e) => {
              const newContext = e.target.value;
              setContextText(newContext);
              // Reset trace and renderedText when user edits context
              if (trace.length > 0) {
                setTrace([]);
                setRenderedText(newContext);
                setExpandedTokenIdx(null);
              } else {
                // If no trace, just update renderedText
                setRenderedText(newContext);
              }
            }}
            placeholder="Enter initial context (empty allowed for BOS)..."
            rows={3}
            className="context-input"
          />
        </div>

        <div className="control-group">
          <label htmlFor="topk">Top-k</label>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input
              id="topk"
              type="number"
              min={5}
              max={30}
              value={topK}
              onChange={(e) => setTopK(Math.max(5, Math.min(30, parseInt(e.target.value) || 10)))}
              className="number-input"
            />
            {usedTopK !== null && usedTopK !== topK && (
              <span style={{ fontSize: '11px', color: '#6b7280', fontStyle: 'italic' }}>
                (used: {usedTopK})
              </span>
            )}
          </div>
        </div>

        <div className="control-group">
          <label htmlFor="mode">Mode</label>
          <select
            id="mode"
            value={mode}
            onChange={(e) => setMode(e.target.value as SelectionMode)}
            className="select-input"
          >
            <option value="stochastic">Stochastic</option>
            <option value="argmax">Argmax</option>
          </select>
        </div>

        {mode === 'stochastic' && (
          <>
            <div className="control-group">
              <label htmlFor="temperature">Temperature</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  id="temperature"
                  type="range"
                  min={0.2}
                  max={1.5}
                  step={0.1}
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="slider-input"
                />
                <span style={{ fontSize: '12px', minWidth: '40px' }}>{temperature.toFixed(1)}</span>
              </div>
            </div>

            <div className="control-group">
              <label htmlFor="topp">Top-p</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  id="topp"
                  type="range"
                  min={0.7}
                  max={1.0}
                  step={0.05}
                  value={topP}
                  onChange={(e) => setTopP(parseFloat(e.target.value))}
                  className="slider-input"
                />
                <span style={{ fontSize: '12px', minWidth: '40px' }}>{topP.toFixed(2)}</span>
              </div>
            </div>
          </>
        )}

        <button
          onClick={handleStep}
          disabled={isLoading}
          className="step-button"
        >
          {isWorking ? 'Working…' : isLoading ? 'Processing...' : 'STEP'}
        </button>

        <div className="control-group">
          <button
            onClick={() => setViewMode(viewMode === 'inspect' ? 'collapsed' : 'inspect')}
            className="toggle-button"
          >
            {viewMode === 'inspect' ? 'Collapsed' : 'Inspect'}
          </button>
        </div>

        {/* Hidden dev toggle */}
        <div className="control-group" style={{ opacity: 0.5, fontSize: '11px' }}>
          <label>
            <input
              type="checkbox"
              checked={softenNewlineEot}
              onChange={(e) => setSoftenNewlineEot(e.target.checked)}
              style={{ marginRight: '4px' }}
            />
            Soften newline/EOT
          </label>
        </div>
      </div>

      {error && (
        <div className="error-message">
          Error: {error}
        </div>
      )}

      {toast && (
        <div className="toast-message">
          {toast}
        </div>
      )}

      {/* Main area */}
      <div className="main-area">
        {viewMode === 'inspect' ? (
          <div className="token-rail" ref={tokenRailRef}>
            {tokens.map((token, idx) => {
              const record = trace[idx];
              if (!record || !record.chosen) {
                return null;  // Skip invalid records
              }
              const isExpanded = expandedTokenIdx === idx;
              const isPulsing = pulsingTokenIdx === idx;

              return (
                <div
                  key={idx}
                  className={`token-chip ${isPulsing ? 'pulsing' : ''} ${isExpanded ? 'expanded' : ''}`}
                  onClick={() => handleTokenClick(idx)}
                  title={(() => {
                    const prob = Number(record.chosen.prob ?? 0);
                    const surprisal = record.chosen.surprisal !== undefined ? Number(record.chosen.surprisal ?? 0) : null;
                    if (surprisal !== null) {
                      return `surprisal = ${surprisal.toFixed(3)} prob = ${prob.toFixed(4)}`;
                    }
                    return `prob = ${prob.toFixed(4)}`;
                  })()}
                >
                  <div className="token-text">
                    {tokenDisplays[idx]}
                    <span className="token-id-label">{record.chosen.token_id}</span>
                  </div>
                  {/* Surprisal bar - only show if surprisal is defined */}
                  {record.chosen.surprisal !== undefined && (() => {
                    const surprisal = Number(record.chosen.surprisal ?? 0);
                    return (
                      <div 
                        className="surprisal-bar"
                        style={{
                          width: `${Math.min((surprisal / SURPRISAL_MAX) * 100, 100)}%`,
                          opacity: Math.min(surprisal / SURPRISAL_MAX, 1.0) * 0.6 + 0.2,
                        }}
                      />
                    );
                  })()}
                  {isExpanded && record && Array.isArray(record.topk) && record.topk.length > 0 && (() => {
                    // Normalize probabilities by max prob in this list (with defensive checks)
                    const probs = record.topk.map(c => Number(c.prob ?? 0));
                    const maxProb = Math.max(...probs, 1);  // Default to 1 to avoid division by zero
                    const coverage = probs.reduce((sum, p) => sum + p, 0);
                    const chosenTokenId = Number(record.chosen.token_id ?? -1);
                    
                    return (
                      <div className="topk-list">
                        {record.topk.map((candidate, candidateIdx) => {
                          const prob = Number(candidate.prob ?? 0);
                          const normalizedWidth = Math.max(0, Math.min(100, (prob / maxProb) * 100));
                          const isChosen = Number(candidate.token_id ?? -1) === chosenTokenId;
                          
                          return (
                            <div
                              key={candidateIdx}
                              className={`topk-item ${isChosen ? 'chosen' : ''}`}
                            >
                              <div 
                                className="topk-bar"
                                style={{
                                  width: `${normalizedWidth}%`,
                                  opacity: Math.max(0, Math.min(1, prob)),
                                }}
                              />
                              <div className="topk-labels">
                                <span className="topk-text">
                                  {candidate.token_text_display || candidate.token_text || ''}
                                  <span className="token-id-label">{Number(candidate.token_id ?? -1)}</span>
                                </span>
                                <span className="topk-prob">{prob.toFixed(4)}</span>
                              </div>
                            </div>
                          );
                        })}
                        <div className="topk-footer">
                          <span>Σprob(top-k) = {coverage.toFixed(4)}</span>
                          <span>N = {record.topk.length}</span>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="collapsed-view" onClick={handleCollapsedClick}>
            <div className="collapsed-text">{renderedText}</div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;

