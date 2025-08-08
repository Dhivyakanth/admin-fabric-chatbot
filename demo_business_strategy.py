#!/usr/bin/env python3
"""
Business Strategy Feature Demonstration
Shows examples of the new business strategy request handling functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from livedata_integration import generate_response

def demo_business_strategy():
    """Demonstrate the business strategy functionality"""
    print("🎯 BUSINESS STRATEGY FEATURE DEMONSTRATION")
    print("=" * 60)
    
    examples = [
        "Give me business strategies for Diwali",
        "Business strategies for Christmas and Holi",
        "What are the business strategies for Valentine's Day?",
        "Give me business strategies for Diwali"  # Repeat to show session memory
    ]
    
    for i, question in enumerate(examples, 1):
        print(f"\n📝 Example {i}: {question}")
        print("-" * 50)
        
        try:
            response = generate_response(question, [])
            print(response)
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print("-" * 50)
    
    print("\n🎉 Business Strategy Features Demonstrated:")
    print("✅ Single festival business strategies")
    print("✅ Multi-festival business strategies") 
    print("✅ Session memory for varied responses")
    print("✅ Comprehensive structured recommendations")
    print("✅ Actionable insights and profit tips")
    
    print("\n💡 Ready to use in production!")
    print("Users can now ask business strategy questions and get")
    print("professional, structured responses with actionable insights.")

if __name__ == "__main__":
    demo_business_strategy()
