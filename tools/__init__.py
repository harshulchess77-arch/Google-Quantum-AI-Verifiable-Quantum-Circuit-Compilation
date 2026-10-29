"""Autonomous optimization harness for Google Quantum AI Verifiable Circuit Compilation.

This package provides tools for verifying, scoring, and optimizing quantum circuits
for the Kaggle competition "Verifiable Quantum Circuit Compilation".

Modules:
    score: Competition metric calculator (geometric mean improvement)
    verify: Wrapper around official verifiers with multi-salt support
    loop: Autonomous propose -> verify -> score -> atomic-accept engine
    build_submission: Deterministic Kaggle submission.zip builder
"""

__version__ = "0.1.0"
