from pathlib import Path


def test_runtime_package_has_no_host_application_imports():
    root = Path(__file__).parents[1] / "src" / "voicekit"
    for path in root.rglob("*.py"):
        source = path.read_text("utf-8")
        assert "twentyfour_myself" not in source
