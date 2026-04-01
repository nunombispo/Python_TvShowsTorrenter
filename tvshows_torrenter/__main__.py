from __future__ import annotations

import argparse

from .app import run


def main() -> None:
    parser = argparse.ArgumentParser(prog="tvshows-torrenter", description="Scan TV show library and download next episode torrents.")
    parser.add_argument(
        "--settings",
        help="Path to settings.json (default: env TVSHOWS_TORRENTER_SETTINGS, ./settings.json, or XDG config).",
        default=None,
    )
    args = parser.parse_args()
    run(settings_path=args.settings)


if __name__ == "__main__":
    main()

