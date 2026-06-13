from distribution_pipeline.renderers.manifest import build_manifest


def test_build_manifest_records_platform_outputs(tmp_path):
    (tmp_path / "xhs" / "cards").mkdir(parents=True)
    (tmp_path / "xhs" / "cards" / "01-cover.html").write_text("", encoding="utf-8")
    (tmp_path / "xhs" / "post.md").write_text("", encoding="utf-8")

    manifest = build_manifest(tmp_path)

    assert manifest["platforms"]["xhs"]["post_md"].endswith("post.md")
    assert manifest["platforms"]["xhs"]["html_count"] == 1


def test_build_manifest_records_guizang_index_output(tmp_path):
    (tmp_path / "xhs").mkdir(parents=True)
    (tmp_path / "xhs" / "index.html").write_text("", encoding="utf-8")
    (tmp_path / "xhs" / "post.md").write_text("", encoding="utf-8")

    manifest = build_manifest(tmp_path)

    assert manifest["platforms"]["xhs"]["html_count"] == 1
    assert manifest["platforms"]["xhs"]["html_files"] == ["xhs/index.html"]


def test_build_manifest_records_guizang_wechat_output_pngs(tmp_path):
    (tmp_path / "wechat" / "output").mkdir(parents=True)
    (tmp_path / "wechat" / "index.html").write_text("", encoding="utf-8")
    (tmp_path / "wechat" / "appendix.md").write_text("", encoding="utf-8")
    (tmp_path / "wechat" / "output" / "wechat-21x9-cover.png").write_text("", encoding="utf-8")
    (tmp_path / "wechat" / "output" / "wechat-1x1-cover.png").write_text("", encoding="utf-8")

    manifest = build_manifest(tmp_path)

    assert manifest["platforms"]["wechat"]["html_files"] == ["wechat/index.html"]
    assert manifest["platforms"]["wechat"]["png_count"] == 2
    assert "wechat/output/wechat-21x9-cover.png" in manifest["platforms"]["wechat"]["png_files"]
