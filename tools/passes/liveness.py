"""Wire liveness analysis and ancilla recycling pass.

Computes exact first-use to last-use/reset intervals for every wire,
then remaps freed ancillas eagerly to minimize peak qubit count Q.
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple
import dataclasses


@dataclasses.dataclass
class WireInterval:
    """Tracks the lifetime of a wire (qubit or bit)."""
    wire_id: int
    first_use: int  # Operation index where wire is first written/read
    last_use: int   # Operation index where wire is last used
    is_reset: bool = False  # Whether wire is reset to |0⟩ at end


def analyze_wire_liveness(circuit_operations: List[Dict]) -> Dict[int, WireInterval]:
    """Analyze wire liveness across all operations in a circuit.
    
    Args:
        circuit_operations: List of operation dictionaries from kickmix circuit
        
    Returns:
        Dict mapping wire_id to WireInterval with lifetime information
    """
    wire_usage: Dict[int, WireInterval] = {}
    
    for op_idx, op in enumerate(circuit_operations):
        # Extract wire IDs from operation (depends on kickmix format)
        # This is a placeholder - actual implementation depends on kickmix.Circuit structure
        op_wires = _extract_wires_from_operation(op)
        
        for wire_id in op_wires:
            if wire_id not in wire_usage:
                wire_usage[wire_id] = WireInterval(wire_id, op_idx, op_idx)
            else:
                wire_usage[wire_id].last_use = op_idx
    
    return wire_usage


def _extract_wires_from_operation(op: Dict) -> Set[int]:
    """Extract wire IDs from a kickmix operation (placeholder)."""
    # Actual implementation would parse kickmix operation structure
    # For now, return empty set as placeholder
    return set()


def compute_ancilla_recycling_mapping(
    wire_intervals: Dict[int, WireInterval],
    num_qubits: int
) -> Dict[int, int]:
    """Compute mapping for recycling freed ancillas.
    
    Args:
        wire_intervals: Wire lifetime analysis
        num_qubits: Total number of qubits in circuit
        
    Returns:
        Dict mapping original wire_id to recycled wire_id
    """
    # Sort wires by last_use time (earliest last_use gets recycled first)
    sorted_wires = sorted(
        wire_intervals.items(),
        key=lambda x: x[1].last_use
    )
    
    recycling_map = {}
    available_ids = []
    
    for wire_id, interval in sorted_wires:
        # Check if wire is no longer used
        if interval.last_use < max(op_idx for op_idx in [i.last_use for i in wire_intervals.values()]):
            available_ids.append(wire_id)
        else:
            # Wire is still live, assign from available pool
            if available_ids:
                recycled_id = available_ids.pop(0)
                recycling_map[wire_id] = recycled_id
    
    return recycling_map


def apply_ancilla_recycling(circuit, recycling_map: Dict[int, int]):
    """Apply wire remapping to a kickmix circuit (placeholder).
    
    Args:
        circuit: kickmix.Circuit object
        recycling_map: Wire ID remapping from compute_ancilla_recycling_mapping
    """
    # Placeholder: actual implementation would remap wire IDs in circuit
    # This requires kickmix.Circuit API access
    pass


def estimate_peak_qubit_reduction(circuit) -> int:
    """Estimate qubit reduction from liveness analysis (placeholder).
    
    Returns:
        Estimated number of qubits that can be recycled
    """
    # Placeholder: would analyze circuit structure
    return 0
