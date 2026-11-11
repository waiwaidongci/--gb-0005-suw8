from fastapi import HTTPException
from ..models import Metric,SourceRow
from ..utils.serialize import record
from .expression_service import compile_metrics
from .pivot_service import build_report
from .audit_service import log
def list_metrics(db):
    rows=db.query(Metric).order_by(Metric.id).all()
    _,order,deps=compile_metrics(rows)
    return {"items":[dict(record(m),dependencies=deps[m.key]) for m in rows],"evaluation_order":order}
def create_metric(db,data,user):
    if db.query(Metric).filter_by(key=data.key).first():raise HTTPException(409,"指标标识已存在")
    row=Metric(**data.model_dump(),owner=user.name)
    try:
        prospective=db.query(Metric).order_by(Metric.id).all()+[row]
        compile_metrics(prospective)
        sources=db.query(SourceRow).order_by(SourceRow.id).all()
        if sources:
            build_report(sources,prospective,["channel","month"])
            build_report(sources,prospective,["region","month"])
    except ValueError as e:raise HTTPException(422,str(e))
    db.add(row);db.flush();log(db,user.email,"metric.register",row.key);db.commit()
    return record(row)
