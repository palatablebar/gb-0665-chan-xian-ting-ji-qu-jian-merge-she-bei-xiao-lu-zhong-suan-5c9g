from decimal import Decimal

def reconcile(result):
    items=result["results"]
    def total(key):return sum((Decimal(x[key]) for x in items),Decimal(0))
    planned,runtime,down,total_count,good=[total(k) for k in ("planned","runtime","downtime_minutes","total","good")]
    return {"planned":str(planned),"runtime":str(runtime),"downtime":str(down),"total":str(total_count),"good":str(good),"scrap":str(total_count-good),"time_ok":planned==runtime+down,"count_ok":result["input_count"]==len(result["rows"])+len(result["quarantine"])+result["blank_count"],"production_ok":good<=total_count,"exceptions":sum(x["status"]!="通过" for x in items)}

def group_lines(items):
    groups={}
    for item in items:
        bucket=groups.setdefault(item["line_id"],{"line_id":item["line_id"],"shifts":0,"planned":Decimal(0),"runtime":Decimal(0),"downtime_minutes":Decimal(0),"total":Decimal(0),"good":Decimal(0)})
        bucket["shifts"]+=1
        for key in ("planned","runtime","downtime_minutes","total","good"):bucket[key]+=Decimal(item[key])
    return [{k:str(v) for k,v in row.items()} for row in groups.values()]

def coverage(result):
    records=sorted(x["record_id"] for x in result["results"])
    excluded=[]
    for row in result["quarantine"]:
        raw=row.get("raw")
        excluded.append({"line":row.get("line"),"code":row.get("code"),"record_id":raw.get("record_id") if isinstance(raw,dict) else None})
    lines={}
    for x in result["results"]:lines[x["line_id"]]=lines.get(x["line_id"],0)+1
    complete=not excluded
    if not records:span="无"
    elif len(records)==1:span=records[0]
    else:span=f"{records[0]}…{records[-1]}"
    if complete:statement=f"有效覆盖：采信 {len(records)} 班（{span}，{len(lines)} 条产线），无隔离班报，覆盖完整，可进入正式考核。"
    else:statement=f"有效覆盖：采信 {len(records)} 班（{span}，{len(lines)} 条产线）；隔离 {len(excluded)} 班未计入合计，缺口不计零产。覆盖不齐，仅可提交临时结论，正式考核须待补齐重算。"
    return {"complete":complete,"included_count":len(records),"excluded_count":len(excluded),"records":records,"excluded":excluded,"lines":{k:lines[k] for k in sorted(lines)},"statement":statement}
