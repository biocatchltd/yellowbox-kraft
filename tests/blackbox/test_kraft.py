from pytest import fail, fixture, mark
from yellowbox.containers import create_and_pull, removing
from yellowbox.networks import connect, temp_network
from yellowbox.utils import docker_host_name

from yellowbox_kraft import KraftService


@mark.parametrize("spinner", [True, False])
def test_make_kafka_kraft(docker_client, spinner):
    with KraftService.run(docker_client, spinner=spinner):
        pass


def test_kafka_kraft_works(docker_client):
    with KraftService.run(
        docker_client, spinner=False
    ) as service, service.consumer() as consumer, service.producer() as producer:
        producer.send("test", b"hello world")

        consumer.subscribe("test")
        consumer.topics()
        consumer.seek_to_beginning()

        for msg in consumer:
            assert msg.value == b"hello world"
            break
        else:
            fail("expected to find a message")


@mark.asyncio
async def test_kafka_kraft_works_async(docker_client):
    async with KraftService.arun(docker_client) as service:
        with service.consumer() as consumer, service.producer() as producer:
            producer.send("test", b"hello world")

            consumer.subscribe("test")
            consumer.topics()
            consumer.seek_to_beginning()

            for msg in consumer:
                assert msg.value == b"hello world"
                break
            else:
                fail("expected to find a message")


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
