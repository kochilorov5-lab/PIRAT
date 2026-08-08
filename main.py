from __future__ import annotations

import sys


def main() -> None:
    if "--idle" in sys.argv:
        from pirat.idle_worker import main as idle_main

        # Keep windowed builds from showing PyInstaller crash dialogs.
        try:
            raise SystemExit(idle_main())
        except SystemExit:
            raise
        except Exception as exc:
            print(f"idle failed: {exc}", flush=True)
            raise SystemExit(1)

    from pirat.app import run

    run()


if __name__ == "__main__":
    main()
