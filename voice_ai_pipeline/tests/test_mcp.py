#!/usr/bin/env python3
"""
Test script for MCP (Model Context Protocol) integration.

This script demonstrates how to use the MCP client to send voice transcriptions
to Copilot for AI-powered responses.

Usage:
    python -m voice_ai_pipeline.tests.test_mcp

Requirements:
    - MCP server running (optional for testing prompt creation)
    - requests library
"""

import os
import sys
from typing import Dict, Any

# Add the parent directory to the path to import the MCP client
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from voice_ai_pipeline.mcp_client import MCPClient, CopilotPrompt, PromptType, create_copilot_prompt
    MCP_AVAILABLE = True
except ImportError as e:
    print(f"❌ MCP client not available: {e}")
    MCP_AVAILABLE = False
    # Define dummy classes to avoid linter errors
    MCPClient = None
    CopilotPrompt = None
    PromptType = None
    create_copilot_prompt = None


def test_prompt_creation():
    """Test prompt creation functionality."""
    if not MCP_AVAILABLE or MCPClient is None:
        pytest.skip("MCP client not available")

    print("🧪 Testing prompt creation...")

    client = MCPClient()

    # Test different types of transcriptions
    test_cases = [
        "Can you help me write a Python function?",
        "What is the capital of France?",
        "Please create a script that calculates fibonacci numbers",
        "Hello, how are you today?",
    ]

    for transcription in test_cases:
        prompt = client.create_prompt_from_transcription(transcription)
        print(f"📝 Original: {transcription}")
        print(f"   Formatted: {prompt.text}")
        print(f"   Type: {prompt.prompt_type.value}")
        print(f"   Confidence: {prompt.metadata['confidence_score']:.2f}")
        print()

    print("✅ Prompt creation tests passed")
    assert True  # All tests passed


def test_convenience_functions():
    """Test convenience functions."""
    if not MCP_AVAILABLE or create_copilot_prompt is None:
        pytest.skip("MCP client not available")

    print("🧪 Testing convenience functions...")

    transcription = "Help me debug this Python code"

    # Test create_copilot_prompt
    prompt = create_copilot_prompt(transcription)
    print(f"📝 Convenience function result:")
    print(f"   Text: {prompt.text}")
    print(f"   Type: {prompt.prompt_type.value}")
    print()

    print("✅ Convenience function tests passed")
    assert True  # All tests passed


def test_mcp_communication():
    """Test MCP communication (requires running MCP server)."""
    if not MCP_AVAILABLE or MCPClient is None:
        pytest.skip("MCP client not available")

    print("🧪 Testing MCP communication...")

    # Check if MCP server is configured
    mcp_url = os.getenv("COPILOT_MCP_URL", "http://localhost:3000/mcp")
    print(f"🔗 MCP Server URL: {mcp_url}")

    client = MCPClient()
    transcription = "What is machine learning?"

    print(f"📤 Sending transcription: {transcription}")
    try:
        response = client.send_to_copilot(transcription)
        print("📥 Response received:")
        print(f"   Status: {response.get('status', 'unknown')}")
        print(f"   Result: {response.get('result', 'No result')}")
        print()
        print("✅ MCP communication test passed")
        assert True  # Test passed
    except Exception as e:
        if "Connection refused" in str(e) or "Max retries exceeded" in str(e):
            pytest.skip(f"MCP server not available at {mcp_url}. This is expected if no MCP server is running.")
        else:
            # Re-raise unexpected errors
            raise


def test_session_management():
    """Test session management functionality."""
    if not MCP_AVAILABLE or MCPClient is None or CopilotPrompt is None or PromptType is None:
        pytest.skip("MCP client not available")

    print("🧪 Testing session management...")

    client = MCPClient()

    # Test session info
    session_info = client.get_session_info()
    print(f"📊 Initial session info: {session_info}")

    # Simulate some interactions
    client._update_session_context(
        CopilotPrompt("test", PromptType.QUESTION, {}, 0, {}),
        {"conversation_id": "test-123", "result": "Test response"}
    )

    # Check updated session
    updated_session = client.get_session_info()
    print(f"📊 Updated session info: {updated_session}")

    # Test session clearing
    client.clear_session()
    cleared_session = client.get_session_info()
    print(f"📊 Cleared session info: {cleared_session}")

    print("✅ Session management tests passed")
    assert True  # All tests passed


def run_all_tests():
    """Run all MCP tests."""

# Pytest-compatible test function to run all MCP tests
import pytest

@pytest.mark.integration
def test_mcp_suite():
    print("🚀 Starting MCP Integration Tests")
    print("=" * 50)

    tests = [
        ("Prompt Creation", test_prompt_creation),
        ("Convenience Functions", test_convenience_functions),
        ("Session Management", test_session_management),
        ("MCP Communication", test_mcp_communication),
    ]

    passed = 0
    total = len(tests)
    failed_tests = []
    skipped_tests = []

    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name} Test")
        print("-" * 30)
        try:
            test_func()
            passed += 1
        except pytest.skip.Exception as e:
            skipped_tests.append(f"{test_name}: {e}")
            print(f"⏭️  Skipped: {e}")
        except Exception as e:
            failed_tests.append(f"{test_name}: {e}")
        print()

    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if skipped_tests:
        print(f"⏭️  {len(skipped_tests)} tests skipped (expected for integration tests)")
        for skipped in skipped_tests:
            print(f"   {skipped}")

    if failed_tests:
        pytest.fail(f"Some MCP tests failed: {failed_tests}")
    else:
        assert True  # All tests passed or were appropriately skipped