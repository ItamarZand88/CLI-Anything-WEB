"""RPC method IDs and URL constants for NotebookLM batchexecute.

Method IDs are cross-referenced with notebooklm-py (the reference implementation).
When IDs rotate on Google's side, update this file as the single source of truth.
"""

BATCHEXECUTE_URL = "https://notebooklm.google.com/_/LabsTailwindUi/data/batchexecute"
BASE_URL = "https://notebooklm.google.com"


class RPCMethod:
    """RPC method identifiers for the batchexecute API.

    Cross-referenced with notebooklm-py src/notebooklm/rpc/types.py.
    """
    # Notebooks
    LIST_NOTEBOOKS = "wXbhsf"
    CREATE_NOTEBOOK = "CCqFvf"
    GET_NOTEBOOK = "rLM1Ne"      # Also returns sources embedded in response
    RENAME_NOTEBOOK = "s0tc2d"
    DELETE_NOTEBOOK = "WWINqb"

    # Sources
    ADD_SOURCE = "izAoDd"        # Add source (URL, text, etc.)
    ADD_URL_SOURCE = "VfAZjd"    # Summarize/add URL — legacy, may be SUMMARIZE
    ADD_TEXT_SOURCE = "hPTbtc"    # May be GET_LAST_CONVERSATION_ID in newer API
    LIST_SOURCES = "izAoDd"      # Same as ADD_SOURCE (deprecated for listing)
    GET_SOURCE = "hizoJc"        # Correct ID from reference
    DELETE_SOURCE = "tGMBJ"      # Correct ID from reference

    # Chat (streaming endpoint, not batchexecute)
    CHAT_QUERY = "yyryJe"        # Also GENERATE_MIND_MAP in reference

    # Artifacts (unified via R7cb6c)
    CREATE_ARTIFACT = "R7cb6c"   # Generate ANY artifact (audio, video, report, quiz, etc.)
    GENERATE_ARTIFACT = "R7cb6c" # Alias for backward compatibility
    LIST_ARTIFACTS = "gArtLc"    # List all artifacts in a notebook
    NOTES_ARTIFACT = "ciyUvf"    # GET_SUGGESTED_REPORTS — AI-suggested formats
    LIST_AUDIO_TYPES = "sqTeoe"

    # Notes
    CREATE_NOTE = "CYK0Xb"

    # Research
    POLL_RESEARCH = "e3bVqc"

    # User/Config
    GET_USER_INFO = "JFMDGd"     # Also GET_SHARE_STATUS in reference
    GET_CONFIG = "ZwVcOc"


# Artifact type IDs (used with CREATE_ARTIFACT / R7cb6c)
class ArtifactType:
    AUDIO = 1
    REPORT = 2           # Briefing doc, study guide, blog post, etc.
    STUDY_GUIDE = 2      # Alias — same as REPORT
    BRIEFING_DOC = 2     # Alias — same as REPORT
    VIDEO = 3
    QUIZ = 4             # Also flashcards
    MIND_MAP = 5
    INFOGRAPHIC = 7
    SLIDE_DECK = 8
    DATA_TABLE = 9
    FAQ = 4              # FAQ uses quiz type
    TIMELINE = 5         # Timeline uses mind map type
