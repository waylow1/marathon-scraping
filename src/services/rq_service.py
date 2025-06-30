import os

import redis
from rq import Queue, Retry

class RQService:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_conn = redis.from_url(self.redis_url)

    def set_queue(self, queue_name):
        self.queue = Queue(queue_name, connection=self.redis_conn)

    def enqueue_jobs(self, first_arg, second_arg=None):
        self.queue.enqueue(
            "src.task.run",
            args=(
                first_arg,
                second_arg,
            ),
            kwargs=None,
            job_timeout=-1,
            result_ttl=-1,
            failure_ttl=-1,
            retry=Retry(max=10),
        )


