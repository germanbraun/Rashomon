import pytest

from rashomon.config import ConfigError, load_config


def test_extends_adds_endpoints_and_overrides_settings(tmp_path):
    (tmp_path / "queries").mkdir()
    (tmp_path / "queries" / "q.rq").write_text("ASK {}")
    (tmp_path / "base.yaml").write_text(
        "settings: {timeout: 10, decimal_places: 3}\n"
        "endpoints: [{name: a, url: 'http://a'}, {name: b, url: 'http://b'}]\n"
        "queries: [{id: q, file: queries/q.rq}]\n"
    )
    (tmp_path / "more").mkdir()
    (tmp_path / "more" / "extra.yaml").write_text(
        "extends: ../base.yaml\n"
        "settings: {timeout: 60}\n"
        "endpoints: [{name: c, url: 'http://c', headers: {Authorization: Basic x}}]\n"
    )

    config = load_config(tmp_path / "more" / "extra.yaml")
    assert [e.name for e in config.endpoints] == ["a", "b", "c"]
    assert config.endpoints[2].headers == {"Authorization": "Basic x"}
    assert [q.text for q in config.queries] == ["ASK {}"]  # file resolved next to base.yaml
    assert (config.timeout, config.decimal_places) == (60, 3)


def test_extends_loop_and_duplicates(tmp_path):
    (tmp_path / "a.yaml").write_text("extends: b.yaml\n")
    (tmp_path / "b.yaml").write_text("extends: a.yaml\n")
    with pytest.raises(ConfigError, match="loops back"):
        load_config(tmp_path / "a.yaml")

    (tmp_path / "base.yaml").write_text(
        "endpoints: [{name: a, url: 'http://a'}, {name: b, url: 'http://b'}]\n"
        "queries: [{id: q, query: 'ASK {}'}]\n"
    )
    (tmp_path / "dup.yaml").write_text("extends: base.yaml\nendpoints: [{name: a, url: 'http://x'}]\n")
    with pytest.raises(ConfigError, match="Duplicate endpoint name: 'a'"):
        load_config(tmp_path / "dup.yaml")
