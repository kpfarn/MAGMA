#!/usr/bin/env python3
"""
Test script to verify LLM configuration and basic functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.llm_interface import LLMInterface

def test_llm_config():
    print("Testing LLM configuration...")
    
    try:
        # Initialize LLM interface
        llm = LLMInterface()
        print(f"✓ LLM Interface initialized")
        print(f"  Model ID: {llm.model_id}")
        print(f"  Temperature: {llm.temperature}")
        print(f"  Max tokens: {llm.max_tokens}")
        print(f"  System prompt loaded: {len(llm.system_prompt)} characters")
        
        # Test loading the model (this will download if needed)
        print("\nLoading model...")
        llm.load()
        print("✓ Model loaded successfully")
        
        # Test basic inference
        print("\nTesting basic inference...")
        test_data = {
            "market_data": {
                "prices": {
                    "AAPL": [{"date": "2024-01-01", "close": 150.0}]
                },
                "news": []
            },
            "portfolio": {
                "holdings": [{"ticker": "AAPL", "shares": 10, "avg_cost": 145.0}]
            }
        }
        
        result = llm.get_recommendations(test_data, test_data["portfolio"])
        print("✓ Inference completed successfully")
        print(f"  Model used: {result.get('model', 'unknown')}")
        print(f"  Response length: {len(result.get('text', ''))} characters")
        print(f"  Response preview: {result.get('text', '')[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_llm_config()
    if success:
        print("\n🎉 LLM configuration test passed!")
    else:
        print("\n❌ LLM configuration test failed!")
        sys.exit(1)

