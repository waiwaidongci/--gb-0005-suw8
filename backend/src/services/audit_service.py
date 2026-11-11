from ..models import Audit
from ..utils.serialize import record
def log(db, actor, action, target):
    db.add(Audit(actor=actor, action=action, target=str(target)))
def list_audit(db):
    return [record(x) for x in db.query(Audit).order_by(Audit.id.desc()).limit(100)]
