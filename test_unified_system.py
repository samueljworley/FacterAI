#!/usr/bin/env python3
"""
Test script for the new unified retrieval and generation system
"""
import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.unified_controller import unified_controller

async def test_unified_system():
    """Test the unified system with a sample query"""
    print("🧪 Testing Unified Retrieval and Generation System")
    print("=" * 50)
    
    # Test query
    query = "What are the effects of exercise on cognitive function?"
    print(f"Query: {query}")
    print()
    
    try:
        # Process the query
        result = await unified_controller.process_query(query, "research")
        
        if result["success"]:
            print("✅ SUCCESS!")
            print(f"Request ID: {result['request_id']}")
            print(f"Total chunks: {result['total_chunks']}")
            print(f"Retrieval latency: {result['retrieval_latency_ms']:.1f}ms")
            print(f"Summary latency: {result['summary_latency_ms']:.1f}ms")
            print(f"Answer latency: {result['answer_latency_ms']:.1f}ms")
            print()
            
            print("📋 SUMMARY:")
            print("-" * 30)
            print(result['summary'])
            print()
            
            print("💡 DETAILED ANSWER:")
            print("-" * 30)
            print(result['answer'])
            print()
            
            print("📚 CITATIONS:")
            print("-" * 30)
            for i, citation in enumerate(result['citations'][:3], 1):
                print(f"{i}. {citation['title']}")
                if citation['pmid']:
                    print(f"   PMID: {citation['pmid']}")
                print()
        else:
            print("❌ FAILED!")
            print(f"Error: {result['error']}")
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_unified_system())
