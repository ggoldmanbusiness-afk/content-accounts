#!/usr/bin/env python3
"""
Verification script for semantic hook scoring implementation
Run this to verify the semantic scorer is working correctly
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

from core.semantic_scorer import SemanticHookScorer

def test_semantic_scorer():
    """Test the semantic hook scorer with various hooks"""
    print("=" * 70)
    print("Semantic Hook Scorer Verification")
    print("=" * 70)

    # Initialize scorer
    try:
        scorer = SemanticHookScorer(use_openrouter=True)
        print("✅ SemanticHookScorer initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize scorer: {e}")
        return False

    # Test hooks for different accounts
    test_cases = [
        {
            "account": "salesprofessional",
            "threshold": 12,
            "hooks": [
                "why your cold calls keep failing (the one technique top performers use)",
                "how to handle objections in enterprise sales",
                "the prospecting mistake that's costing you deals"
            ]
        },
        {
            "account": "dreamtimelullabies",
            "threshold": 8,
            "hooks": [
                "5 bedtime routines that actually work (most parents skip #3)",
                "the bedtime mistake 90% of parents make is starting with bed",
                "why your toddler won't sleep through the night"
            ]
        }
    ]

    all_passed = True

    for test_case in test_cases:
        account = test_case["account"]
        threshold = test_case["threshold"]

        print(f"\n{'=' * 70}")
        print(f"Testing {account} (threshold: {threshold}/20)")
        print(f"{'=' * 70}")

        for hook in test_case["hooks"]:
            total, feedback = scorer.score_hook(hook)
            passed = total >= threshold

            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"\n{status} [{total}/20] \"{hook}\"")

            if not passed:
                all_passed = False
                print(f"  Feedback:")
                for fb in feedback:
                    print(f"    - {fb}")

    print(f"\n{'=' * 70}")
    if all_passed:
        print("✅ All tests passed! Semantic scoring is working correctly.")
    else:
        print("⚠️  Some tests failed. Consider lowering thresholds or adjusting scoring.")
    print(f"{'=' * 70}\n")

    return all_passed


if __name__ == "__main__":
    success = test_semantic_scorer()
    sys.exit(0 if success else 1)
