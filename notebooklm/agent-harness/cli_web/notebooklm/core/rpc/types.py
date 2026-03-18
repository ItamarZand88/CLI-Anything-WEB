"""RPC method IDs and constants for NotebookLM batchexecute protocol."""

# Base URL for all batchexecute calls
BATCHEXECUTE_URL = "https://notebooklm.google.com/_/LabsTailwindUi/data/batchexecute"

# Homepage for token extraction
HOMEPAGE_URL = "https://notebooklm.google.com/"

# WIZ_global_data keys for dynamic parameters
WIZ_KEYS = {
    "at": "SNlM0e",      # CSRF token
    "bl": "cfb2h",       # Build label
    "fsid": "FdrFJe",    # Session ID
}

# RPC Method IDs
class RpcMethod:
    # Notebook operations
    LIST_NOTEBOOKS = "wXbhsf"
    LIST_SHARED_NOTEBOOKS = "ub2Bae"
    GET_NOTEBOOK = "rLM1Ne"
    GET_USER_QUOTAS = "ZwVcOc"
    GET_PLAN_INFO = "ozz5Z"

    # Source operations (embedded in notebook responses)

    # Chat operations
    GET_CHAT_THREADS = "hPTbtc"
    GET_CHAT_HISTORY = "khqZz"
    GET_SUMMARY = "VfAZjd"

    # Artifact/Studio operations
    LIST_ARTIFACTS = "gArtLc"
    GET_OUTPUT_TEMPLATES = "sqTeoe"
    GET_SAVED_NOTES = "cFji9"

    # Sharing operations
    GET_COLLABORATORS = "JFMDGd"

    # Annotation operations
    GET_NOTES = "e3bVqc"

    # Mutation operations
    CREATE_NOTEBOOK = "CCqFvf"
    DELETE_NOTEBOOK = "WWINqb"
    ADD_TEXT_SOURCE = "izAoDd"
    CREATE_ARTIFACT = "R7cb6c"


# Source type codes
SOURCE_TYPE_DRIVE_DOC = 1
SOURCE_TYPE_PDF = 3
SOURCE_TYPE_PASTED_TEXT = 4
SOURCE_TYPE_WEB_URL = 5
SOURCE_TYPE_PASTED_TEXT_V2 = 8
SOURCE_TYPE_YOUTUBE = 9
SOURCE_TYPE_AUDIO = 10

SOURCE_TYPE_LABELS = {
    SOURCE_TYPE_DRIVE_DOC: "Google Drive",
    SOURCE_TYPE_PDF: "PDF",
    SOURCE_TYPE_PASTED_TEXT: "Pasted Text",
    SOURCE_TYPE_WEB_URL: "Web URL",
    SOURCE_TYPE_PASTED_TEXT_V2: "Pasted Text",
    SOURCE_TYPE_YOUTUBE: "YouTube",
    SOURCE_TYPE_AUDIO: "Audio",
}

# Artifact type codes
ARTIFACT_TYPE_AUDIO = 1
ARTIFACT_TYPE_VIDEO = 3
ARTIFACT_TYPE_QUIZ = 4
ARTIFACT_TYPE_PRESENTATION = 8

STREAMING_URL = "https://notebooklm.google.com/_/LabsTailwindUi/data/google.internal.labs.tailwind.orchestration.v1.LabsTailwindOrchestrationService/GenerateFreeFormStreamed"

ARTIFACT_TYPE_LABELS = {
    ARTIFACT_TYPE_AUDIO: "Audio Overview",
    ARTIFACT_TYPE_VIDEO: "Video",
    ARTIFACT_TYPE_QUIZ: "Quiz",
    ARTIFACT_TYPE_PRESENTATION: "Presentation",
}
