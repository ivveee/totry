"""Pytest test for producer


It creates a fake localhost website, kafka producer and consumer
Then it connects to remote Kafka server (it uses the same credentials as the subsystem)
sends one request and receives it.
The timeout is 10 seconds.
TODO:
TODO:
"""

import json
import logging

from aiohttp import web
from aiokafka import AIOKafkaConsumer
from aiokafka.helpers import create_ssl_context
from async_timeout import timeout
from yarl import URL

from producer import run_in_loop, set_up_producer
from website_checker import WebsiteChecker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("asyncio").level = logging.WARNING
logging.getLogger("aiokafka").level = logging.WARNING

PORT = 8080
LOCALHOST = f'http://127.0.0.1:{PORT}'


async def create_app(f):
    app = web.Application()
    app.router.add_route("GET", "/", f)
    return app


async def test_loop(aiohttp_server):
    try:
        async def hello(request):
            return web.Response(body=b"Hello")
        server = await aiohttp_server(await create_app(hello), port=PORT)
        async with timeout(20):
            with open('../resources/kafka_certificates.json') as json_file:
                data = json.load(json_file)
            consumer = AIOKafkaConsumer("website_check",
                                        auto_offset_reset='latest',
                                        enable_auto_commit=False,
                                        bootstrap_servers=data.get('service_uri'),
                                        security_protocol='SSL',
                                        ssl_context=create_ssl_context(
                                            cafile=data.get('ca_path'),
                                            certfile=data.get('cert_path'),
                                            keyfile=data.get('key_path')
                                        ))
            await consumer.start()

            producer = await set_up_producer('../resources/kafka_certificates.json')
            await producer.start()
            checker = WebsiteChecker()
            await checker.create(URL(LOCALHOST), None)
            await run_in_loop(checker, producer, 10, 1)
            async for msg in consumer:
                logger.info(
                    f'Consumed: {msg.topic}, {msg.partition}, {msg.offset},{msg.key}, {msg.value}, {msg.timestamp}')
                package = msg.value.decode("utf-8").split(",", 4)
                assert package[1] == LOCALHOST
                assert package[2] == '200'
                await consumer.stop()
    finally:
        await checker.destroy()
        await producer.stop()
        await consumer.stop()

