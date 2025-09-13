#!/usr/bin/env python3
"""
Text Summarization Component for TTS AI Pipeline

This component provides text summarization capabilities for transcribed audio content
using pre-trained transformer models.

Features:
- Automatic text summarization using BART or T5 models
- Configurable summary length and quality
- Fallback to extractive summarization if transformers unavailable
- Batch processing support
- Error handling and performance optimization

Requirements:
    - transformers>=4.40.0
    - sentencepiece>=0.2.0
    - torch (already included in main requirements)
"""

import re
import os
from typing import Optional, List, Dict, Any, Union
from collections import Counter

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    pipeline = None
    AutoTokenizer = None
    AutoModelForSeq2SeqLM = None
    torch = None
    TRANSFORMERS_AVAILABLE = False


class TextSummarizer:
    """Text summarization component using transformer models."""

    def __init__(self, model_name: str = "facebook/bart-large-cnn",
                 device: Optional[str] = None, max_length: int = 150,
                 min_length: int = 30):
        """
        Initialize the text summarizer.

        Args:
            model_name: HuggingFace model name for summarization
            device: Device to run model on ('cpu', 'cuda', 'auto', or None for auto-detect)
            max_length: Maximum length of generated summary
            min_length: Minimum length of generated summary
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("Transformers library is not available. Please install with: pip install transformers sentencepiece")

        self.model_name = model_name
        self.max_length = max_length
        self.min_length = min_length

        # Determine device
        if device == 'auto' or device is None:
            self.device = 0 if torch.cuda.is_available() else -1
        elif device == 'cpu':
            self.device = -1
        elif device == 'cuda':
            self.device = 0
        else:
            self.device = int(device) if device.isdigit() else -1

        self.summarizer = None
        self._load_model()

    def _load_model(self):
        """Load the summarization model."""
        try:
            print(f"🤖 Loading summarization model: {self.model_name}")
            self.summarizer = pipeline(
                "summarization",
                model=self.model_name,
                tokenizer=self.model_name,
                device=self.device,
                max_length=self.max_length,
                min_length=self.min_length,
                do_sample=False
            )
            print("✅ Summarization model loaded successfully")

        except Exception as e:
            print(f"❌ Failed to load summarization model: {e}")
            print("🔄 Falling back to extractive summarization")
            self.summarizer = None

    def summarize(self, text: str, max_length: Optional[int] = None,
                  min_length: Optional[int] = None) -> str:
        """
        Summarize the given text.

        Args:
            text: Text to summarize
            max_length: Maximum summary length (overrides instance setting)
            min_length: Minimum summary length (overrides instance setting)

        Returns:
            Summarized text
        """
        if not text or not text.strip():
            return "No text provided for summarization."

        # Clean and preprocess text
        text = self._preprocess_text(text)

        # Use instance defaults if not specified
        max_len = max_length or self.max_length
        min_len = min_length or self.min_length

        try:
            if self.summarizer:
                # Use transformer model
                summary = self._summarize_with_model(text, max_len, min_len)
            else:
                # Fallback to extractive summarization
                summary = self._extractive_summarize(text, max_len)

            return summary.strip()

        except Exception as e:
            print(f"❌ Summarization failed: {e}")
            return self._fallback_summary(text, max_len)

    def _summarize_with_model(self, text: str, max_length: int, min_length: int) -> str:
        """Summarize using transformer model."""
        # Handle text length limits
        max_input_length = 1024  # Most models have this limit
        if len(text.split()) > max_input_length:
            # Truncate to fit model limits
            words = text.split()[:max_input_length]
            text = ' '.join(words)

        # Generate summary
        result = self.summarizer(
            text,
            max_length=max_length,
            min_length=min_length,
            do_sample=False,
            num_beams=4,
            early_stopping=True
        )

        return result[0]['summary_text']

    def _extractive_summarize(self, text: str, max_words: int) -> str:
        """
        Fallback extractive summarization using sentence scoring.

        Args:
            text: Text to summarize
            max_words: Maximum words in summary

        Returns:
            Extractive summary
        """
        sentences = self._split_into_sentences(text)
        if not sentences:
            return text[:200] + "..." if len(text) > 200 else text

        # Score sentences
        sentence_scores = self._score_sentences(sentences, text)

        # Select top sentences
        top_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)
        selected_sentences = []

        word_count = 0
        for sentence, _ in top_sentences:
            sentence_words = len(sentence.split())
            if word_count + sentence_words <= max_words:
                selected_sentences.append(sentence)
                word_count += sentence_words
            else:
                break

        # Sort selected sentences by original order
        original_order = []
        for sentence in sentences:
            if sentence in selected_sentences:
                original_order.append(sentence)

        return ' '.join(original_order)

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for summarization."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())

        # Remove excessive punctuation
        text = re.sub(r'[^\w\s.,!?-]', '', text)

        return text

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting (can be improved with NLTK)
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def _score_sentences(self, sentences: List[str], full_text: str) -> Dict[str, float]:
        """Score sentences for extractive summarization."""
        # Simple scoring based on word frequency
        words = re.findall(r'\b\w+\b', full_text.lower())
        word_freq = Counter(words)

        # Remove stop words (basic list)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'shall'}

        # Score each sentence
        sentence_scores = {}
        for sentence in sentences:
            sentence_words = re.findall(r'\b\w+\b', sentence.lower())
            score = 0

            for word in sentence_words:
                if word not in stop_words:
                    score += word_freq.get(word, 0)

            # Normalize by sentence length
            if sentence_words:
                score /= len(sentence_words)

            sentence_scores[sentence] = score

        return sentence_scores

    def _fallback_summary(self, text: str, max_words: int) -> str:
        """Generate a simple fallback summary."""
        words = text.split()
        if len(words) <= max_words:
            return text

        # Take first part of text
        summary_words = words[:max_words]
        summary = ' '.join(summary_words)

        # Add ellipsis if truncated
        if len(words) > max_words:
            summary += '...'

        return summary

    def batch_summarize(self, texts: List[str], max_length: Optional[int] = None,
                       min_length: Optional[int] = None) -> List[str]:
        """
        Summarize multiple texts in batch.

        Args:
            texts: List of texts to summarize
            max_length: Maximum summary length
            min_length: Minimum summary length

        Returns:
            List of summaries
        """
        summaries = []
        for text in texts:
            summary = self.summarize(text, max_length, min_length)
            summaries.append(summary)

        return summaries


class SummarizationConfig:
    """Configuration class for text summarization."""

    # Available models (smaller to larger)
    MODELS = {
        'small': 'facebook/bart-base',
        'medium': 'facebook/bart-large-cnn',
        'large': 'facebook/bart-large-xsum',
        't5-small': 't5-small',
        't5-base': 't5-base',
        't5-large': 't5-large'
    }

    @staticmethod
    def get_model_config(model_size: str = 'medium') -> Dict[str, Any]:
        """
        Get configuration for a specific model size.

        Args:
            model_size: Size of the model ('small', 'medium', 'large')

        Returns:
            Configuration dictionary
        """
        configs = {
            'small': {
                'model_name': SummarizationConfig.MODELS['small'],
                'max_length': 100,
                'min_length': 20
            },
            'medium': {
                'model_name': SummarizationConfig.MODELS['medium'],
                'max_length': 150,
                'min_length': 30
            },
            'large': {
                'model_name': SummarizationConfig.MODELS['large'],
                'max_length': 200,
                'min_length': 50
            }
        }

        return configs.get(model_size, configs['medium'])


def main():
    """Command-line interface for text summarization."""
    import argparse

    parser = argparse.ArgumentParser(description="Text Summarization for TTS AI Pipeline")
    parser.add_argument('--text', help='Text to summarize')
    parser.add_argument('--file', help='File containing text to summarize')
    parser.add_argument('--model', default='medium', choices=['small', 'medium', 'large'],
                       help='Model size to use')
    parser.add_argument('--max-length', type=int, help='Maximum summary length')
    parser.add_argument('--min-length', type=int, help='Minimum summary length')
    parser.add_argument('--device', help='Device to run model on (cpu, cuda, auto)')

    args = parser.parse_args()

    # Check availability
    if not TRANSFORMERS_AVAILABLE:
        print("❌ Transformers library is not available.")
        print("📦 Install with: pip install transformers sentencepiece")
        return 1

    try:
        # Get model configuration
        config = SummarizationConfig.get_model_config(args.model)

        # Override with command line args
        if args.max_length:
            config['max_length'] = args.max_length
        if args.min_length:
            config['min_length'] = args.min_length
        if args.device:
            config['device'] = args.device

        # Initialize summarizer
        summarizer = TextSummarizer(**config)

        # Get text to summarize
        if args.text:
            text = args.text
        elif args.file:
            with open(args.file, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            print("❌ Please provide text with --text or --file")
            return 1

        # Generate summary
        print("📝 Generating summary...")
        summary = summarizer.summarize(text)

        print("\n" + "="*50)
        print("📄 ORIGINAL TEXT:")
        print("="*50)
        print(text[:500] + "..." if len(text) > 500 else text)

        print("\n" + "="*50)
        print("📋 SUMMARY:")
        print("="*50)
        print(summary)

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
