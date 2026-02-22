import os

# Project root (directory above /src)
BASE = os.path.dirname(os.path.dirname(__file__))
EMB_DIR = os.path.join(BASE, "embeddings")

# GitHub settings for code-change watcher
GITHUB_REPO = os.getenv("GITHUB_REPO", "MoldovanAndrada/traceability_project")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Multi-project dataset registry.
# Add new entries here to scale from 3 to 5+ projects.
PROJECTS = {
    "lang": {
        "data_dir": os.path.join(BASE, "traceability_lang"),
        "stories": "user_stories.csv",
        "code_dir": "code",
    },
    "time": {
        "data_dir": os.path.join(BASE, "traceability_time_poc_complex"),
        "stories": "time_usr_stories.csv",
        "code_dir": "src",
    },
    "math": {
        "data_dir": os.path.join(BASE, "traceability_math_large - corect final"),
        "stories": "user_stories.csv",
        "code_dir": "src",
    },
}


def resolve_project(project_name: str) -> dict:
    if project_name not in PROJECTS:
        known = ", ".join(sorted(PROJECTS))
        raise ValueError(f"Unknown project '{project_name}'. Available projects: {known}")

    project = PROJECTS[project_name].copy()
    project["name"] = project_name
    project["stories_path"] = os.path.join(project["data_dir"], project["stories"])
    project["code_path"] = os.path.join(project["data_dir"], project["code_dir"])
    return project


# Backward-compatible defaults (lang dataset)
DEFAULT_PROJECT = "lang"
_DATA = resolve_project(DEFAULT_PROJECT)
DATA_DIR = _DATA["data_dir"]
USER_STORIES = _DATA["stories_path"]
CODE_DIR = _DATA["code_path"]

# Embedding files
FAISS_INDEX = os.path.join(EMB_DIR, "index.faiss")
EMB_FILE = os.path.join(EMB_DIR, "embeddings.npy")
META_FILE = os.path.join(EMB_DIR, "metadata.json")
