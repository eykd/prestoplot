"""HTTP server for serving grammar-generated content."""

from __future__ import annotations

import logging
import traceback
from http.server import BaseHTTPRequestHandler
from typing import TYPE_CHECKING

import markdown

from . import storages, story

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def create_handler(oracle_path: Path) -> type:
    """Create HTTP request handler for serving grammar content.

    Args:
        oracle_path: Path to the grammar file to serve

    Returns:
        HTTPRequestHandler class configured for the given oracle

    """

    class HTTPRequestHandler(BaseHTTPRequestHandler):
        """HTTP request handler that serves grammar-generated HTML content."""

        oracle_storage = storages.FileStorage(oracle_path.parent)

        def do_GET(self) -> None:
            """Handle GET requests by generating and serving grammar content.

            Generates content from the configured oracle and serves it as
            an HTML page with Markdown formatting.
            """
            kwargs = {}

            try:
                prompt = markdown.markdown(
                    story.render_story(self.oracle_storage, oracle_path.stem, **kwargs)
                )
            except Exception:
                logger.exception('Error!')
                self.send_response(500)
                self.wfile.write(
                    f'<h1>Error</h1><pre>{traceback.format_exc()}</pre>'.encode()
                )

            else:
                self.send_response(200)  # Success!

                self.send_header('content-type', 'text/html')
                self.end_headers()

                text_out = f"""

<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta http-equiv="x-ua-compatible" content="ie=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />

    <style>
        main {{
          max-width: 60ch;
          font-size: 2rem;
          margin: 1em auto;
        }}
    </style>


    <title>&mdash;</title>
  </head>

  <body>
    <main>
    {prompt}
    </main>
  </body>
</html>

                """

                self.wfile.write(text_out.encode('utf-8'))

    return HTTPRequestHandler
