from pathlib import Path


def test_ecosystem_map_avoids_stale_static_counts():
    readme = Path("README.md").read_text(encoding="utf-8")
    ecosystem = readme.split("## Ecosystem Map", 1)[1].split("## Key Concepts", 1)[0]

    assert "| Stars |" not in ecosystem
    assert "154+" not in ecosystem
    assert "78 |" not in ecosystem
    assert "64 |" not in ecosystem
    assert "45 |" not in ecosystem
