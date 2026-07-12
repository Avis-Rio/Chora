from pathlib import Path

STYLE_DIR = Path(__file__).resolve().parents[1] / "styles"


def _coerce_scalar(value: str):
    if value == "true":
        return True
    if value == "false":
        return False
    return value.strip('"')


def _load_yaml_fallback(text: str) -> dict:
    data = {}
    current_key = None
    nested_key = None

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if indent == 0 and line.endswith(":"):
            current_key = line[:-1]
            data[current_key] = {}
            nested_key = None
        elif indent == 0 and ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = _coerce_scalar(value.strip())
            current_key = key.strip()
            nested_key = None
        elif indent == 2 and line.startswith("- ") and current_key:
            if not isinstance(data.get(current_key), list):
                data[current_key] = []
            data[current_key].append(_coerce_scalar(line[2:].strip()))
        elif indent == 2 and line.endswith(":") and current_key:
            nested_key = line[:-1]
            data[current_key][nested_key] = []
        elif indent == 2 and ":" in line and current_key:
            key, value = line.split(":", 1)
            data[current_key][key.strip()] = _coerce_scalar(value.strip())
            nested_key = key.strip()
        elif indent == 4 and line.startswith("- ") and current_key and nested_key:
            if not isinstance(data[current_key].get(nested_key), list):
                data[current_key][nested_key] = []
            data[current_key][nested_key].append(_coerce_scalar(line[2:].strip()))

    return data


def load_style(style_id: str) -> dict:
    path = STYLE_DIR / f"{style_id}.yaml"
    if not path.exists():
        raise ValueError(f"Unknown style: {style_id}")
    text = path.read_text(encoding="utf-8")
    try:
        import yaml

        return yaml.safe_load(text) or {}
    except ImportError:
        return _load_yaml_fallback(text)
