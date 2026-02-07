"""
Fork-Join merge helpers.

Single responsibility: build merged NodeOutput for join nodes by combining
full data from all branch outputs. Uses existing key policy (key, key_2, key_3).

Join node input shape:
  data = initial keys (pre-fork) + every key from every branch (all node outputs).
  Key collisions resolved with key_2, key_3 via get_unique_key.
  No new schema; nodes read keys as today (all node outputs in the dict).
"""

from typing import Dict, List

from ...Node.Core.Node.Core.Data import NodeOutput


def get_unique_key(data: Dict, base_key: str) -> str:
    """
    Resolve a unique key for merging. If base_key exists, use base_key_2, base_key_3, etc.
    Matches BaseNode.get_unique_output_key behavior for a plain dict.
    """
    if base_key not in data:
        return base_key
    counter = 2
    while f"{base_key}_{counter}" in data:
        counter += 1
    return f"{base_key}_{counter}"


def merge_branch_outputs(
    initial_output: NodeOutput,
    branch_outputs: List[NodeOutput],
) -> NodeOutput:
    """
    Merge full data from all branch outputs into one NodeOutput for a join node.

    Every key from each branch's output.data is added to the merged dict.
    Key collisions are resolved with key_2, key_3 (same as get_unique_output_key).
    Call after asyncio.gather so all branch_outputs are available (single-threaded merge).
    """
    merged_data: Dict = dict(initial_output.data)
    for branch_out in branch_outputs:
        if not branch_out or not getattr(branch_out, "data", None):
            continue
        for key, value in branch_out.data.items():
            resolved_key = get_unique_key(merged_data, key)
            merged_data[resolved_key] = value
    return NodeOutput(
        id=initial_output.id,
        data=merged_data,
        metadata=initial_output.metadata,
    )
