from ..models import Delivery
from ..utils.serialize import record
def list_deliveries(db):return [record(x) for x in db.query(Delivery).order_by(Delivery.id.desc()).limit(100)]
