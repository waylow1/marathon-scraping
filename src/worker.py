import os
import random
import socket
import string
import argparse

import redis
from rq import Queue, Worker

parser = argparse.ArgumentParser()
parser.add_argument("--dossard", type=str, help="Nom de la queue (dossard)", required=True)
args = parser.parse_args()

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_conn: redis.Redis = redis.from_url(REDIS_URL)

queue_name: str = args.dossard
queue = Queue(queue_name, connection=redis_conn)

name: str = (
    socket.gethostname()
    + "->"
    + "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(16))
)

worker = Worker([queue], name=name, connection=redis_conn)
worker.work()