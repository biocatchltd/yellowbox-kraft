from __future__ import annotations

from contextlib import closing
from typing import Any, ContextManager, cast

from docker import DockerClient

try:
    from kafka import KafkaConsumer, KafkaProducer
    from kafka.errors import KafkaError

    KafkaException = KafkaError
except ImportError:
    KafkaConsumer = KafkaProducer = None
    # python3.12 uses confluent_kafka
    from confluent_kafka import Consumer as ConfluentConsumer
    from confluent_kafka import KafkaException
    from confluent_kafka.error import KafkaError
from yellowbox.containers import create_and_pull
from yellowbox.retry import RetrySpec
from yellowbox.subclasses import AsyncRunMixin, RunMixin, SingleContainerService
from yellowbox.utils import DOCKER_EXPOSE_HOST, get_free_port

__all__ = ["KraftService"]

KAFKA_INNER_PORT = 9092


class KraftService(SingleContainerService, RunMixin, AsyncRunMixin):
    container_port: int = KAFKA_INNER_PORT

    def __init__(
        self,
        docker_client: DockerClient,
        image: str = "bitnamilegacy/kafka:4.0.0-debian-12-r10",
        bitnami_debug: bool = False,
        **kwargs,
    ):
        self.port = get_free_port()
        extra_broker_env = {}
        if bitnami_debug:
            extra_broker_env["BITNAMI_DEBUG"] = "true"
        container = create_and_pull(
            docker_client,
            image,
            ports={self.port: ("0.0.0.0", self.port)},
            publish_all_ports=True,
            detach=True,
            environment={
                "KAFKA_CFG_PROCESS_ROLES": "controller,broker",
                "KAFKA_CFG_CONTROLLER_QUORUM_VOTERS": "0@localhost:9093",
                "KAFKA_CFG_CONTROLLER_LISTENER_NAMES": "CONTROLLER",
                "KAFKA_CFG_NODE_ID": "0",
                "KAFKA_CFG_LISTENERS": f"PLAINTEXT://:9092,CONTROLLER://:9093,EXTERNAL://0.0.0.0:{self.port}",
                "KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP": (
                    "CONTROLLER:PLAINTEXT,EXTERNAL:PLAINTEXT,PLAINTEXT:PLAINTEXT"
                ),
                "KAFKA_CFG_ADVERTISED_LISTENERS": f"EXTERNAL://localhost:{self.port},PLAINTEXT://kafka:9092",
                "ALLOW_PLAINTEXT_LISTENER": "yes",
                "KAFKA_ENABLE_KRAFT": "true",
                **extra_broker_env,
            },
        )
        super().__init__(container, **kwargs)

    def consumer(self, **kwargs) -> ContextManager[KafkaConsumer]:
        if KafkaConsumer is None:
            raise ImportError("kafka-python is not installed")
        port = self.port
        return cast(
            "ContextManager[KafkaConsumer]",
            closing(
                KafkaConsumer(
                    bootstrap_servers=[f"{DOCKER_EXPOSE_HOST}:{port}"], security_protocol="PLAINTEXT", **kwargs
                )
            ),
        )

    def producer(self, **kwargs) -> ContextManager[KafkaProducer]:
        if KafkaConsumer is None:
            raise ImportError("kafka-python is not installed")
        port = self.port
        return cast(
            "ContextManager[KafkaProducer]",
            closing(
                KafkaProducer(
                    bootstrap_servers=[f"{DOCKER_EXPOSE_HOST}:{port}"], security_protocol="PLAINTEXT", **kwargs
                )
            ),
        )

    def _consumer(self, **kwargs) -> ContextManager[Any]:
        port = self.port
        if KafkaConsumer is not None:
            return closing(
                KafkaConsumer(
                    bootstrap_servers=[f"{DOCKER_EXPOSE_HOST}:{port}"], security_protocol="PLAINTEXT", **kwargs
                )
            )
        else:
            return closing(
                ConfluentConsumer(
                    {
                        "bootstrap.servers": f"{DOCKER_EXPOSE_HOST}:{port}",
                        "security.protocol": "PLAINTEXT",
                        "group.id": "yb-0",
                        **kwargs,
                    }
                )
            )

    def _check_broker(self) -> None:
        if KafkaConsumer is not None:
            with self._consumer():
                pass
            return
        consumer = ConfluentConsumer(
            {
                "bootstrap.servers": f"{DOCKER_EXPOSE_HOST}:{self.port}",
                "security.protocol": "PLAINTEXT",
                "group.id": "yb-health",
            }
        )
        try:
            metadata = consumer.list_topics(timeout=5)
            if not metadata.brokers:
                raise ConnectionError("Kafka has no brokers yet")
        finally:
            consumer.close()

    def start(self, retry_spec: RetrySpec | None = None):
        super().start()
        retry_spec = retry_spec or RetrySpec(attempts=20)
        retry_spec.retry(self._check_broker, (KafkaException, KafkaError, ConnectionError, ValueError))
        return self

    async def astart(self, retry_spec: RetrySpec | None = None) -> None:
        super().start()
        retry_spec = retry_spec or RetrySpec(attempts=20)
        await retry_spec.aretry(self._check_broker, (KafkaException, KafkaError, ConnectionError, ValueError))

    def stop(self, signal="SIGKILL"):
        # difference in default signal
        super().stop(signal)
