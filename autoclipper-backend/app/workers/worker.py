from rq import Worker
from app.workers.queue import queue, redis_conn

if __name__ == "__main__":
    w = Worker([queue], connection=redis_conn)
    w.work()
