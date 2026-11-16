import sqlite3,json
from contextlib import contextmanager
from app.config import data_dir
from app.errors import reject
@contextmanager
def connect():
    d=data_dir();d.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(d/"records.sqlite",timeout=20)
    c.row_factory=sqlite3.Row
    c.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY,digest TEXT UNIQUE,body TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 1,decision TEXT NOT NULL DEFAULT '待复核')")
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()
def save(result):
    m=result["manifest"]
    with connect() as c:
        c.execute("INSERT OR IGNORE INTO runs(id,digest,body) VALUES(?,?,?)",(m["run_id"],m["sha256"],json.dumps(result,ensure_ascii=False)))
    return fetch(m["run_id"])
def _scope(body):
    results=body.get("results",[])
    months=sorted({str(x.get("start",""))[:7] for x in results if x.get("start")})
    lines=sorted({x.get("line_id") for x in results if x.get("line_id")})
    source=body.get("manifest",{}).get("source","")
    if not source and not months and not lines:return None
    return json.dumps([source,months,lines],ensure_ascii=False)
def _superseded(c,rowid,scope):
    if scope is None:return False
    for other in c.execute("SELECT body FROM runs WHERE rowid>?",(rowid,)):
        newer=_scope(json.loads(other["body"]))
        if newer is not None and newer==scope:return True
    return False
def _validity(c,row,data):
    return "已失效" if _superseded(c,row["rowid"],_scope(data)) else "有效"
def fetch(run_id):
    with connect() as c:
        row=c.execute("SELECT rowid,* FROM runs WHERE id=?",(run_id,)).fetchone()
        if row is None:reject("NOT_FOUND","运行不存在")
        data=json.loads(row["body"]);data["revision"]=row["revision"];data["decision"]=row["decision"]
        data["validity"]=_validity(c,row,data)
    return data
def history():
    with connect() as c:
        rows=c.execute("SELECT rowid,id,revision,decision,body FROM runs ORDER BY rowid DESC LIMIT 100").fetchall()
        return [{"id":row["id"],"revision":row["revision"],"decision":row["decision"],"validity":_validity(c,row,json.loads(row["body"]))} for row in rows]
def review(run_id,revision,decision,stage="临时"):
    if not isinstance(revision,int) or isinstance(revision,bool) or revision<1:reject("VERSION","修订号须为正整数")
    if decision not in ("通过","退回"):reject("DECISION","复核状态无效")
    if stage not in ("临时","正式"):reject("STAGE","结论阶段无效")
    with connect() as c:
        row=c.execute("SELECT rowid,body FROM runs WHERE id=?",(run_id,)).fetchone()
        if row is None:reject("NOT_FOUND","运行不存在")
        body=json.loads(row["body"])
        if _superseded(c,row["rowid"],_scope(body)):reject("SUPERSEDED","上游班报已更新，该结果失效，请复核最新运行")
        if decision=="通过" and stage=="正式" and not body.get("coverage",{}).get("complete"):reject("INCOMPLETE_COVERAGE","存在隔离班报，覆盖不齐，仅可提交临时结论")
        label="退回" if decision=="退回" else stage+decision
        changed=c.execute("UPDATE runs SET revision=revision+1,decision=? WHERE id=? AND revision=?",(label,run_id,revision)).rowcount
        if not changed:reject("STALE_VERSION","数据已更新，请重新载入")
    return fetch(run_id)
