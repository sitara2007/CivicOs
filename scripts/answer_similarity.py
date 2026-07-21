"""Compute a simple similarity score between an OpenAI answer and ground truth."""

from __future__ import annotations

import argparse
import difflib
import sys


def similarity_score(reference: str, candidate: str) -> float:
    """Return a normalized similarity score between 0.0 and 1.0."""
    return difflib.SequenceMatcher(None, reference.strip(), candidate.strip()).ratio()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare an OpenAI answer against ground truth and print a similarity score."
    )
    parser.add_argument(
        "--ground-truth",
        required=True,
        help="The ground truth text to compare against.",
    )
    parser.add_argument(
        "--openai-answer",
        required=True,
        help="The OpenAI answer text to compare.",
    )
    args = parser.parse_args(argv)

    score = similarity_score(args.ground_truth, args.openai_answer)
    print(f"Ground truth: {args.ground_truth}")
    print(f"OpenAI answer: {args.openai_answer}")
    print(f"Similarity Score: {score:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
