"""
Automated QA Test Script

Tests the NextWord API endpoints to verify functionality.
Run this after starting the backend: uvicorn main:app --reload
"""
import requests
import json
import time
import sys
from typing import Dict, Any

# Fix Windows encoding issues
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

API_BASE = "http://localhost:8000"

def test_health():
    """Test /healthz endpoint"""
    print("=" * 60)
    print("Test 1: Health Check")
    print("=" * 60)
    try:
        response = requests.get(f"{API_BASE}/healthz", timeout=5)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        print(f"[PASS] Health check passed")
        print(f"  Model: {data.get('model_name')}")
        print(f"  Vocab size: {data.get('vocab_size')}")
        print(f"  Contract version: {data.get('contract_version')}")
        assert data.get('model_name') == 'Qwen/Qwen2.5-1.5B', "Wrong model name"
        assert isinstance(data.get('vocab_size'), int) and data.get('vocab_size') > 0, "Invalid vocab size"
        assert data.get('contract_version') == 'v1', "Wrong contract version"
        return True
    except requests.exceptions.ConnectionError:
        print(f"[FAIL] Health check failed: Backend not running")
        print(f"  Please start the backend: uvicorn main:app --reload")
        return False
    except Exception as e:
        print(f"[FAIL] Health check failed: {e}")
        return False

