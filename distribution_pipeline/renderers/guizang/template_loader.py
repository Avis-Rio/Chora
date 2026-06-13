from pathlib import Path


VENDOR_DIR = Path(__file__).resolve().parents[2] / "vendor" / "guizang"

TEMPLATES = {
    "editorial": "template-editorial-card.html",
    "swiss": "template-swiss-card.html",
}


def vendor_path(name: str) -> Path:
    return VENDOR_DIR / name


def load_template(mode: str) -> str:
    if mode not in TEMPLATES:
        raise ValueError(f"Unknown guizang mode: {mode}")
    return vendor_path(TEMPLATES[mode]).read_text(encoding="utf-8")
