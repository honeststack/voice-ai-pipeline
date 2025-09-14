"""MCP (Model Context Protocol) client for integrating with Copilot.

This component allows speech transcribed by the ASR service to be converted
into prompts for Copilot, enabling voice-driven AI interactions.

Features:
- Convert transcribed speech to structured Copilot prompts
- Handle MCP protocol communication with Copilot
- Support for different prompt templates and contexts
- Error handling and retry logic
- Integration with the voice pipeline

Usage:
    from voice_ai_pipeline.mcp_client import MCPClient

    client = MCPClient()
    prompt = client.create_prompt_from_transcription("Hello, how can I help you?")
    response = client.send_to_copilot(prompt)
"""

import os
import json
import time
import requests
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum


class PromptType(Enum):
    """Types of prompts that can be generated from speech."""
    QUESTION = "question"
    COMMAND = "command"
    CODE_REQUEST = "code_request"
    GENERAL = "general"


@dataclass
class CopilotPrompt:
    """Structured prompt for Copilot."""
    text: str
    prompt_type: PromptType
    context: Dict[str, Any]
    timestamp: float
    metadata: Dict[str, Any]


class MCPClient:
    """MCP client for communicating with Copilot.

    This class handles the Model Context Protocol communication with Copilot,
    converting transcribed speech into structured prompts and managing responses.
    """

    def __init__(
        self,
        copilot_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        prompt_templates: Optional[Dict[str, str]] = None
    ):
        """Initialize the MCP client.

        Args:
            copilot_url: URL of the Copilot MCP endpoint
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            prompt_templates: Custom prompt templates for different types
        """
        self.copilot_url = copilot_url or os.getenv(
            "COPILOT_MCP_URL",
            "http://localhost:3000/mcp"
        )
        self.timeout = timeout
        self.max_retries = max_retries

        # Default prompt templates
        self.prompt_templates = prompt_templates or {
            "question": "Please help me with this question: {text}",
            "command": "Please execute this command or task: {text}",
            "code_request": "Please help me write code for: {text}",
            "general": "{text}"
        }

        # Session context for maintaining conversation state
        self.session_context = {
            "conversation_id": None,
            "last_interaction": None,
            "user_preferences": {}
        }

    def create_prompt_from_transcription(
        self,
        transcription: str,
        prompt_type: Optional[PromptType] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> CopilotPrompt:
        """Create a structured prompt from transcribed speech.

        Args:
            transcription: The transcribed text from speech
            prompt_type: Type of prompt (auto-detected if None)
            context: Additional context information

        Returns:
            Structured CopilotPrompt object
        """
        # Auto-detect prompt type if not specified
        if prompt_type is None:
            prompt_type = self._detect_prompt_type(transcription)

        # Get appropriate template
        template = self.prompt_templates.get(prompt_type.value, self.prompt_templates["general"])

        # Format the prompt
        formatted_text = template.format(text=transcription.strip())

        # Create metadata
        metadata = {
            "original_transcription": transcription,
            "word_count": len(transcription.split()),
            "detected_language": self._detect_language(transcription),
            "confidence_score": self._calculate_confidence(transcription)
        }

        # Merge with provided context
        full_context = {
            "session_id": self.session_context.get("conversation_id"),
            "timestamp": time.time(),
            **(context or {})
        }

        return CopilotPrompt(
            text=formatted_text,
            prompt_type=prompt_type,
            context=full_context,
            timestamp=time.time(),
            metadata=metadata
        )

    def send_to_copilot(
        self,
        prompt: Union[CopilotPrompt, str],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a prompt to Copilot via MCP protocol.

        Args:
            prompt: The prompt to send (CopilotPrompt object or string)
            options: Additional options for the request

        Returns:
            Response from Copilot
        """
        if isinstance(prompt, str):
            prompt = self.create_prompt_from_transcription(prompt)

        # Prepare MCP request
        mcp_request = self._prepare_mcp_request(prompt, options)

        # Send request with retry logic
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.copilot_url,
                    json=mcp_request,
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    result = response.json()
                    self._update_session_context(prompt, result)
                    return result
                else:
                    error_msg = f"MCP request failed with status {response.status_code}: {response.text}"
                    if attempt == self.max_retries - 1:
                        raise Exception(error_msg)
                    print(f"Attempt {attempt + 1} failed: {error_msg}")
                    time.sleep(2 ** attempt)  # Exponential backoff

            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise Exception(f"MCP request failed after {self.max_retries} attempts: {str(e)}")
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                time.sleep(2 ** attempt)

        raise Exception("MCP request failed after all retry attempts")

    def _prepare_mcp_request(
        self,
        prompt: CopilotPrompt,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Prepare MCP request payload.

        Args:
            prompt: The prompt to send
            options: Additional request options

        Returns:
            MCP request payload
        """
        request = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),  # Unique request ID
            "method": "copilot/chat",
            "params": {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt.text,
                        "metadata": prompt.metadata
                    }
                ],
                "context": prompt.context,
                "options": {
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "model": "gpt-4",
                    **(options or {})
                }
            }
        }

        # Add conversation context if available
        if self.session_context.get("conversation_id"):
            request["params"]["conversation_id"] = self.session_context["conversation_id"]

        return request

    def _detect_prompt_type(self, transcription: str) -> PromptType:
        """Auto-detect the type of prompt from transcription.

        Args:
            transcription: The transcribed text

        Returns:
            Detected PromptType
        """
        text_lower = transcription.lower().strip()

        # Check for questions
        if any(word in text_lower for word in ["what", "how", "why", "when", "where", "who", "can you", "could you"]):
            return PromptType.QUESTION

        # Check for commands
        if any(word in text_lower for word in ["please", "can you", "would you", "help me", "create", "make", "do"]):
            # Check if it's code-related
            if any(word in text_lower for word in ["code", "function", "class", "script", "program", "write"]):
                return PromptType.CODE_REQUEST
            return PromptType.COMMAND

        return PromptType.GENERAL

    def _detect_language(self, text: str) -> str:
        """Simple language detection (can be enhanced with proper NLP library).

        Args:
            text: Text to analyze

        Returns:
            Detected language code
        """
        # Basic heuristics - in production, use a proper language detection library
        if any(char in text for char in "ñáéíóúü"):
            return "es"  # Spanish
        elif any(char in text for char in "äöüß"):
            return "de"  # German
        elif any(char in text for char in "àâäéèêëïîôùûüÿ"):
            return "fr"  # French
        else:
            return "en"  # English (default)

    def _calculate_confidence(self, text: str) -> float:
        """Calculate confidence score for the transcription.

        Args:
            text: Transcribed text

        Returns:
            Confidence score between 0 and 1
        """
        # Simple confidence calculation based on text characteristics
        # In production, this would come from the ASR model
        word_count = len(text.split())
        avg_word_length = sum(len(word) for word in text.split()) / max(word_count, 1)

        # Higher confidence for longer, more structured text
        base_confidence = min(0.9, word_count / 20)  # Max confidence at 20 words
        length_bonus = min(0.1, avg_word_length / 10)  # Bonus for longer words

        return base_confidence + length_bonus

    def _update_session_context(self, prompt: CopilotPrompt, response: Dict[str, Any]):
        """Update session context after successful interaction.

        Args:
            prompt: The prompt that was sent
            response: The response received
        """
        # Update conversation ID if provided in response
        if "conversation_id" in response:
            self.session_context["conversation_id"] = response["conversation_id"]

        # Store last interaction
        self.session_context["last_interaction"] = {
            "timestamp": time.time(),
            "prompt_type": prompt.prompt_type.value,
            "response_length": len(str(response.get("result", "")))
        }

    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information.

        Returns:
            Session context information
        """
        last_interaction = self.session_context.get("last_interaction")
        return {
            **self.session_context,
            "total_interactions": len([k for k in self.session_context.keys() if k.startswith("interaction_")]),
            "last_activity": last_interaction.get("timestamp") if last_interaction else None
        }

    def clear_session(self):
        """Clear the current session context."""
        self.session_context = {
            "conversation_id": None,
            "last_interaction": None,
            "user_preferences": {}
        }


# Convenience functions for easy integration
def create_copilot_prompt(transcription: str, **kwargs) -> CopilotPrompt:
    """Convenience function to create a Copilot prompt from transcription.

    Args:
        transcription: The transcribed speech text
        **kwargs: Additional arguments for MCPClient.create_prompt_from_transcription

    Returns:
        Structured CopilotPrompt
    """
    client = MCPClient()
    return client.create_prompt_from_transcription(transcription, **kwargs)


def send_to_copilot(transcription: str, **kwargs) -> Dict[str, Any]:
    """Convenience function to send transcription directly to Copilot.

    Args:
        transcription: The transcribed speech text
        **kwargs: Additional arguments for MCPClient.send_to_copilot

    Returns:
        Response from Copilot
    """
    client = MCPClient()
    prompt = client.create_prompt_from_transcription(transcription)
    return client.send_to_copilot(prompt, **kwargs)


if __name__ == "__main__":
    # Example usage
    client = MCPClient()

    # Test prompt creation
    transcription = "Can you help me write a Python function to calculate fibonacci numbers?"
    prompt = client.create_prompt_from_transcription(transcription)

    print(f"Original: {transcription}")
    print(f"Formatted: {prompt.text}")
    print(f"Type: {prompt.prompt_type.value}")
    print(f"Confidence: {prompt.metadata['confidence_score']:.2f}")

    # Note: Actual Copilot communication would require a running MCP server
    print("\nNote: To test Copilot integration, ensure MCP server is running at:", client.copilot_url)