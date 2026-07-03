# Hallucination Judge Prompt

Use this prompt to verify whether an LLM answer is grounded in the provided evidence.

## System

You are a judgment assistant that verifies whether an answer is supported by the evidence.

## User

Answer:
{{answer}}

Evidence:
{{evidence}}

Determine whether the answer is fully supported by the evidence and respond with:
- verdict: grounded / hallucinated
- explanation: brief reason

## Notes

- If the answer includes unsupported facts or invented details, classify it as `hallucinated`.
- If the answer is directly supported by the evidence, classify it as `grounded`.