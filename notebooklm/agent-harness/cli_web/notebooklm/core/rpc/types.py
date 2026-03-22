"""RPC method IDs and URL constants for NotebookLM batchexecute.

When IDs rotate on Google's side, update this file as the single source of truth.
"""

BATCHEXECUTE_URL = "https://notebooklm.google.com/_/LabsTailwindUi/data/batchexecute"
BASE_URL = "https://notebooklm.google.com"


class RPCMethod:
    """RPC method identifiers for the batchexecute API.

    Reverse-engineered from network traffic analysis.
    """
    # Notebooks
    LIST_NOTEBOOKS = "wXbhsf"
    CREATE_NOTEBOOK = "CCqFvf"
    GET_NOTEBOOK = "rLM1Ne"      # Also returns sources embedded in response
    RENAME_NOTEBOOK = "s0tc2d"
    DELETE_NOTEBOOK = "WWINqb"

    # Sources — ALL source ops use "izAoDd" with different param structures
    ADD_SOURCE = "izAoDd"        # Add source (URL, text, file)
    ADD_SOURCE_FILE = "o4cbdc"   # Register uploaded file as source
    GET_SOURCE = "hizoJc"
    DELETE_SOURCE = "tGMBJ"
    REFRESH_SOURCE = "FLmJqe"

    # Chat (streaming endpoint, not batchexecute)
    CHAT_QUERY = "yyryJe"        # Also GENERATE_MIND_MAP in reference

    # Artifacts (unified via R7cb6c)
    CREATE_ARTIFACT = "R7cb6c"   # Generate ANY artifact (audio, video, report, quiz, etc.)
    LIST_ARTIFACTS = "gArtLc"    # List all artifacts in a notebook
    NOTES_ARTIFACT = "ciyUvf"    # GET_SUGGESTED_REPORTS — AI-suggested formats
    LIST_AUDIO_TYPES = "sqTeoe"

    # Notes
    CREATE_NOTE = "CYK0Xb"
    GET_NOTES_AND_MIND_MAPS = "cFji9"

    # Conversation
    GET_LAST_CONVERSATION_ID = "hPTbtc"
    GET_CONVERSATION_TURNS = "khqZz"

    # Research
    POLL_RESEARCH = "e3bVqc"

    # User/Config
    GET_USER_INFO = "JFMDGd"     # Also GET_SHARE_STATUS in reference
    GET_CONFIG = "ZwVcOc"
    SUMMARIZE = "VfAZjd"         # Summarize sources


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
