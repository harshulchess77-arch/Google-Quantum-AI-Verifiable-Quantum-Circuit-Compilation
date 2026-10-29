"""Modular circuit optimization and liveness compaction passes.

This module contains optimization passes that can be applied to kickmix circuits
to reduce qubit count and gate counts while preserving functionality.
"""

from .liveness import analyze_wire_liveness, compute_ancilla_recycling_mapping
from .gate_cancellation import cancel_adjacent_gates, commute_diagonal_gates, fuse_z_pow_rotations
from .hmr_uncomputation import apply_hmr_uncomputation

__all__ = [
    "analyze_wire_liveness",
    "compute_ancilla_recycling_mapping",
    "cancel_adjacent_gates",
    "commute_diagonal_gates",
    "fuse_z_pow_rotations",
    "apply_hmr_uncomputation",
]
