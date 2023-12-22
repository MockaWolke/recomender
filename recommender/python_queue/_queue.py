import subprocess
from subprocess import Popen, PIPE, TimeoutExpired
import threading
import queue
import sys
from loguru import logger
from recommender import REPO_PATH
from hashlib import sha256


class BackgroundTaskQueue:
    instance = None

    @classmethod
    def get_instance(cls, *args, **kwargs):
        if cls.instance is not None:
            return cls.instance

        cls.instance = cls(*args, **kwargs)
        return cls.instance

    def __init__(self, timeout=10) -> None:
        self.task_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker)
        self.worker_thread.start()
        self.task_status = {}
        self.timeout = timeout

    def add_task(self, user_id):
        job_id = sha256(f"{user_id} and some random noise (:".encode()).hexdigest()

        self.task_status[job_id] = "waiting"
        self.task_queue.put((job_id, user_id))

        return job_id

    def _worker(self):
        while True:
            job_id, user_id = self.task_queue.get()
            if user_id is None:
                break
            self._process_task(job_id, user_id)
            self.task_queue.task_done()

    def _process_task(self, job_id, user_id):
        process = Popen(
            [
                sys.executable,
                REPO_PATH / "recommender/python_queue/job.py",
                str(user_id),
            ],
            stdout=PIPE,
            stderr=PIPE,
        )

        try:
            stdout, stderr = process.communicate(timeout=self.timeout)
            if process.returncode != 0:
                self.task_status[job_id] = "error"

                logger.error(f"Background Process Failed for ID {user_id}: {stderr}")
            else:
                self.task_status[job_id] = "success"
                logger.success(f"Background Process for ID {user_id}")

        except TimeoutExpired:
            self.task_status[job_id] = "error"
            logger.error(f"Timeout. Job for User {user_id} exceeded {self.timeout}s")
