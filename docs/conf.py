"""
Sphinx configuration for the ud2 documentation.
"""

import importlib
from pathlib import Path


def load_setup():
    from configparser import ConfigParser

    global project
    global release
    global version
    global author
    global copyright

    conf = ConfigParser()
    conf.read(["../setup.cfg"])
    metadata = conf['metadata']

    project = metadata['name']
    release = metadata['version']
    version = '.'.join(release.split('.')[:2])
    author = metadata['author']
    copyright = f"{metadata['copyright_years']}, {author}"

load_setup()


def patch_sphinx_reports():
    import sphinx_reports

    ReportDomain = None
    # _sphinx_reports_spec = importlib.util.find_spec('sphinx_reports')

    # if _sphinx_reports_spec is not None:
    #     sphinx_reports = importlib.import_module('sphinx_reports')
    ReportDomain = sphinx_reports.ReportDomain
    def _normalize_report_config_types():
        normalized = {}
        for key, (default, rebuild, config_type) in ReportDomain.configValues.items():
            origin = getattr(config_type, '__origin__', None)
            normalized_type = origin if origin is not None else config_type
            normalized[key] = (default, rebuild, normalized_type)

        ReportDomain.configValues = normalized

    _normalize_report_config_types()

patch_sphinx_reports()


extensions = [
    'myst_parser',
    'sphinxcontrib.mermaid',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx_reports',
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

autosummary_generate = True

autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
    'exclude-members': 'field_validator',
}

suppress_warnings = [
    'autodoc.duplicate_object',
]


# Sphinx Reports configuration

# configuration for the Code Coverage report
report_codecov_packages = {
    'src': {
        'name': project,
        'json_report': 'build/coverage.json',
        'fail_below': 0,
        'levels': 'default',
    },
}

# configuration for the Document Coverage report
report_doccov_packages = {
  "src": {
    "name": project,
    "directory": project,
    "fail_below": 50,
    "levels": "default"
  }
}


# The end.
