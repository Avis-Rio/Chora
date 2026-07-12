from pathlib import Path

VENDOR = Path("distribution_pipeline/vendor/guizang")


def test_guizang_vendor_assets_exist():
    expected = [
        "LICENSE",
        "template-editorial-card.html",
        "template-swiss-card.html",
        "assets/magazine-bg-webgl.js",
        "validate-social-deck.mjs",
        "README.md",
    ]

    for name in expected:
        assert (VENDOR / name).exists(), name
