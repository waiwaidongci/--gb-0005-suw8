from fastapi import HTTPException
from ..models import SourceRow,Metric
from ..utils.serialize import record
from .pivot_service import build_report
def source_preview(db):
    return [record(x) for x in db.query(SourceRow).order_by(SourceRow.id).limit(100)]
def reconciliation(db):
    try:return build_report(db.query(SourceRow).order_by(SourceRow.id).all(),db.query(Metric).order_by(Metric.id).all(),["channel","month"])
    except ValueError as e:raise HTTPException(422,str(e))
