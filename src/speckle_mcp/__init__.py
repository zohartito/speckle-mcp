"""Read-only Model Context Protocol server for Speckle.

The console entry point is ``speckle_mcp.server:main`` (exposed as the
``speckle-mcp`` command). ``server`` is imported lazily rather than at package
import time so that ``python -m speckle_mcp.server`` does not trip runpy's
"module found in sys.modules" warning.
"""

__version__ = "0.1.0"
