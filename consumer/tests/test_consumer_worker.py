"""Pytest test for receiver


It creates a fake kafka producer and consumer
Then it connects to remote Kafka server (it uses the same credentials as the subsystem)
sends one request and receives it.
The timeout is 30 seconds.
TODO: Restructure worker
TODO:
"""
import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.helpers import create_ssl_context
from async_timeout import timeout
from shared.website_check_result import WebsiteCheckResult
from yarl import URL

from consumer_worker import ConsumerWorker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger('aiokafka').level = logging.INFO


async def test_consumer():
    async with timeout(30):

        with open('../resources/kafka_certificates.json') as json_file:
            data = json.load(json_file)

        consumer = AIOKafkaConsumer(
                                "website_check",
                                     auto_offset_reset='latest',
                                    enable_auto_commit=False,
                                    bootstrap_servers=data.get('service_uri'),
                                    security_protocol='SSL',
                                    ssl_context=create_ssl_context(
                                        cafile=data.get('ca_path'),
                                        certfile=data.get('cert_path'),
                                        keyfile=data.get('key_path')
                                    ))
        producer = AIOKafkaProducer(
            bootstrap_servers=data.get('service_uri'),
            security_protocol='SSL', ssl_context=create_ssl_context(
                cafile=data.get('ca_path'),
                certfile=data.get('cert_path'),
                keyfile=data.get('key_path')
            ))
        await producer.start()
        check_result = WebsiteCheckResult(URL("http://test.re"), "200")
        worker = ConsumerWorker()

        async def on_ready():
            await asyncio.sleep(2)  # Why ?
            await producer.send("website_check", check_result.to_package().encode('utf-8'))
            logger.info(f"SENT {check_result}")

        async def on_received(status):
            logger.info(f"RECEIVED {status}")
            assert check_result.result == status.result
            assert check_result.url == status.url
            await worker.destroy()
            await producer.stop()
            await producer.stop()

        async def empty(arg):
            pass
        worker.send_to_db = empty  # Super unsafe  TODO: Think of a more Pythonic way to make this
        await worker.run(None, consumer, on_ready, on_received)
