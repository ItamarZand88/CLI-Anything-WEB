"""RPC method identifiers for cli-web-${app_name} batchexecute.

When Google rotates RPC IDs, update this file as the single source of truth.
Verify every RPC ID against captured traffic — the same endpoint may serve
multiple operations with different param structures.
"""
from __future__ import annotations

# TODO: replace with the real batchexecute URL from traffic analysis.
# Typical shape: https://<app>.google.com/_/<ServiceName>/data/batchexecute
BATCHEXECUTE_URL = "https://FILL_IN_HOST/_/FILL_IN_SERVICE/data/batchexecute"
BASE_URL = "https://FILL_IN_HOST"


class RPCMethod:
    """RPC method IDs discovered from network traffic analysis.

    Add each ID as a class attribute. Example::

        LIST_THINGS = "wXbhsf"
        CREATE_THING = "CCqFvf"
    """

    # Fill these in after parsing the analyze-traffic.json output.
    EXAMPLE = "FILL_IN_RPC_ID"
