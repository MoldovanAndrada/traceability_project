import os

# Project root (directory above /src)
BASE = os.path.dirname(os.path.dirname(__file__))

# Data directories
DATA_DIR = os.path.join(BASE, "traceability_lang")
EMB_DIR = os.path.join(BASE, "embeddings")

# File paths
TEST_CASES     = os.path.join(DATA_DIR, "test_cases.csv")
USER_STORIES   = os.path.join(DATA_DIR, "user_stories.csv")
FAULTS         = os.path.join(DATA_DIR, "faults.csv")
GITHUB_REPO = "MoldovanAndrada/traceability_project"
GITHUB_TOKEN = "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"

# Folder containing the source code you want to watch
CODE_DIR       = os.path.join(DATA_DIR, "code")

# Embedding files
FAISS_INDEX    = os.path.join(EMB_DIR, "index.faiss")
EMB_FILE       = os.path.join(EMB_DIR, "embeddings.npy")
META_FILE      = os.path.join(EMB_DIR, "metadata.json")
