"""Entry point to the Consumer package of website monitoring system.


It sets up a database connection pool and creates several (default - 5) workers in a group "async_tasks"
that asynchronously consume data from Kafka topic "website_check"
and writes it to a "results_log" table of PostgreSQL database "results_log"

TODO: add schema checks for jsons
TODO: implement multiprocessing
TODO: implement table dispatching
"""

import asyncio
import json
import logging.config
import sys

import aiopg
from aiokafka import AIOKafkaConsumer
from aiokafka.helpers import create_ssl_context
from aiopg import Pool

from consumer_worker import ConsumerWorker

logging.config.fileConfig('logging.ini')
logger = logging.getLogger('verbose')
logger_fast = logging.getLogger('fast')
logger_fast.handlers[0].terminator = ""

logging.getLogger("asyncio").level = logging.INFO
logging.getLogger("aiokafka").level = logging.WARNING

if sys.platform == 'win32':
    # Set the policy to prevent "Event loop is closed" error on Windows - https://github.com/encode/httpx/issues/914
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def set_up_db(path: str) -> Pool:
    with open(path) as json_file:
        data = json.load(json_file)
    pool = aiopg.create_pool(user=data['user'],
                             database='check_results',
                             host=data['host'],
                             password=data['password'],
                             port=data['port'])
    logger.info(f'Database data loaded')
    return await pool


async def set_up_consumer(certificates_path: str) -> AIOKafkaConsumer:
    with open(certificates_path) as json_file:
        data = json.load(json_file)
    consumer = AIOKafkaConsumer("website_check",
                                group_id="async_tasks",
                                auto_offset_reset='latest',
                                enable_auto_commit=False,
                                bootstrap_servers=data.get('service_uri'),
                                security_protocol='SSL',
                                ssl_context=create_ssl_context(
                                    cafile=data.get('ca_path'),
                                    certfile=data.get('cert_path'),
                                    keyfile=data.get('key_path')
                                ))
    logger.info(f'Kafka consumer data loaded')
    return consumer


async def entry_point():
    engine: Pool = await set_up_db('../resources/db_access_data.json')
    workers = []
    tasks = []
    for i in range(0, 5):
        worker = ConsumerWorker()
        workers.append(worker)
        consumer = await set_up_consumer('../resources/kafka_certificates.json')
        task = worker.create_task(engine, consumer)
        tasks.append(task)
    try:
        await asyncio.gather(*tasks, return_exceptions=False)
    finally:
        logger.info(f'Wrapping up consumer. Please wait')
        engine.close()
        await engine.wait_closed()
        [tasks_to_del.cancel() for tasks_to_del in tasks]


if __name__ == '__main__':
    asyncio.run(entry_point())
