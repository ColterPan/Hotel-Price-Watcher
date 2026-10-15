"""Entry point: `python -m hotel_watcher.main` or `uvicorn hotel_watcher.main:app`."""

from __future__ import annotations

import os

import uvicorn

from hotel_watcher.api.app import create_app

app = create_app()


def run() -> None:
    # Bind to localhost by default. This app has no authentication, so it
    # should not be reachable from other machines unless you put it behind
    # something that has.
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("hotel_watcher.main:app", host=host, port=port)


if __name__ == "__main__":
    run()
