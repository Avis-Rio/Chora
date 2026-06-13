from distribution_pipeline.assets.providers import discover_image_candidates, load_image_provider_env


def test_load_image_provider_env_reads_local_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    monkeypatch.delenv("UNSPLASH_ACCESS_KEY", raising=False)
    (tmp_path / ".env").write_text(
        "PEXELS_API_KEY=pexels-from-env\nUNSPLASH_ACCESS_KEY=unsplash-from-env\n",
        encoding="utf-8",
    )

    env = load_image_provider_env()

    assert env["PEXELS_API_KEY"] == "pexels-from-env"
    assert env["UNSPLASH_ACCESS_KEY"] == "unsplash-from-env"


def test_discover_image_candidates_uses_dotenv_keys(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    monkeypatch.delenv("UNSPLASH_ACCESS_KEY", raising=False)
    (tmp_path / ".env").write_text(
        "PEXELS_API_KEY=pexels-from-env\nUNSPLASH_ACCESS_KEY=unsplash-from-env\n",
        encoding="utf-8",
    )
    calls = []

    def fake_fetch_json(url, headers=None):
        calls.append((url, headers or {}))
        if "pexels.com" in url:
            return {
                "photos": [
                    {
                        "url": "https://pexels.example/photo/lab",
                        "photographer": "Ada",
                        "photographer_url": "https://pexels.example/ada",
                        "width": 1200,
                        "height": 800,
                        "alt": "AI lab",
                        "src": {"large": "https://images.example/pexels-lab.jpg"},
                    }
                ]
            }
        if "unsplash.com" in url:
            return {
                "results": [
                    {
                        "width": 1200,
                        "height": 800,
                        "alt_description": "Research lab",
                        "urls": {"regular": "https://images.example/unsplash-lab.jpg"},
                        "links": {"html": "https://unsplash.example/photo/lab"},
                        "user": {
                            "name": "Grace",
                            "links": {"html": "https://unsplash.example/grace"},
                        },
                    }
                ]
            }
        return {}

    candidates = discover_image_candidates(
        {
            "asset_id": "xhs-02-evidence",
            "role": "evidence",
            "query": "AI research lab",
        },
        fetch_json=fake_fetch_json,
        max_candidates=3,
    )

    providers = {candidate["provider"] for candidate in candidates}
    assert {"pexels", "unsplash"} <= providers
    assert any(headers.get("Authorization") == "pexels-from-env" for _url, headers in calls)
    assert any(headers.get("Authorization") == "Client-ID unsplash-from-env" for _url, headers in calls)
