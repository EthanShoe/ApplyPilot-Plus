"""Shared Jinja2Templates instance with cache disabled to avoid unhashable-key bug."""
import re
from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader

_TEMPLATES_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=True,
    cache_size=0,
)


def _strip_md(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\*{1,2}([^*\n]+)\*{1,2}', r'\1', text)       # **bold** / *italic*
    text = re.sub(r'#{1,6}\s*', '', text)                           # ## headings
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)           # [link](url)
    text = re.sub(r'`([^`]+)`', r'\1', text)                       # `inline code`
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)    # bullet points
    text = re.sub(r'\n{3,}', '\n\n', text)                         # excess blank lines
    return text.strip()


_env.filters["strip_md"] = _strip_md

templates = Jinja2Templates(env=_env)
