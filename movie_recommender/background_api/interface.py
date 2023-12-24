from movie_recommender import REPO_PATH, BACKGROUND_PORT
from requests import Timeout
from hashlib import sha256
import requests
import time
from loguru import logger
from subprocess import Popen
import sys


class BackgroundInterface:
    @staticmethod
    def start_background_api(waiting=10, timeout=2) -> bool:
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
            api = Popen(
                cmd,
                cwd=str(REPO_PATH / "movie_recommender/background_api/"),
            )

            start = time.time()

            while time.time() - start < waiting:
                try:
                    if BackgroundInterface.check_health(timeout):
                        return True
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

        return response.json()
