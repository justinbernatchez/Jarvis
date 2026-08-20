from __future__ import annotations

import json
from pathlib import Path

from jarvis_api.main import create_app


def generate_openapi(output: Path | None = None) -> Path:
    target = output or Path("contracts/openapi/openapi.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    document = create_app().openapi()
    target.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def main() -> None:
    path = generate_openapi()
    print(path)


if __name__ == "__main__":
    main()
