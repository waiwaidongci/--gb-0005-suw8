import os,sys,time,subprocess,uuid
from pathlib import Path
import pytest
BACKEND=Path(__file__).resolve().parents[1]
REDIS_SERVER=Path(os.environ.get("REDIS_SERVER","/tmp/redis-7.4.2/src/redis-server"))
REDIS_PORT=int(os.environ.get("REDIS_TEST_PORT","6391"))
# 环境变量必须在任何 src.* 导入前生效（settings 在导入时读取环境）
_TMP_ROOT=Path("/tmp/metric-ledger-tests")
_TMP_ROOT.mkdir(exist_ok=True)
_ART=_TMP_ROOT/"artifacts";_ART.mkdir(exist_ok=True)
# 每个测试进程独立 sqlite 文件，避免多次 pytest 并发时 drop/create 互相干扰
_DB=_TMP_ROOT/f"test-{os.getpid()}.sqlite"
if _DB.exists():_DB.unlink()
os.environ.update(
    DATABASE_URL=f"sqlite:///{_DB}",
    REDIS_URL=f"redis://127.0.0.1:{REDIS_PORT}/0",
    ARTIFACT_DIR=str(_ART),
    RUN_LEASE_SECONDS="2",
    ENQUEUE_RETRY="2",
    ENQUEUE_RETRY_DELAY="0.05",
)
sys.path.insert(0,str(BACKEND))
def _redis_available():
    if not REDIS_SERVER.exists():return False
    try:
        cli=str(REDIS_SERVER).replace("redis-server","redis-cli")
        out=subprocess.run([cli,"-p",str(REDIS_PORT),"ping"],capture_output=True,text=True,timeout=5)
        return out.stdout.strip()=="PONG"
    except Exception:return False
if not _redis_available():
    pytest.skip("本地 Redis 不可用（设置 REDIS_SERVER/REDIS_TEST_PORT）",allow_module_level=True)
@pytest.fixture(autouse=True)
def _flush_redis():
    from src.services.queue_service import queue
    queue.flushdb()
    yield
@pytest.fixture()
def db():
    from src.config.database import SessionLocal,engine,Base
    from src import models  # noqa:F401 确保所有模型已注册
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        yield session
    Base.metadata.drop_all(engine)
@pytest.fixture()
def seed_data(db):
    from src.models import Metric,SourceRow
    db.add_all([
        Metric(key="net_revenue",name="净收入",expression="revenue-refunds",unit="元",description="d",owner="t"),
        Metric(key="gross_profit",name="贡献毛利",expression="net_revenue-cost",unit="元",description="d",owner="t"),
    ])
    rows=[]
    for i in range(20):
        rows.append(SourceRow(source_key=f"K-{i:03d}",day="2026-10-01" if i<10 else "2026-09-01",
                              channel=["直营渠道","书店合作","数字发行"][i%3],region=["华东","华北","华南"][i%3],
                              revenue=200.0+i,cost=80.0,refunds=10.0,orders=10,reference_net=190.0))
    db.add_all(rows);db.commit()
    return db
def start_worker():
    log=open(f"/tmp/worker-{uuid.uuid4().hex}.log","w")
    proc=subprocess.Popen([sys.executable,"-u","-m","src.worker"],cwd=str(BACKEND),env=os.environ.copy(),
                          stdout=log,stderr=subprocess.STDOUT)
    return proc,log
def stop_worker(proc,log):
    proc.terminate()
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=10)
    log.close()
def wait_for(predicate,timeout=20,interval=0.2):
    deadline=time.time()+timeout
    while time.time()<deadline:
        if predicate():return True
        time.sleep(interval)
    return False
@pytest.fixture(scope="session",autouse=True)
def _no_stray_workers():
    # 测试开始前清掉残留 worker，避免它们抢走出队消息导致用例失败
    subprocess.run(["pkill","-9","-f","src.worker"],capture_output=True)
    yield
    subprocess.run(["pkill","-9","-f","src.worker"],capture_output=True)
@pytest.fixture()
def workers():
    procs=[]
    yield procs
    for proc,log in procs:stop_worker(proc,log)
