"""
Semantic Hook Scoring
Uses embeddings to evaluate hook quality without hardcoded keywords
"""

import os
import re
from typing import List, Tuple, Dict
import numpy as np
import requests
from functools import lru_cache


class SemanticHookScorer:
    """Scores hooks using semantic similarity instead of keyword matching"""

    # Reference examples of high-quality hooks for each dimension
    REFERENCE_EXAMPLES = {
        "curiosity_gap": [
            "what actually happens when you ignore the advice everyone gives",
            "the real reason your strategy keeps failing (no one talks about this)",
            "it's not what you think - here's the truth about",
            "what really happens behind the scenes that changes everything",
            "the one thing no one tells you about",
            "why this keeps happening and what it means",
            "the hidden reason most people struggle with",
            "what top performers know that you don't",
            "the mistake everyone makes that ruins everything",
            "why your approach isn't working (and what to do instead)",
            "the secret to success that nobody shares"
        ],
        "actionability": [
            "how to build a system that actually works",
            "5 steps to completely transform your approach",
            "stop doing this and start doing this instead",
            "the exact method I use to achieve results",
            "how to fix this problem in 3 simple steps",
            "the framework I built to solve",
            "start using this technique immediately",
            "implement this strategy today",
            "simple routines that actually work",
            "practical techniques to improve results",
            "strategies that get real outcomes"
        ],
        "specificity": [
            "3 morning routines that changed my bedtime struggles",
            "the exact cold calling script that closed 47 deals",
            "5 specific techniques for handling objections in enterprise sales",
            "why 2am wake-ups happen and the one thing that fixed it",
            "7 bedtime mistakes parents make between 6-8pm",
            "the precise moment in your sales call where you lose the deal",
            "4 naptime rituals that work for 18-month-olds",
            "the one prospecting method that landed 12 meetings this week"
        ],
        "scroll_stop": [
            "stop trying to do it the normal way - go backward",
            "what top performers do differently that most people never notice",
            "the opposite of what everyone tells you actually works better",
            "most parents keep making this mistake and wonder why it fails",
            "why doing less actually gets you more results",
            "the counterintuitive approach that changed everything",
            "most sales reps are doing this backward",
            "everything you learned about this is wrong"
        ]
    }

    def __init__(self, api_key: str = None, use_openrouter: bool = True, custom_references: Dict = None):
        """
        Initialize with OpenAI API or OpenRouter

        Args:
            api_key: API key (defaults to env vars)
            use_openrouter: If True, use OpenRouter; else use OpenAI directly
            custom_references: Optional niche-specific reference examples to merge with defaults
        """
        if use_openrouter:
            self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
            self.base_url = "https://openrouter.ai/api/v1"
            self.model = "openai/text-embedding-3-small"
        else:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            self.base_url = "https://api.openai.com/v1"
            self.model = "text-embedding-3-small"

        if not self.api_key:
            raise ValueError("No API key found. Set OPENROUTER_API_KEY or OPENAI_API_KEY")

        # Merge references: niche-specific first (higher priority), then defaults
        self.reference_examples = {k: list(v) for k, v in self.REFERENCE_EXAMPLES.items()}
        if custom_references:
            for dimension, examples in custom_references.items():
                if dimension in self.reference_examples and isinstance(examples, list):
                    self.reference_examples[dimension] = (
                        examples + self.reference_examples[dimension]
                    )

    @lru_cache(maxsize=1000)
    def _get_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding for text (with caching)

        Args:
            text: Text to embed

        Returns:
            Embedding vector as numpy array
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "input": text
        }

        response = requests.post(
            f"{self.base_url}/embeddings",
            headers=headers,
            json=data,
            timeout=30
        )

        if response.status_code != 200:
            raise RuntimeError(f"Embedding API error: {response.status_code} - {response.text}")

        result = response.json()
        embedding = result["data"][0]["embedding"]
        return np.array(embedding)

    def _similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Cosine similarity between two embeddings"""
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

    def score_dimension(self, hook: str, dimension: str, debug: bool = False) -> int:
        """
        Score a hook on one dimension (0-5 points)

        Args:
            hook: The hook text to score
            dimension: One of "curiosity_gap", "actionability", "specificity", "scroll_stop"
            debug: If True, print debug info

        Returns:
            Score from 0-5 based on semantic similarity to reference examples
        """
        if dimension not in self.reference_examples:
            return 2  # Default

        hook_emb = self._get_embedding(hook.lower())
        reference_examples = self.reference_examples[dimension]

        # Get max similarity to any reference example
        max_similarity = 0.0
        best_example = ""
        for example in reference_examples:
            example_emb = self._get_embedding(example)
            similarity = self._similarity(hook_emb, example_emb)
            if similarity > max_similarity:
                max_similarity = similarity
                best_example = example

        if debug:
            print(f"  [{dimension}] max_sim={max_similarity:.3f}, best='{best_example[:50]}...'")

        # Convert similarity (0-1) to score (0-5)
        # Calibrated against real text-embedding-3-small outputs:
        #   Cross-domain hooks: 0.19-0.34, Same-niche hooks: 0.35-0.50, Near-match: 0.50-0.70+
        if max_similarity >= 0.45:
            return 5
        elif max_similarity >= 0.35:
            return 4
        elif max_similarity >= 0.28:
            return 3
        elif max_similarity >= 0.20:
            return 2
        else:
            return 1

    def score_hook(self, hook: str) -> Tuple[int, List[str]]:
        """
        Score a complete hook across all dimensions

        Returns:
            (total_score, feedback_list)
        """
        scores = {}
        feedback = []

        # Score each dimension
        dimensions = ["curiosity_gap", "actionability", "specificity", "scroll_stop"]
        for dimension in dimensions:
            score = self.score_dimension(hook, dimension)
            scores[dimension] = score

            # Generate feedback if score is low
            if score < 3:
                dim_name = dimension.replace('_', ' ').title()
                # Provide example instead of exact keywords
                examples = self.reference_examples[dimension][:2]
                feedback.append(
                    f"{dim_name} could be stronger (scored {score}/5). "
                    f"Examples: '{examples[0]}' or '{examples[1]}'"
                )

        total = sum(scores.values())

        # Add style feedback
        if any(word[0].isupper() and i > 0 for i, word in enumerate(hook.split()) if len(word) > 1):
            feedback.append("Style violation: Avoid capitalizing words mid-sentence")

        return total, feedback

    def get_dimension_breakdown(self, hook: str) -> Dict[str, int]:
        """
        Get detailed breakdown of scores by dimension

        Returns:
            Dict mapping dimension names to scores
        """
        scores = {}
        for dimension in ["curiosity_gap", "actionability", "specificity", "scroll_stop"]:
            scores[dimension] = self.score_dimension(hook, dimension)
        return scores
