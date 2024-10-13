import os
import subprocess
import logging
import docker

from benchmark.models import Testcase


logger = logging.getLogger(__name__)


class TestEnvService:

    def __init__(self, testcase: Testcase):
        self.testcase = testcase

    def start_testenv(self) -> list:
        """Starts the Docker environment for the test case."""
        compose_path = os.path.join("/app/", self.testcase.path, 'docker-compose.yml')
        try:
            subprocess.run(
                [
                    "docker-compose",
                    "-f", compose_path,
                    "up", "-d",
                    "--build",
                    "--remove-orphans",
                    "--force-recreate",
                    "-V"
                ],
                check=True
            )
            logger.info("Docker Compose started successfully.")

            client = docker.from_env()
            containers = [container for container in client.containers.list() if self.testcase.id.lower() in container.name]
            return containers
        except subprocess.CalledProcessError as e:
            logger.error(f"Error occurred while running Docker Compose: {e}")
            return []


    def stop_testenv(self) -> None:
        """Stops the Docker environment for the test case."""
        compose_path = os.path.join("/app/", self.testcase.path, 'docker-compose.yml')
        try:
            subprocess.run(
                ["docker-compose", "-f", compose_path, "down", "-v"],
                check=True
            )
            logger.info("Docker Compose stopped successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error occurred while stopping Docker Compose: {e}")