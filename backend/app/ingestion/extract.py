"""Document content extraction functions.

Converts uploaded files into Markdown for downstream processing.
"""

from pathlib import Path

import mammoth


def docx_to_markdown(file_path: Path) -> str:
    """Convert a DOCX file to Markdown using mammoth.

    Args:
        file_path: Path to the .docx file on disk.

    Returns:
        The extracted content as a Markdown string.
    """
    with open(file_path, "rb") as f:
        result = mammoth.convert_to_markdown(f)
    return result.value


def txt_to_markdown(file_path: Path, filename: str) -> str:
    """Convert a plain text file to Markdown by wrapping it with a heading.

    Args:
        file_path: Path to the .txt or .md file on disk.
        filename: The original filename, used as the Markdown heading.

    Returns:
        The file content wrapped under a ``# {filename}`` heading.
    """
    content = file_path.read_text(encoding="utf-8")
    return f"# {filename}\n\n{content}"
