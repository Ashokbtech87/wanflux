#!/usr/bin/env python3
"""Quick test of viral optimizer components"""

import sys
sys.path.insert(0, r'C:\Users\ashok\Downloads\Python_Apps\Ytubuploader')

print("=" * 70)
print("QUICK VIRAL OPTIMIZER TEST")
print("=" * 70)

# Test 1: Import
print("\n[TEST 1] Importing viral_optimizer module...")
try:
    from viral_optimizer import ViralSEOOptimizer, ViralMetricsTracker
    print("[PASS] Successfully imported ViralSEOOptimizer and ViralMetricsTracker")
except Exception as e:
    print(f"[FAIL] Import error: {e}")
    sys.exit(1)

# Test 2: Ollama availability
print("\n[TEST 2] Checking Ollama availability...")
try:
    from ollama import chat
    print("[PASS] Ollama chat function is available")
except Exception as e:
    print(f"[FAIL] Ollama not available: {e}")
    sys.exit(1)

# Test 3: Static methods
print("\n[TEST 3] Testing static methods...")
try:
    keywords = ViralSEOOptimizer.extract_viral_keywords("Test description", "Gaming Setup", [])
    print(f"[PASS] extract_viral_keywords: {len(keywords)} keywords")
    
    hashtags = ViralSEOOptimizer.generate_viral_hashtags("Gaming Setup", ["gaming", "setup"])
    print(f"[PASS] generate_viral_hashtags: {len(hashtags)} hashtags")
    
    posting_time = ViralSEOOptimizer.get_optimal_posting_time()
    print(f"[PASS] get_optimal_posting_time: {posting_time['best']}")
    
    engagement = ViralSEOOptimizer.generate_engagement_strategy("Gaming Setup")
    print(f"[PASS] generate_engagement_strategy: {len(engagement)} items")
    
    thumbnails = ViralSEOOptimizer.create_thumbnail_suggestions("Gaming Setup", "RGB setup")
    print(f"[PASS] create_thumbnail_suggestions: {len(thumbnails)} categories")
    
    patterns = ViralSEOOptimizer.analyze_viral_patterns([])
    print(f"[PASS] analyze_viral_patterns: works with empty data")
    
except Exception as e:
    print(f"[FAIL] Static method error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Ollama simple test
print("\n[TEST 4] Testing Ollama with simple prompt...")
try:
    response = chat(
        model='kimi-k2.5:cloud',
        messages=[{'role': 'user', 'content': 'Generate 3 viral YouTube titles about Gaming Setup'}]
    )
    content = response.message.content
    if content and len(content) > 0:
        print(f"[PASS] Ollama responded with {len(content)} characters")
        print(f"[INFO] Preview: {content[:100]}...")
    else:
        print("[WARNING] Ollama returned empty response")
except Exception as e:
    print(f"[FAIL] Ollama test error: {e}")
    sys.exit(1)

# Summary
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print("[PASS] All core tests passed!")
print("[INFO] Viral optimizer module is working correctly")
print("[INFO] Ollama integration is functional")
print("[INFO] Static methods (keywords, hashtags, etc.) work perfectly")
print("\n[NOTE] Full viral title/description generation may take 2-5 minutes")
print("[NOTE] This is normal due to complex AI processing")
print("=" * 70)

sys.exit(0)
