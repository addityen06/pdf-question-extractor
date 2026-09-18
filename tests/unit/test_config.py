"""
Unit tests for the configuration system.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from questionai.core.config import load_config, PipelineConfig


class TestLoadConfig:
    def test_defaults_when_no_file(self):
        config = load_config(None)
        assert isinstance(config, PipelineConfig)
        assert config.ocr.dpi == 300
        assert config.extraction.native_text_threshold == 50
        assert config.question_detection.question_signal_threshold == 3

    def test_defaults_when_missing_file(self):
        config = load_config("/nonexistent/path/config.yaml")
        assert isinstance(config, PipelineConfig)

    def test_override_from_yaml(self):
        yaml_content = """
ocr:
  dpi: 600
extraction:
  native_text_threshold: 100
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            tmp_path = f.name

        config = load_config(tmp_path)
        assert config.ocr.dpi == 600
        assert config.extraction.native_text_threshold == 100
        # Unset values fall back to defaults
        assert config.question_detection.question_signal_threshold == 3

        Path(tmp_path).unlink()

    def test_question_separator_default(self):
        config = load_config(None)
        assert config.extraction.question_separator == "<<<QUESTION_END>>>"
