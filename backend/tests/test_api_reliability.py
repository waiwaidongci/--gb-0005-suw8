"""HTTP 层验证：队列故障下手工报表接口仍返回 202 且保留编号，恢复后自动完成。"""
from fastapi.testclient import TestClient
from src.main import app
from src.controllers.dependencies import current_user
from src.constants.status import RunStatus
from src.models import ReportRun
from src.services.queue_service import queue
from src.services.worker_service import recover_pending,process_job
from src.config.settings import JOB_QUEUE_KEY
class _FakeUser:
    id=1;email="analyst@hengchi.demo";name="宋予";role="analyst"
def test_post_report_survives_queue_outage(seed_data,monkeypatch):
    app.dependency_overrides[current_user]=lambda:_FakeUser()
    client=TestClient(app)
    calls={"n":0}
    def broken(*a,**k):
        calls["n"]+=1;raise ConnectionError("redis down")
    monkeypatch.setattr(queue,"rpush",broken)
    try:
        resp=client.post("/reports",json={"name":"接口层故障报表","dimensions":["channel","month"]})
        # 不再像旧实现那样返回 503：报表已落库，队列故障由重试与对账兜底
        assert resp.status_code==202,resp.text
        body=resp.json()
        assert body["status"]==RunStatus.QUEUED
        run_id=body["id"]
        assert calls["n"]==3  # 初次 + 2 次即时重试
    finally:
        monkeypatch.undo()
    # 队列恢复后自动补推并完成，编号不变
    recover_pending(seed_data)
    assert queue.lrange(JOB_QUEUE_KEY,0,-1)==[str(run_id)]
    process_job(seed_data,str(run_id))
    seed_data.expire_all()
    run=seed_data.get(ReportRun,run_id)
    assert run.status==RunStatus.COMPLETED and run.id==run_id
    app.dependency_overrides.clear()
