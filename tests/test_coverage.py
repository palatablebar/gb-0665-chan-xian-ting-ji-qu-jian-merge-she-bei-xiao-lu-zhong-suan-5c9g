import pytest
from app.modules.m7_batches.service import run
from app.modules.m7_batches.rules import csv_evidence
from app.modules.m6_reconcile.service import run as reconcile
from app.store import review,fetch,history
from app.errors import DomainError
from app.config import SAMPLE_DIR

def text_of(name):return (SAMPLE_DIR/name).read_text(encoding="utf-8")

def test_same_coverage_everywhere(dirty):
    saved=run(dirty);rid=saved["manifest"]["run_id"]
    statement=saved["coverage"]["statement"]
    assert reconcile(dirty)["coverage"]["statement"]==statement
    assert fetch(rid)["coverage"]["statement"]==statement
    assert statement in csv_evidence(fetch(rid))

def test_line_totals_carry_shifts(dirty):
    result=run(dirty)
    assert len(result["line_totals"])==6
    assert all(row["shifts"]=="6" for row in result["line_totals"])

def test_incomplete_coverage_blocks_formal(dirty):
    a=run(dirty);rid=a["manifest"]["run_id"]
    assert a["coverage"]["complete"] is False
    assert a["coverage"]["excluded_count"]==5
    with pytest.raises(DomainError) as exc:review(rid,1,"通过","正式")
    assert exc.value.code=="INCOMPLETE_COVERAGE"

def test_provisional_is_default(dirty):
    a=run(dirty);rid=a["manifest"]["run_id"]
    assert review(rid,1,"通过")["decision"]=="临时通过"

def test_formal_allowed_when_complete(clean):
    a=run(clean);rid=a["manifest"]["run_id"]
    assert a["coverage"]["complete"] is True
    assert review(rid,1,"通过","正式")["decision"]=="正式通过"

def test_stage_validation(dirty):
    a=run(dirty);rid=a["manifest"]["run_id"]
    with pytest.raises(DomainError):review(rid,1,"通过","月结")

def test_upstream_update_invalidates_old_result():
    v1=run({"text":text_of("dirty.csv")});rid1=v1["manifest"]["run_id"]
    review(rid1,1,"通过")
    v2=run({"text":text_of("clean.csv")});rid2=v2["manifest"]["run_id"]
    assert rid1!=rid2
    assert fetch(rid1)["validity"]=="已失效"
    assert fetch(rid2)["validity"]=="有效"
    with pytest.raises(DomainError) as exc:review(rid1,2,"退回")
    assert exc.value.code=="SUPERSEDED"

def test_samples_do_not_supersede_each_other(clean,dirty):
    a=run(dirty);b=run(clean)
    assert fetch(a["manifest"]["run_id"])["validity"]=="有效"
    assert fetch(b["manifest"]["run_id"])["validity"]=="有效"

def test_supplement_rerun_no_double_count():
    options={"text":text_of("clean.csv")}
    a=run(options);b=run(options)
    assert a["manifest"]["run_id"]==b["manifest"]["run_id"]
    assert len(history())==1
    assert fetch(a["manifest"]["run_id"])["reconciliation"]["good"]=="10260"

def test_anomaly_records_survive_supersede():
    v1=run({"text":text_of("dirty.csv")});rid1=v1["manifest"]["run_id"]
    codes=sorted(x["code"] for x in v1["quarantine"])
    run({"text":text_of("clean.csv")})
    kept=fetch(rid1)
    assert kept["validity"]=="已失效"
    assert sorted(x["code"] for x in kept["quarantine"])==codes
    assert all(isinstance(x.get("line"),int) and "raw" in x for x in kept["quarantine"])
