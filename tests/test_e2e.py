from fastapi.testclient import TestClient
from app.main import app
from app.config import MODULES

def test_pages():
    with TestClient(app) as c:
        for slug,label in MODULES:assert c.get("/"+slug).status_code==200
def test_api_and_export():
    with TestClient(app) as c:
        a=c.post("/api/runs",json={"sample":"dirty"}).json();rid=a["manifest"]["run_id"]
        assert c.get(f"/api/runs/{rid}/evidence.csv").status_code==200
        assert a["reconciliation"]["time_ok"] is True
def test_wrong_csv():
    with TestClient(app) as c:assert c.post("/api/runs",json={"text":"a,b\n1,2"}).status_code==422

def test_percentages_in_page():
    with TestClient(app) as c:
        page=c.get("/calculate").text
        assert "83.33%" in page and "63.33%" in page
        assert "0.833333333333" not in page.split("title=",1)[0]

def test_coverage_statement_on_both_pages():
    with TestClient(app) as c:
        rid=c.post("/api/runs",json={"sample":"dirty"}).json()["manifest"]["run_id"]
        reconcile=c.get("/reconcile",params={"run_id":rid}).text
        batches=c.get("/batches",params={"run_id":rid}).text
        assert "有效覆盖" in reconcile and "有效覆盖" in batches
        statement=reconcile.split("有效覆盖：",1)[1].split("<")[0]
        assert statement in batches

def test_review_stage_gate():
    with TestClient(app) as c:
        rid=c.post("/api/runs",json={"sample":"dirty"}).json()["manifest"]["run_id"]
        blocked=c.post(f"/api/runs/{rid}/review",json={"revision":1,"decision":"通过","stage":"正式"})
        assert blocked.status_code==422 and blocked.json()["detail"]["code"]=="INCOMPLETE_COVERAGE"
        ok=c.post(f"/api/runs/{rid}/review",json={"revision":1,"decision":"通过","stage":"临时"})
        assert ok.status_code==200 and ok.json()["decision"]=="临时通过"

def test_superseded_review_returns_409():
    from app.config import SAMPLE_DIR
    with TestClient(app) as c:
        v1=c.post("/api/runs",json={"text":(SAMPLE_DIR/"dirty.csv").read_text(encoding="utf-8")}).json()
        rid=v1["manifest"]["run_id"]
        assert c.post(f"/api/runs/{rid}/review",json={"revision":1,"decision":"通过"}).status_code==200
        c.post("/api/runs",json={"text":(SAMPLE_DIR/"clean.csv").read_text(encoding="utf-8")})
        stale=c.post(f"/api/runs/{rid}/review",json={"revision":2,"decision":"退回"})
        assert stale.status_code==409 and stale.json()["detail"]["code"]=="SUPERSEDED"
        kept=c.get(f"/api/runs/{rid}/evidence.csv").text
        assert "有效覆盖" in kept and "COUNT" in kept
