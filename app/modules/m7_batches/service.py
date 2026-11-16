import time
from app.modules.m6_reconcile.service import run as previous
from app.modules.m1_intake.service import source
from app.manifest import identify,create
from app.store import save,history
from .rules import validate
def run(options=None):
    options=validate(options or {})
    start=time.perf_counter()
    content=source(options)
    digest=identify(content.hex(),options.get("params",{}))
    result=previous(options)
    label="upload" if "text" in options else "sample:"+options.get("sample","dirty")
    result["manifest"]=create(digest,options.get("params",{}),time.perf_counter()-start,label)
    result=save(result)
    result["history"]=history()
    return result
