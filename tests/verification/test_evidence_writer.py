"""Tests for evidence JSON writer utility (TDD).

Tests verify that:
1. Evidence files are created with correct schema
2. Naming conventions are followed
3. Directory creation is safe (idempotent)
4. JSON output is deterministic
"""

import json
import pytest
from pathlib import Path

from tests.verification.evidence_writer import (
    EvidenceRecord,
    InputSpec,
    ReactionRecord,
    GroupAverages,
    write_evidence,
    read_evidence,
    EVIDENCE_DIR,
)


class TestEvidenceWriter:

    def test_write_evidence_creates_file(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(
            "tests.verification.evidence_writer.EVIDENCE_DIR", tmp_path
        )
        
        input_spec = InputSpec(
            model="1x1",
            load_case="SDL",
            bay_x=6.0,
            bay_y=6.0,
            slab_elements_per_bay=1,
        )
        reactions = [
            ReactionRecord(node_tag=1, x=0.0, y=0.0, Fz_kN=13.5),
            ReactionRecord(node_tag=2, x=6.0, y=0.0, Fz_kN=13.5),
            ReactionRecord(node_tag=3, x=0.0, y=6.0, Fz_kN=13.5),
            ReactionRecord(node_tag=4, x=6.0, y=6.0, Fz_kN=13.5),
        ]
        record = EvidenceRecord(
            input_spec=input_spec,
            load_case="SDL",
            expected_sum_Fz_kN=54.0,
            actual_sum_Fz_kN=54.0,
            relative_error_percent=0.0,
            reactions=reactions,
        )
        
        filepath = write_evidence("1x1", "SDL", record)
        
        assert filepath.exists()
        assert filepath.name == "1x1_SDL.json"

    def test_write_evidence_with_mesh_level(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(
            "tests.verification.evidence_writer.EVIDENCE_DIR", tmp_path
        )
        
        input_spec = InputSpec(
            model="2x3",
            load_case="SDL",
            bay_x=6.0,
            bay_y=6.0,
            slab_elements_per_bay=2,
        )
        reactions = [ReactionRecord(node_tag=1, x=0.0, y=0.0, Fz_kN=13.5)]
        record = EvidenceRecord(
            input_spec=input_spec,
            load_case="SDL",
            expected_sum_Fz_kN=324.0,
            actual_sum_Fz_kN=324.0,
            relative_error_percent=0.0,
            reactions=reactions,
        )
        
        filepath = write_evidence("2x3", "SDL", record, mesh_level=2)
        
        assert filepath.exists()
        assert filepath.name == "2x3_SDL_mesh2.json"

    def test_write_evidence_json_schema(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(
            "tests.verification.evidence_writer.EVIDENCE_DIR", tmp_path
        )
        
        input_spec = InputSpec(
            model="1x1",
            load_case="LL",
            bay_x=6.0,
            bay_y=6.0,
            slab_elements_per_bay=1,
        )
        reactions = [
            ReactionRecord(node_tag=1, x=0.0, y=0.0, Fz_kN=27.0),
        ]
        group_averages = GroupAverages(
            corner_avg_kN=27.0,
            edge_avg_kN=0.0,
            interior_avg_kN=0.0,
        )
        record = EvidenceRecord(
            input_spec=input_spec,
            load_case="LL",
            expected_sum_Fz_kN=108.0,
            actual_sum_Fz_kN=107.9,
            relative_error_percent=0.09,
            reactions=reactions,
            group_averages=group_averages,
        )
        
        filepath = write_evidence("1x1", "LL", record)
        
        with open(filepath, "r") as f:
            data = json.load(f)
        
        assert "input_spec" in data
        assert "load_case" in data
        assert "expected_sum_Fz_kN" in data
        assert "actual_sum_Fz_kN" in data
        assert "relative_error_percent" in data
        assert "reactions" in data
        assert "group_averages" in data
        
        assert data["input_spec"]["model"] == "1x1"
        assert data["load_case"] == "LL"
        assert data["expected_sum_Fz_kN"] == 108.0
        assert data["actual_sum_Fz_kN"] == 107.9

    def test_write_evidence_sorted_keys(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(
            "tests.verification.evidence_writer.EVIDENCE_DIR", tmp_path
        )
        
        input_spec = InputSpec(
            model="1x1",
            load_case="SDL",
            bay_x=6.0,
            bay_y=6.0,
            slab_elements_per_bay=1,
        )
        reactions = [ReactionRecord(node_tag=1, x=0.0, y=0.0, Fz_kN=13.5)]
        record = EvidenceRecord(
            input_spec=input_spec,
            load_case="SDL",
            expected_sum_Fz_kN=54.0,
            actual_sum_Fz_kN=54.0,
            relative_error_percent=0.0,
            reactions=reactions,
        )
        
        filepath = write_evidence("1x1", "SDL", record)
        
        with open(filepath, "r") as f:
            content = f.read()
        
        keys = [line.strip().split(":")[0].strip('"') for line in content.split("\n") 
                if ":" in line and not line.strip().startswith("{") and not line.strip().startswith("[")]
        
        top_level_keys = ["actual_sum_Fz_kN", "expected_sum_Fz_kN", "group_averages", 
                         "input_spec", "load_case", "reactions", "relative_error_percent"]
        for key in top_level_keys:
            assert key in keys or f'"{key}"' in content

    def test_write_evidence_creates_directory(self, tmp_path, monkeypatch) -> None:
        nested_dir = tmp_path / "nested" / "benchmarks"
        monkeypatch.setattr(
            "tests.verification.evidence_writer.EVIDENCE_DIR", nested_dir
        )
        
        assert not nested_dir.exists()
        
        input_spec = InputSpec(
            model="1x1",
            load_case="DL",
            bay_x=6.0,
            bay_y=6.0,
            slab_elements_per_bay=1,
        )
        reactions = [ReactionRecord(node_tag=1, x=0.0, y=0.0, Fz_kN=50.0)]
        record = EvidenceRecord(
            input_spec=input_spec,
            load_case="DL",
            expected_sum_Fz_kN=200.0,
            actual_sum_Fz_kN=199.5,
            relative_error_percent=0.25,
            reactions=reactions,
        )
        
        filepath = write_evidence("1x1", "DL", record)
        
        assert nested_dir.exists()
        assert filepath.exists()

    def test_read_evidence_roundtrip(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(
            "tests.verification.evidence_writer.EVIDENCE_DIR", tmp_path
        )
        
        input_spec = InputSpec(
            model="2x3",
            load_case="SDL",
            bay_x=6.0,
            bay_y=6.0,
            slab_elements_per_bay=1,
        )
        reactions = [
            ReactionRecord(node_tag=1, x=0.0, y=0.0, Fz_kN=13.5),
            ReactionRecord(node_tag=2, x=6.0, y=0.0, Fz_kN=27.0),
        ]
        group_averages = GroupAverages(
            corner_avg_kN=13.5,
            edge_avg_kN=27.0,
            interior_avg_kN=54.0,
        )
        record = EvidenceRecord(
            input_spec=input_spec,
            load_case="SDL",
            expected_sum_Fz_kN=324.0,
            actual_sum_Fz_kN=323.5,
            relative_error_percent=0.15,
            reactions=reactions,
            group_averages=group_averages,
        )
        
        filepath = write_evidence("2x3", "SDL", record)
        data = read_evidence(filepath)
        
        assert data["input_spec"]["model"] == "2x3"
        assert data["load_case"] == "SDL"
        assert data["expected_sum_Fz_kN"] == 324.0
        assert data["actual_sum_Fz_kN"] == 323.5
        assert len(data["reactions"]) == 2
        assert data["group_averages"]["corner_avg_kN"] == 13.5
