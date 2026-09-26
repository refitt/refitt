import importlib.util
from pathlib import Path


def _script_module():
    path = Path("scripts/find_host.py")
    spec = importlib.util.spec_from_file_location("find_host_script", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Associator:
    def find_host(self, *args, **kwargs):
        class Result:
            def model_dump_json(self, indent):
                return '{"outcome":"hostless"}'
        return Result()


def test_script_writes_json(tmp_path, monkeypatch):
    script = _script_module()
    monkeypatch.setattr(script, "_associator", lambda args: _Associator())
    output = tmp_path / "result.json"
    assert script.main(["--ra", "1", "--dec", "2", "--ps1-hats", "/tmp/ps1", "--output", str(output)]) == 0
    assert output.read_text() == '{"outcome":"hostless"}\n'


def test_script_requires_a_catalog_path():
    script = _script_module()
    try:
        script.main(["--ra", "1", "--dec", "2"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected argparse to reject an incomplete command")
