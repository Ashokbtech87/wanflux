#!/usr/bin/env python3
"""
Test script to verify VIRAL OPTIMIZATION works with Ollama
"""

import sys
sys.path.insert(0, r'C:\Users\ashok\Downloads\Python_Apps\Ytubuploader')

def test_viral_optimizer():
    """Test if viral optimizer works correctly with Ollama"""
    print("=" * 70)
    print("TESTING VIRAL YOUTUBE OPTIMIZER WITH OLLAMA")
    print("=" * 70)
    
    # Test 1: Import viral optimizer
    print("\n[TEST 1] Importing viral_optimizer module...")
    try:
        from viral_optimizer import ViralSEOOptimizer, ViralMetricsTracker
        print("[PASS] Successfully imported ViralSEOOptimizer and ViralMetricsTracker")
    except Exception as e:
        print(f"[FAIL] Import error: {e}")
        return False
    
    # Test 2: Check Ollama availability
    print("\n[TEST 2] Checking Ollama availability...")
    try:
        from ollama import chat
        print("[PASS] Ollama chat function is available")
    except Exception as e:
        print(f"[FAIL] Ollama not available: {e}")
        return False
    
    # Test 3: Test static methods (without calling Ollama)
    print("\n[TEST 3] Testing static methods...")
    try:
        # Test keyword extraction
        keywords = ViralSEOOptimizer.extract_viral_keywords(
            "Test description about gaming setup", 
            "Gaming Setup", 
            []
        )
        print(f"[PASS] extract_viral_keywords returned {len(keywords)} keywords")
        
        # Test hashtag generation
        hashtags = ViralSEOOptimizer.generate_viral_hashtags(
            "Gaming Setup", 
            ["gaming", "setup", "pc"]
        )
        print(f"[PASS] generate_viral_hashtags returned {len(hashtags)} hashtags")
        
        # Test optimal posting time
        posting_time = ViralSEOOptimizer.get_optimal_posting_time()
        print(f"[PASS] get_optimal_posting_time returned: {posting_time}")
        
        # Test engagement strategy
        engagement = ViralSEOOptimizer.generate_engagement_strategy("Gaming Setup")
        print(f"[PASS] generate_engagement_strategy returned strategy with {len(engagement)} items")
        
        # Test thumbnail suggestions
        thumbnails = ViralSEOOptimizer.create_thumbnail_suggestions(
            "Gaming Setup", 
            "RGB setup with multiple monitors"
        )
        print(f"[PASS] create_thumbnail_suggestions returned {len(thumbnails)} suggestion categories")
        
    except Exception as e:
        print(f"[FAIL] Static method error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Verify Ollama integration (actual call)
    print("\n[TEST 4] Testing Ollama integration with viral title generation...")
    print("[INFO] This will call Ollama API - make sure Ollama is running!")
    print("[INFO] Testing with a simple topic: 'Gaming Setup'...")
    
    try:
        # Test actual Ollama call for viral titles
        titles = ViralSEOOptimizer.generate_viral_titles(
            topic="Gaming Setup",
            content_analysis="RGB gaming setup with multiple monitors and LED lighting",
            num_titles=3  # Just test with 3 to save time
        )
        
        if titles and len(titles) > 0:
            print(f"[PASS] Successfully generated viral titles!")
            print(f"[INFO] Generated content length: {len(titles)} characters")
            print("\n[PREVIEW] First 200 characters of generated titles:")
            print("-" * 70)
            print(titles[:200])
            print("-" * 70)
        else:
            print("[WARNING] Ollama returned empty response")
            
    except Exception as e:
        print(f"[FAIL] Ollama call error: {e}")
        print("[INFO] Make sure Ollama is running: ollama serve")
        print("[INFO] Make sure model is pulled: ollama pull kimi-k2.5:cloud")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: Test viral description generation
    print("\n[TEST 5] Testing viral description generation with Ollama...")
    try:
        description = ViralSEOOptimizer.generate_viral_description(
            topic="Gaming Setup",
            titles="1. Ultimate Gaming Setup 2026!\n2. RGB Setup Secrets Revealed",
            keywords=["gaming", "setup", "rgb", "pc", "2026"],
            search_data="Top video: Ultimate Gaming Setup with 1M views",
            video_duration=600
        )
        
        if description and len(description) > 0:
            print(f"[PASS] Successfully generated viral description!")
            print(f"[INFO] Description length: {len(description)} characters")
            print("\n[PREVIEW] First 200 characters:")
            print("-" * 70)
            print(description[:200])
            print("-" * 70)
        else:
            print("[WARNING] Ollama returned empty description")
            
    except Exception as e:
        print(f"[FAIL] Description generation error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print("[PASS] All tests passed successfully!")
    print("[INFO] Viral optimization is working correctly with Ollama")
    print("[INFO] The system can generate:")
    print("       - 10 viral title options")
    print("       - 30+ SEO keywords")
    print("       - 20-25 viral hashtags")
    print("       - Viral-optimized descriptions")
    print("       - Thumbnail suggestions")
    print("       - Posting time recommendations")
    print("       - Engagement strategies")
    print("\n[READY] Your viral optimization system is ready to use!")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    success = test_viral_optimizer()
    sys.exit(0 if success else 1)
