import os
import subprocess
from pathlib import Path


DEPENDENCY_MESSAGE = (
    "Guizang image export requires Node.js and Playwright. "
    "Playwright browser binaries are also required."
)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROJECT_PLAYWRIGHT_BROWSERS = PROJECT_ROOT / ".ms-playwright"


def discover_guizang_render_scripts(package_dir: Path) -> list[Path]:
    package_dir = Path(package_dir)
    return sorted(package_dir.glob("*/render.cjs"))


def _is_missing_playwright(text: str) -> bool:
    return (
        "ERR_MODULE_NOT_FOUND" in text
        or "Cannot find package 'playwright'" in text
        or "Cannot find module 'playwright'" in text
    )


def _node_env() -> dict[str, str]:
    env = os.environ.copy()
    paths = [str(path / "node_modules") for path in [PROJECT_ROOT, *PROJECT_ROOT.parents]]
    if env.get("NODE_PATH"):
        paths.append(env["NODE_PATH"])
    env["NODE_PATH"] = os.pathsep.join(paths)
    env.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(PROJECT_PLAYWRIGHT_BROWSERS))
    return env


def export_guizang_images(package_dir: Path) -> list[Path]:
    package_dir = Path(package_dir)
    scripts = discover_guizang_render_scripts(package_dir)
    image_paths: list[Path] = []

    for script in scripts:
        print(f"Guizang image export: running {script}")
        try:
            subprocess.run(
                ["node", "render.cjs"],
                cwd=script.parent,
                check=True,
                text=True,
                env=_node_env(),
                timeout=180,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(DEPENDENCY_MESSAGE) from exc
        except subprocess.CalledProcessError as exc:
            details = "\n".join(part for part in [exc.output, exc.stderr] if part)
            if _is_missing_playwright(details):
                raise RuntimeError(DEPENDENCY_MESSAGE) from exc
            suffix = f"\n{details}" if details else "\nSee render output above."
            raise RuntimeError(f"Guizang image export failed for {script}:{suffix}") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Guizang image export timed out for {script}") from exc
        image_paths.extend(sorted((script.parent / "output").glob("*.png")))

    return image_paths
