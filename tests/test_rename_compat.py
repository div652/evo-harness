from __future__ import annotations

import os
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

from evoharness.cli import legacy_main
from evoharness.environment import env_value
from evoharness.errors import AHERunnerError, ConfigurationError, EvoHarnessError
from evoharness.harness import HARNESS_ABI_VERSIONS, load_harness_manifest
from evoharness.meta.middleware import (
    AheLongToolOutputMiddleware,
    MetaLongToolOutputMiddleware,
)

from .conftest import make_example_project


def test_old_import_paths_resolve_to_the_same_objects() -> None:
    code = (
        "import warnings; warnings.simplefilter('error', DeprecationWarning)\n"
        "try:\n    import ahe_runner\nexcept DeprecationWarning:\n    pass\n"
        "warnings.simplefilter('ignore')\n"
        "import ahe_runner\n"
        "from ahe_runner.adapter import BenchmarkAdapterV2 as Old\n"
        "from ahe_runner.meta.model_client import (\n"
        "    RecordedExactModelClient as OldClient,\n)\n"
        "from evoharness.adapter import BenchmarkAdapterV2 as New\n"
        "from evoharness.meta.model_client import (\n"
        "    RecordedExactModelClient as NewClient,\n)\n"
        "assert Old is New and OldClient is NewClient\n"
        "import ahe_runner.adapter, evoharness.adapter\n"
        "assert ahe_runner.adapter is evoharness.adapter\n"
        "print(ahe_runner.__version__)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip()


def test_old_names_still_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert AHERunnerError is EvoHarnessError
    assert issubclass(ConfigurationError, AHERunnerError)
    assert AheLongToolOutputMiddleware is MetaLongToolOutputMiddleware
    assert "ahe.harness/v2" in HARNESS_ABI_VERSIONS

    monkeypatch.delenv("EVOHARNESS_PRE_STAGE_COMMAND", raising=False)
    monkeypatch.setenv("AHE_PRE_STAGE_COMMAND", "true")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert env_value("EVOHARNESS_PRE_STAGE_COMMAND") == "true"
    assert any("deprecated" in str(item.message) for item in caught)
    monkeypatch.setenv("EVOHARNESS_PRE_STAGE_COMMAND", "new")
    assert env_value("EVOHARNESS_PRE_STAGE_COMMAND") == "new"

    config_path = make_example_project(tmp_path)
    manifest = config_path.parent / "harness_manifest.yaml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "evoharness.harness/v2", "ahe.harness/v2"
        ),
        encoding="utf-8",
    )
    assert load_harness_manifest(manifest).abi_version == "ahe.harness/v2"
    legacy_config = config_path.with_name("ahe.yaml")
    os.replace(config_path, legacy_config)
    assert legacy_main(["validate", "--config", str(legacy_config)]) == 0
    captured = capsys.readouterr()
    assert "`ahe` command is deprecated" in captured.err
