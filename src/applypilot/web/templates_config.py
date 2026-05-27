"""Shared Jinja2Templates instance with cache disabled to avoid unhashable-key bug."""
from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader

_TEMPLATES_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=True,
    cache_size=0,
)

templates = Jinja2Templates(env=_env)
