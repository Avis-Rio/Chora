"""generate_cover — split package for the Chora cover image generator.

Originally a single ``generate_cover.py`` (1008 lines). Replaced by the
following sub-modules (see ``skills/ARCHITECTURE.md`` §6):

- :mod:`generate_cover.palettes` — topic-keyed palette catalogue.
- :mod:`generate_cover.style` — LLM-driven style picker + style-file parsing.
- :mod:`generate_cover.title` — LLM-driven title cleaning + dirname heuristic.
- :mod:`generate_cover.image` — Gemini image generation entry point.
- :mod:`generate_cover.pipeline` — podcast cover pipeline (the public
  ``generate_podcast_cover`` etc.).
- :mod:`generate_cover._infra` — internal shared constants and LLM text client.

Public API re-exports preserve the original ``from generate_cover import X``
ergonomics for all call-sites:
``process_podcast`` / ``distribution_pipeline/assets/image_assets`` /
``distribution_pipeline/renderers/guizang/vision_subject_mapper`` /
``distribution_pipeline/assets/ai_image/gateway.py``.

Note: ``distribution_pipeline/assets/ai_image/gateway.py`` performs a dynamic
``import generate_cover`` against the repo root and calls
``generate_cover.generate_cover(...)``. The re-export below ensures that
callsite continues to work after the monolithic file was removed.
"""

from generate_cover.palettes import get_color_palette_for_topic
from generate_cover.style import (
    analyze_content_style,
    get_random_style,
    get_style_content,
    parse_style_content,
)
from generate_cover.title import (
    clean_title_with_llm,
    extract_title_from_dirname,
)
from generate_cover.image import generate_cover
from generate_cover.pipeline import (
    generate_podcast_cover,
    generate_podcast_cover_with_fallback,
    regenerate_missing_covers,
)

__all__ = [
    # palettes
    "get_color_palette_for_topic",
    # style
    "analyze_content_style",
    "get_random_style",
    "get_style_content",
    "parse_style_content",
    # title
    "clean_title_with_llm",
    "extract_title_from_dirname",
    # image
    "generate_cover",
    # pipeline
    "generate_podcast_cover",
    "generate_podcast_cover_with_fallback",
    "regenerate_missing_covers",
]
