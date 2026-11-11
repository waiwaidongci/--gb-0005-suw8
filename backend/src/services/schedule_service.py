from datetime import datetime,timedelta,timezone
from fastapi import HTTPException
from ..models import DeliverySchedule
from ..utils.serialize import record
from .audit_service import log
def list_schedules(db):return [record(x) for x in db.query(DeliverySchedule).order_by(DeliverySchedule.id)]
def create_schedule(db,data,user):
    if len(set(data.dimensions))!=len(data.dimensions):raise HTTPException(422,"不能重复选择维度")
    if db.query(DeliverySchedule).filter_by(name=data.name).first():raise HTTPException(409,"交付计划名称已存在")
    fields=data.model_dump(exclude={'start_delay_seconds'})
    row=DeliverySchedule(**fields,next_run_at=(datetime.now(timezone.utc)+timedelta(seconds=data.start_delay_seconds)).isoformat(),owner=user.name)
    db.add(row);db.flush();log(db,user.email,"schedule.create",row.id);db.commit();return record(row)
def change_state(db,sid,active,user):
    row=db.get(DeliverySchedule,sid)
    if not row:raise HTTPException(404,"计划不存在")
    row.active=active;log(db,user.email,"schedule.resume" if active else "schedule.pause",row.id);db.commit();return record(row)
