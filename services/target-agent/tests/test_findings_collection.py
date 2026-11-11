"""Selected-suite collection, explicit skips, and legacy evidence compatibility."""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts/collect_adversarial_findings.py"
SPEC = importlib.util.spec_from_file_location("assessment_collector_tests", SCRIPT)
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


def save(folder, name, value):
    (folder / name).write_text(json.dumps(value), encoding="utf-8")


def artifacts(folder, ids, *, skipped=False, legacy=False):
    save(folder, "metadata.json", {} if legacy else {"selected_case_ids": ids})
    save(folder, "summary.json", [{"case_id": case_id} for case_id in ids])
    for case_id in ids:
        body = {"test_id": case_id, "scan_id": "SCAN-" + case_id}
        record = {"case": {"case_id": case_id}, "request": body,
                  "submission_result": "Not run" if skipped else "Accepted",
                  "execution_attempted": not skipped}
        if skipped:
            record["not_run_reason"] = "requires memory test setup"
        else:
            record["response"] = {**body, "steps": [{"action": {"type": "final"}}],
                                  "stop_reason": "final"}
        save(folder, case_id + ".json", record)


def test_selected_tool_suite_does_not_require_seven_legacy_files(tmp_path):
    artifacts(tmp_path, ["TM-01", "TM-02"])
    _, result = collector.combine(tmp_path)
    assert result["collection_complete"] and result["execution_complete"]
    assert result["expected_case_ids"] == ["TM-01", "TM-02"]
    assert result["missing_case_ids"] == []


def test_skipped_memory_artifacts_are_complete_collection_but_not_execution(tmp_path):
    artifacts(tmp_path, ["MC-01", "MC-02", "MC-03"], skipped=True)
    _, result = collector.combine(tmp_path)
    assert result["collection_complete"]
    assert not result["execution_complete"]
    assert result["counts"]["not_run"] == 3
    assert result["counts"]["execution_attempted"] == 0
    assert result["counts"]["cases_without_step_lists"] == 0
    assert all(row["not_run_reason"] for row in result["cases"])


def test_missing_selected_case_is_detected(tmp_path):
    artifacts(tmp_path, ["TM-01", "TM-02"])
    (tmp_path / "TM-02.json").unlink()
    _, result = collector.combine(tmp_path)
    assert result["missing_case_ids"] == ["TM-02"]
    assert not result["collection_complete"]


def test_original_seven_case_evidence_still_collects(tmp_path):
    artifacts(tmp_path, list(collector.LEGACY_CASE_IDS), legacy=True)
    _, result = collector.combine(tmp_path)
    assert result["collection_complete"]
    assert result["expected_case_ids"] == list(collector.LEGACY_CASE_IDS)


def test_extra_artifact_cannot_expand_selected_suite_silently(tmp_path):
    artifacts(tmp_path, ["TM-01"])
    save(tmp_path, "TM-02.json", {"case": {"case_id": "TM-02"},
                                  "request": {"test_id": "TM-02", "scan_id": "different"}})
    _, result = collector.combine(tmp_path)
    assert result["unexpected_case_ids"] == ["TM-02"]
    assert not result["collection_complete"]


def test_not_run_with_response_is_flagged(tmp_path):
    artifacts(tmp_path, ["MC-01"], skipped=True)
    path = tmp_path / "MC-01.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["response"] = {**record["request"], "stop_reason": "final", "steps": []}
    save(tmp_path, path.name, record)
    _, result = collector.combine(tmp_path)
    assert not result["collection_complete"]
    assert any("Not-run" in note for note in result["cases"][0]["identity_mismatches"])


@pytest.mark.parametrize("bad_summary", [None, {}, [{"case_id": ["TM-01"]}]])
def test_bad_summary_is_reported_instead_of_crashing(tmp_path, bad_summary):
    artifacts(tmp_path, ["TM-01"])
    save(tmp_path, "summary.json", bad_summary)
    _, result = collector.combine(tmp_path)
    assert not result["collection_complete"]
    assert result["collection_issues"]


def test_bad_selected_manifest_is_reported(tmp_path):
    artifacts(tmp_path, ["TM-01"])
    save(tmp_path, "metadata.json", {"selected_case_ids": [{"case_id": "TM-01"}]})
    _, result = collector.combine(tmp_path)
    assert not result["collection_complete"]
    assert result["expected_case_ids"] == ["TM-01"]


def test_multiple_collections_ignore_generated_reports(tmp_path):
    artifacts(tmp_path, ["TM-01"])
    first, _ = collector.combine(tmp_path)
    second, result = collector.combine(tmp_path)
    assert first != second
    assert result["collection_complete"] and len(result["cases"]) == 1


def test_mismatched_scan_cannot_be_reported_as_complete_execution(tmp_path):
    artifacts(tmp_path, ["TM-01"])
    record = json.loads((tmp_path / "TM-01.json").read_text(encoding="utf-8"))
    record["response"]["scan_id"] = "UNRELATED-SCAN"
    save(tmp_path, "TM-01.json", record)
    _, result = collector.combine(tmp_path)
    assert not result["collection_complete"]
    assert not result["execution_complete"]
