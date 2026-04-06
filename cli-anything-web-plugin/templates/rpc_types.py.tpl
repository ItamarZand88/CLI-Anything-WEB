"""RPC method definitions for cli-web-${app_name}.

Each method maps to a batchexecute RPC ID discovered from traffic capture.
IMPORTANT: Verify every RPC ID against captured traffic. The same endpoint
may use different param structures for different operations.
"""
from __future__ import annotations

from enum import Enum


class RPCMethod(Enum):
    """Known RPC methods.

    Format: NAME = ("rpc_id", "human_description")
    Fill in from <APP>.md after traffic analysis.
    """

    # EXAMPLE = ("AbCdEf", "Example operation description")
    pass
