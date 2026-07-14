"""Sphinx configuration for the quant_data documentation."""

from __future__ import annotations

import os
import sys
from pathlib import Path


DOCS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = DOCS_DIR.parent
sys.path.insert(0, str(PROJECT_DIR.parent))

from quant_data import __version__  # noqa: E402


project = "quant_data"
author = "quant_data maintainers"
copyright = "2026, quant_data maintainers"
version = __version__
release = __version__

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.viewcode",
    "sphinx.ext.doctest",
    "sphinx.ext.coverage",
    "sphinx.ext.graphviz",
]

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}
root_doc = "index"
language = "zh_CN"
html_search_language = "zh"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
templates_path = ["_templates"]

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "substitution",
    "tasklist",
]
myst_heading_anchors = 3

autosummary_generate = True
autodoc_class_signature = "mixed"
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_typehints_format = "short"
autoclass_content = "class"
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_use_param = True
napoleon_use_rtype = False

autosectionlabel_prefix_document = True
nitpicky = True
nitpick_ignore_regex = [
    ("py:class", r"(Any|Callable|Literal|Mapping|Path|Protocol|Sequence)"),
    ("py:class", r"(pandas|pyarrow|polars)\..*"),
    ("py:class", r"(datetime|pathlib|typing|collections\.abc)\..*"),
]

# Strict local builds are deterministic and never fetch inventories. Set this
# flag when authoring cross-project links with internet access.
_online_intersphinx = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "pyarrow": ("https://arrow.apache.org/docs/", None),
}
intersphinx_mapping = (
    _online_intersphinx
    if os.environ.get("QUANT_DATA_DOCS_ONLINE", "").lower()
    in {"1", "true", "yes", "on"}
    else {}
)

graphviz_output_format = "svg"
_environment_dot = Path(sys.executable).with_name("dot")
if _environment_dot.exists():
    graphviz_dot = str(_environment_dot)

html_theme = "pydata_sphinx_theme"
html_title = f"quant_data {release}"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_theme_options = {
    "navbar_align": "left",
    "header_links_before_dropdown": 7,
    "navigation_depth": 4,
    "show_toc_level": 2,
    "navigation_with_keys": True,
}
html_context = {"default_mode": "auto"}
html_show_sourcelink = True
html_copy_source = True
html_permalinks_icon = "¶"
pygments_style = "friendly"
pygments_dark_style = "monokai"
