"""Configuration file for the Sphinx documentation builder."""

# import os
# import sys
from datetime import datetime

# Insert the parent directory into the path
# sys.path.insert(0, os.path.abspath("../your_source_code"))

project = "your-package-name"
author = "your-name"

year = datetime.now().year
copyright = f"{year}"

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

pygments_style = "sphinx"

autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "show-inheritance": True,
}

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinxcontrib.mermaid",
]

# sphinx-palewire-theme settings
# html_theme = "palewire"
# html_sidebars: dict[Any, Any] = {
#     "**": [
#         "about.html",
#         "navigation.html",
#     ]
# }
# html_theme_options: dict[Any, Any] = {
#     "canonical_url": "https://palewi.re/docs/first-llm-classifier/",
# }
# html_baseurl = "/docs/"
