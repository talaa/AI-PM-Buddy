"""Knowledge loader utilities.

Loads markdown knowledge files (e.g., skills, processes, templates) from the
`backend/knowledge` directory and provides a simple concatenation function to
inject them into prompts.
"""
import os
from typing import List, Dict

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge")

def load_knowledge_files(file_keys: List[str]) -> Dict[str, str]:
    """Load the requested markdown files.

    Parameters
    ----------
    file_keys: List[str]
        List of identifiers, e.g., ["skills", "processes", "templates"].
        The function will look for a file named `<key>.md` inside the knowledge
        directory.

    Returns
    -------
    dict
        Mapping of key to file content. Missing files are ignored.
    """
    data: Dict[str, str] = {}
    for key in file_keys:
        filename = f"{key}.md"
        path = os.path.join(KNOWLEDGE_DIR, filename)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data[key] = f.read()
            except Exception as e:
                # Log but continue – we don't have a logger here, raise HTTP error
                # in the calling endpoint if needed.
                raise RuntimeError(f"Failed to read knowledge file {filename}: {e}")
    return data

def build_knowledge_context(knowledge_data: Dict[str, str]) -> str:
    """Create a single string from loaded knowledge.

    Each section is prefixed with a header for clarity.
    """
    sections = []
    for key, content in knowledge_data.items():
        sections.append(f"## {key.capitalize()}\n{content}\n")
    return "\n".join(sections)
