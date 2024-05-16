from contextlib import closing
from time import sleep

from confluent_kafka import Consumer as ConfluentConsumer, Producer as ConfluentProducer
from pytest import fixture, mark
from yellowbox.containers import create_and_pull, removing
from yellowbox.networks import connect, temp_network
from yellowbox.utils import DOCKER_EXPOSE_HOST, docker_host_name

from yellowbox_kraft import KraftService


def get_consumer(kafka_service: KraftService):
    return closing(
        ConfluentConsumer(
            {
                "bootstrap.servers": f"{DOCKER_EXPOSE_HOST}:{kafka_service.port}",
                "security.protocol": "PLAINTEXT",
                "group.id": "yb-0",
            }
        )
    )


def get_producer(kafka_service: KraftService):
    return ConfluentProducer(
        {
            "bootstrap.servers": f"{DOCKER_EXPOSE_HOST}:{kafka_service.port}",
            "security.protocol": "PLAINTEXT",
        }
    )


@mark.parametrize("spinner", [True, False])
def test_make_kafka_kraft(docker_client, spinner):
    with KraftService.run(docker_client, spinner=spinner):
        pass


def test_kafka_kraft_works(docker_client):
    with KraftService.run(docker_client, spinner=False) as service, get_consumer(service) as consumer:
        producer = get_producer(service)
        producer.produce("test", b"hello world")
        producer.flush()

        sleep(1)

        def on_assign(consumer, partitions):
            for p in partitions:
                p.offset = -2
            consumer.assign(partitions)

        consumer.subscribe(["test"], on_assign=on_assign)
        msg = consumer.poll(10)
        assert msg is not None
        assert not msg.error()
        assert msg.value() == b"hello world"


@mark.asyncio
async def test_kafka_kraft_works_async(docker_client):
    async with KraftService.arun(docker_client) as service:
        with get_consumer(service) as consumer:
            producer = get_producer(service)
            producer.produce("test", b"hello world")
            producer.flush()

            sleep(1)

            def on_assign(consumer, partitions):
                for p in partitions:
                    p.offset = -2
                consumer.assign(partitions)

            consumer.subscribe(["test"], on_assign=on_assign)
            msg = consumer.poll(10)
            assert msg is not None
            assert not msg.error()
            assert msg.value() == b"hello world"


@fixture(scope="module")
def kafka_kraft_service(docker_client):
    with KraftService.run(docker_client, spinner=False) as service:
        yield service


def test_kafka_kraft_sibling_network(docker_client, kafka_kraft_service):
    with temp_network(docker_client) as network, connect(network, kafka_kraft_service) as alias:
        container = create_and_pull(
            docker_client,
            "confluentinc/cp-kafkacat:latest",
            f"kafkacat -b {alias[0]}:{kafka_kraft_service.container_port} -L",
        )
        with connect(network, container):
            container.start()
            with removing(container):
                return_status = container.wait()
            assert return_status["StatusCode"] == 0


def test_kafka_kraft_sibling(docker_client, kafka_kraft_service):
    container = create_and_pull(
        docker_client,
        "confluentinc/cp-kafkacat:latest",
        f"kafkacat -b {docker_host_name}:{kafka_kraft_service.port} -L",
    )
    container.start()
    with removing(container):
        return_status = container.wait()
    assert return_status["StatusCode"] == 0
