import logging,time
from redis import Redis
from ..config.settings import REDIS_URL,JOB_QUEUE_KEY,ENQUEUE_RETRY,ENQUEUE_RETRY_DELAY
queue=Redis.from_url(REDIS_URL,decode_responses=True)
def enqueue(run_id):
    """把报表编号推入队列；失败即时重试，仍失败则抛出，由调用方保留 queued 状态交由对账兜底。"""
    last=None
    for attempt in range(ENQUEUE_RETRY+1):
        try:
            queue.rpush(JOB_QUEUE_KEY,run_id)
            return
        except Exception as exc:
            last=exc
            logging.warning("入队失败 run_id=%s attempt=%s: %s",run_id,attempt+1,exc)
            if attempt<ENQUEUE_RETRY:time.sleep(ENQUEUE_RETRY_DELAY)
    raise last
def queue_length():
    return queue.llen(JOB_QUEUE_KEY)
