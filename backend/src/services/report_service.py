import csv,io
from fastapi import HTTPException
from redis import Redis
from ..config.settings import REDIS_URL
from ..models import ReportRun
from ..utils.serialize import record
from .audit_service import log
queue=Redis.from_url(REDIS_URL,decode_responses=True)
def list_runs(db):return [record(x) for x in db.query(ReportRun).order_by(ReportRun.id.desc()).limit(100)]
def get_run(db,rid):
    row=db.get(ReportRun,rid)
    if not row:raise HTTPException(404,"报表运行不存在")
    return row
def create_run(db,data,user):
    if len(set(data.dimensions))!=len(data.dimensions):raise HTTPException(422,"不能重复选择维度")
    row=ReportRun(name=data.name,dimensions=data.dimensions,owner=user.name)
    db.add(row);db.flush();log(db,user.email,"report.enqueue",row.id);db.commit()
    try:queue.rpush("metric:jobs",row.id)
    except Exception:
        row.status="failed";row.error="队列暂时不可用，请重新提交";db.commit();raise HTTPException(503,row.error)
    return record(row)
def export_run(db,rid):
    row=get_run(db,rid)
    if row.status!="completed":raise HTTPException(409,"报表尚未完成")
    out=io.StringIO();w=csv.writer(out);keys=row.result['evaluation_order'];dims=row.result['dimensions']
    w.writerow(dims+keys+['reference_net','difference','source_count'])
    for cell in row.result['cells']:w.writerow([cell['dimensions'][k] for k in dims]+[cell['values'][k] for k in keys]+[cell[k] for k in ['reference_net','difference','source_count']])
    return out.getvalue()
