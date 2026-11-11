import csv,io,logging
from fastapi import HTTPException
from ..models import ReportRun
from ..utils.serialize import record
from .audit_service import log
from .queue_service import enqueue
def list_runs(db):return [record(x) for x in db.query(ReportRun).order_by(ReportRun.id.desc()).limit(100)]
def get_run(db,rid):
    row=db.get(ReportRun,rid)
    if not row:raise HTTPException(404,"报表运行不存在")
    return row
def create_run(db,data,user):
    if len(set(data.dimensions))!=len(data.dimensions):raise HTTPException(422,"不能重复选择维度")
    row=ReportRun(name=data.name,dimensions=data.dimensions,owner=user.name)
    db.add(row);db.flush();log(db,user.email,"report.enqueue",row.id);db.commit()
    # 入队失败不改变报表编号与 queued 状态：即时重试后仍失败则由 worker 对账循环补推
    try:
        enqueue(row.id)
    except Exception as exc:
        logging.error("报表 %s 入队失败，等待对账补推: %s",row.id,exc)
    return record(row)
def export_run(db,rid):
    row=get_run(db,rid)
    if row.status!="completed":raise HTTPException(409,"报表尚未完成")
    out=io.StringIO();w=csv.writer(out);keys=row.result['evaluation_order'];dims=row.result['dimensions']
    w.writerow(dims+keys+['reference_net','difference','source_count'])
    for cell in row.result['cells']:w.writerow([cell['dimensions'][k] for k in dims]+[cell['values'][k] for k in keys]+[cell[k] for k in ['reference_net','difference','source_count']])
    return out.getvalue()
