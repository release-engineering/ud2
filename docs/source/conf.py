"""
Sphinx configuration for the ud2 documentation.
"""

import configparser
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETUP_CFG = PROJECT_ROOT / 'setup.cfg'

config = configparser.ConfigParser()
config.read(SETUP_CFG)
metadata = config['metadata']

project = metadata.get('name', 'ud2')
author = metadata.get('author', 'Unknown')
release = metadata.get('version', '0.0.0')
version = release

current_year = datetime.utcnow().year
copyright = (
    f"{current_year}, {author}"
)

extensions = [
    'myst_parser',
    'sphinxcontrib.mermaid',
]

templates_path = ['_templates']
exclude_patterns = ['build', 'Thumbs.db', '.DS_Store']

root_doc = 'index'

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# MyST / Markdown configuration
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

myst_enable_extensions = [
    'colon_fence',
    'deflist',
    'linkify',
]

myst_fence_as_directive = [
    'mermaid',
]

mermaid_version = '10.9.1'

# The end.