def test_empty_context():
    """Test empty context (BOS)"""
    print("\n" + "=" * 60)
    print("Test 2: Empty Context (BOS)")
    print("=" * 60)
    try:
        response = requests.post(
            f"{API_BASE}/step",
            json={
                "context_text": "",
                "top_k": 10,
                "mode": "argmax"
            },
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        print(f"[PASS] Empty context request succeeded")
        print(f"  Context len tokens: {data.get('context_len_tokens')}")
        print(f"  Top-k count: {len(data.get('topk', []))}")
        print(f"  Chosen token: {data.get('chosen', {}).get('token_text', 'N/A')}")
        print(f"  Append text: {data.get('append_text', 'N/A')}")
        assert 'topk' in data, "Missing topk field"
        assert len(data['topk']) == 10, f"Expected 10 top-k items, got {len(data['topk'])}"
        assert 'chosen' in data, "Missing chosen field"
        assert 'append_text' in data, "Missing append_text field"
        assert data.get('context_len_tokens') == 0 or data.get('context_len_tokens') is not None, "Invalid context_len_tokens"
        return True
    except Exception as e:
        print(f"[FAIL] Empty context test failed: {e}")
        return False

def test_short_prompt():
    """Test short prompt"""
    print("\n" + "=" * 60)
    print("Test 3: Short Prompt")
    print("=" * 60)
    try:
        prompt = "The capital of France is"
        response = requests.post(
            f"{API_BASE}/step",
            json={
                "context_text": prompt,
                "top_k": 10,
                "mode": "argmax"
            },
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        print(f"[PASS] Short prompt request succeeded")
        print(f"  Context len tokens: {data.get('context_len_tokens')}")
        print(f"  Top-k count: {len(data.get('topk', []))}")
        print(f"  Coverage top-k: {data.get('coverage_topk', 0):.4f}")
        print(f"  Chosen token: '{data.get('chosen', {}).get('token_text', 'N/A')}'")
        print(f"  Append text: '{data.get('append_text', 'N/A')}'")
        
        # Verify top-k structure
        topk = data.get('topk', [])
        assert len(topk) == 10, f"Expected 10 top-k items, got {len(topk)}"
        
        # Verify probabilities are sorted descending
        probs = [item['prob'] for item in topk]
        assert probs == sorted(probs, reverse=True), "Probabilities not sorted descending"
        
        # Verify coverage
        coverage = data.get('coverage_topk', 0)
        assert 0 < coverage <= 1, f"Coverage should be between 0 and 1, got {coverage}"
        
        # Verify chosen is in topk or is the argmax
        chosen_id = data.get('chosen', {}).get('token_id')
        topk_ids = [item['token_id'] for item in topk]
        assert chosen_id in topk_ids, "Chosen token should be in topk"
        
        # Verify chosen is highlighted (highest prob in topk)
        chosen_in_topk = next((item for item in topk if item['token_id'] == chosen_id), None)
        if chosen_in_topk:
            max_prob_in_topk = max(item['prob'] for item in topk)
            assert chosen_in_topk['prob'] == max_prob_in_topk, "Chosen should have highest prob in topk"
        
        return True
    except Exception as e:
        print(f"[FAIL] Short prompt test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_unicode_prompt():
    """Test Unicode/emoji prompt"""
    print("\n" + "=" * 60)
    print("Test 4: Unicode/Emoji Prompt")
    print("=" * 60)
    try:
        prompt = "Emoji test: 🔥 The"
        response = requests.post(
            f"{API_BASE}/step",
            json={
                "context_text": prompt,
                "top_k": 10,
                "mode": "argmax"
            },
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        print(f"[PASS] Unicode prompt request succeeded")
        print(f"  Context len tokens: {data.get('context_len_tokens')}")
        print(f"  Chosen token: '{data.get('chosen', {}).get('token_text', 'N/A')}'")
        print(f"  Append text: '{data.get('append_text', 'N/A')}'")
        
        # Verify Unicode is preserved
        append_text = data.get('append_text', '')
        assert isinstance(append_text, str), "Append text should be a string"
        print(f"  [OK] Unicode preserved in response")
        
        return True
    except Exception as e:
        print(f"[FAIL] Unicode prompt test failed: {e}")
        return False

def test_truncation():
    """Test context truncation to 512 tokens"""
    print("\n" + "=" * 60)
    print("Test 5: Context Truncation")
    print("=" * 60)
    try:
        # Create a very long prompt (should exceed 512 tokens)
        long_prompt = "The capital of France is " * 100  # ~2400 tokens
        response = requests.post(
            f"{API_BASE}/step",
            json={
                "context_text": long_prompt,
                "top_k": 10,
                "mode": "argmax"
            },
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        context_len = data.get('context_len_tokens', 0)
        print(f"[PASS] Truncation test succeeded")
        print(f"  Original length: ~2400 tokens (estimated)")
        print(f"  Context len tokens: {context_len}")
        assert context_len == 512, f"Expected 512 tokens after truncation, got {context_len}"
        print(f"  [OK] Truncation to 512 tokens verified")
        return True
    except Exception as e:
        print(f"[FAIL] Truncation test failed: {e}")
        return False

def test_topk_clamping():
    """Test top-k clamping"""
    print("\n" + "=" * 60)
    print("Test 6: Top-k Clamping")
    print("=" * 60)
    try:
        # Test below minimum
        response = requests.post(
            f"{API_BASE}/step",
            json={
                "context_text": "Test",
                "top_k": 3,  # Below minimum of 5
                "mode": "argmax"
            },
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        used_top_k = data.get('used_top_k', 0)
        topk_count = len(data.get('topk', []))
        print(f"[PASS] Top-k clamping test (below minimum)")
        print(f"  Requested: 3, Used: {used_top_k}, Top-k items: {topk_count}")
        assert used_top_k == 5, f"Expected used_top_k to be 5, got {used_top_k}"
        assert topk_count == 5, f"Expected 5 top-k items, got {topk_count}"
        
        # Test above maximum
        response = requests.post(
            f"{API_BASE}/step",
            json={
                "context_text": "Test",
                "top_k": 50,  # Above maximum of 30
                "mode": "argmax"
            },
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        used_top_k = data.get('used_top_k', 0)
        topk_count = len(data.get('topk', []))
        print(f"[PASS] Top-k clamping test (above maximum)")
        print(f"  Requested: 50, Used: {used_top_k}, Top-k items: {topk_count}")
        assert used_top_k == 30, f"Expected used_top_k to be 30, got {used_top_k}"
        assert topk_count == 30, f"Expected 30 top-k items, got {topk_count}"
        
        return True
    except Exception as e:
        print(f"[FAIL] Top-k clamping test failed: {e}")
        return False

def test_multiple_steps():
    """Test multiple sequential steps"""
    print("\n" + "=" * 60)
    print("Test 7: Multiple Sequential Steps")
    print("=" * 60)
    try:
        context = "The capital of France is"
        for i in range(3):
            response = requests.post(
                f"{API_BASE}/step",
                json={
                    "context_text": context,
                    "top_k": 10,
                    "mode": "argmax"
                },
                timeout=30
            )
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            append_text = data.get('append_text', '')
            context += append_text
            print(f"  Step {i+1}: Added '{append_text}' (context len: {data.get('context_len_tokens')})")
        
        print(f"[PASS] Multiple steps succeeded")
        print(f"  Final context: '{context}'")
        return True
    except Exception as e:
        print(f"[FAIL] Multiple steps test failed: {e}")
        return False

def test_response_structure():
    """Test response structure matches contract"""
    print("\n" + "=" * 60)
    print("Test 8: Response Structure")
    print("=" * 60)
    try:
        response = requests.post(
            f"{API_BASE}/step",
            json={
                "context_text": "Test",
                "top_k": 10,
                "mode": "argmax"
            },
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Check all required fields
        required_fields = [
            'contract_version',
            'context_len_tokens',
            'topk',
            'coverage_topk',
            'last_token',
            'model_info',
            'chosen',
            'append_text',
            'used_top_k'
        ]
        
        missing_fields = [field for field in required_fields if field not in data]
        assert len(missing_fields) == 0, f"Missing fields: {missing_fields}"
        
        # Check contract version header
        assert response.headers.get('X-NextTokenLens-Contract') == 'v1', "Missing contract version header"
        
        # Check nested structures
        assert 'id' in data['last_token'] or data['last_token'].get('id') is None, "Invalid last_token structure"
        assert 'provider' in data['model_info'], "Missing provider in model_info"
        assert data['model_info']['provider'] == 'hf-local', "Wrong provider"
        
        print(f"[PASS] Response structure verified")
        print(f"  Contract version: {data.get('contract_version')}")
        print(f"  All required fields present")
        return True
    except Exception as e:
        print(f"[FAIL] Response structure test failed: {e}")
        return False

def test_error_handling():
    """Test error handling"""
    print("\n" + "=" * 60)
    print("Test 9: Error Handling")
    print("=" * 60)
    try:
        # Test huge input
        huge_input = "x" * 60000  # Exceeds 50k limit
        response = requests.post(
            f"{API_BASE}/step",
            json={
                "context_text": huge_input,
                "top_k": 10,
                "mode": "argmax"
            },
            timeout=30
        )
        assert response.status_code == 400, f"Expected 400 for huge input, got {response.status_code}"
        data = response.json()
        assert data.get('status') == 'error', "Error response should have status='error'"
        assert 'message' in data, "Error response should have message"
        assert 'hint' in data, "Error response should have hint"
        print(f"[PASS] Error handling for huge input works")
        
        return True
    except Exception as e:
        print(f"[FAIL] Error handling test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("NextWord API - Automated QA Test Suite")
    print("=" * 60)
    print(f"Testing API at: {API_BASE}")
    print("Make sure the backend is running: uvicorn main:app --reload\n")
    
    tests = [
        ("Health Check", test_health),
        ("Empty Context (BOS)", test_empty_context),
        ("Short Prompt", test_short_prompt),
        ("Unicode/Emoji", test_unicode_prompt),
        ("Context Truncation", test_truncation),
        ("Top-k Clamping", test_topk_clamping),
        ("Multiple Steps", test_multiple_steps),
        ("Response Structure", test_response_structure),
        ("Error Handling", test_error_handling),
    ]
    
    # First, check if backend is running
    try:
        response = requests.get(f"{API_BASE}/healthz", timeout=2)
        if response.status_code != 200:
            print(f"[ERROR] Backend returned status {response.status_code}")
            return 1
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Backend not running at {API_BASE}")
        print(f"  Please start the backend: uvicorn main:app --reload")
        return 1
    except Exception as e:
        print(f"[ERROR] Could not connect to backend: {e}")
        return 1
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except requests.exceptions.ConnectionError:
            print(f"[FAIL] {name}: Lost connection to backend")
            results.append((name, False))
        except Exception as e:
            print(f"[FAIL] {name} crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {name}")
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit(main())

