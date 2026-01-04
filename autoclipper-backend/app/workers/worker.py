from rq import Worker
from app.workers.queue import queue, io_queue, ai_queue, render_queue, redis_conn

if __name__ == "__main__":
    w = Worker([io_queue, ai_queue, render_queue, queue], connection=redis_conn)
    w.work()
