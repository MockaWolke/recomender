from movie_recommender import REPO_PATH, BACKGROUND_PORT
from requests import Timeout
from hashlib import sha256
import requests
import time
from loguru import logger
from subprocess import Popen, PIPE
import threading
import queue
import sys
import socket


def is_port_available(port) -> bool:
    """Check wether port is Avalibale"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def enqueue_output(out, queue):
    for line in iter(out.readline, b""):
        queue.put(line)
    out.close()


def get_stderr_text(process: Popen, wait_time: int) -> str:
    stderr_queue = queue.Queue()

    # Start threads to populate queues
    stderr_thread = threading.Thread(
        target=enqueue_output, args=(process.stderr, stderr_queue)
    )
    stderr_thread.daemon = True
    stderr_thread.start()

    time.sleep(wait_time)

    stderr_output = []

    while not stderr_queue.empty():
        stderr_output.append(stderr_queue.get_nowait())

    return "".join(stderr_output)


class BackgroundInterface:
    @staticmethod
    def start_background_api(waiting=10, timeout=2) -> bool:
        # if not is_port_available(BACKGROUND_PORT):
        #     raise ValueError(
        #         f"The BACKGROUND_PORT {BACKGROUND_PORT} is not free, choose another in the .env!"
        #     )

        if BackgroundInterface.check_health(2):
            raise ValueError(f"Already an API at port {BACKGROUND_PORT}")

        logger.debug(f"The python executable {sys.executable}")

        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "api:background_api",
            "--host",
            "0.0.0.0",
            "--port",
            BACKGROUND_PORT,
        ]

        cmd = [str(i) for i in cmd]

        try:
            process = Popen(
                cmd,
                cwd=str(REPO_PATH / "movie_recommender/background_api/"),
                stderr=PIPE,
                text=True,
            )

            start = time.time()

            while time.time() - start < waiting:
                try:
                    if BackgroundInterface.check_health(timeout):
                        std_err_output = get_stderr_text(process, 1)
                        logger.debug(
                            f"The Uvicorn startup outputs: \n {std_err_output}"
                        )

                        return "Uvicorn running on" in std_err_output
                except:
                    pass
                time.sleep(0.25)

            raise Exception("The Api was not succesfully started")

        except Exception as e:
            logger.error(f"Failed to start background API: {e}")
            return False

    @staticmethod
    def check_health(timeout) -> bool:
        try:
            start = time.time()
            endpoint = f"http://localhost:{BACKGROUND_PORT}/health/"

            response = requests.get(endpoint, timeout=timeout)

            # Raise an HTTPError for bad requests
            response.raise_for_status()
            logger.success(
                f"Received {response.status_code} - Took {time.time() -start :.4f}"
            )
            return True
        except Exception as e:
            return False

    @staticmethod
    def commit_job(user_id: int, timeout: float) -> bool:
        response = requests.post(
            f"http://localhost:{BACKGROUND_PORT}/calculate_recommendations/?user_id={user_id}",
            timeout=timeout,
        )

        response.raise_for_status()  # Raise an HTTPError for bad requests
        logger.debug(f"received respone {response}")

        return response.json()
