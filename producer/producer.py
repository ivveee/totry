"""Entry point to the Producer package of Isalive website monitoring system

It loads the list of websites to be checked and Kafka certificates,
then it creates AIOKafkaProducer and multiple WebsiteChecker objects.
Each WebsiteChecker asynchronously creates GET requests in an infinite (by default) loop.
The result of each check is sent to Kafka topic "website_check".

TODO: extract and create a Dispatcher class that runs and manages coroutines
TODO: add schema checks for jsons
TODO: manage debugger code for production
"""
import asyncio
import json
import logging
import logging.config
import re
from typing import List

from aiokafka import AIOKafkaProducer
from aiokafka.helpers import create_ssl_context
from yarl import URL

from website_checker import WebsiteChecker

#logging.basicConfig(level=logging.INFO)
logging.config.fileConfig('logging.ini')
logger = logging.getLogger('verbose')
logger_fast = logging.getLogger('fast')
logger_fast.handlers[0].terminator = ""

logging.getLogger('asyncio').level = logging.WARNING
logging.getLogger('aiohttp').level = logging.WARNING
logging.getLogger('aiokafka').level = logging.WARNING


async def set_up_producer(path: str) -> AIOKafkaProducer:
    with open(path) as json_file:
        data = json.load(json_file)
    producer = AIOKafkaProducer(
            bootstrap_servers=data.get('service_uri'),
            security_protocol='SSL', ssl_context=create_ssl_context(
                cafile=data.get('ca_path'),
                certfile=data.get('cert_path'),
                keyfile=data.get('key_path')
            ))
    logger.info('Kafka certificates for producer loaded')
    return producer


async def set_up_website_data(path: str) -> [List, int, float]:
    with open(path) as json_file:
        initializers = json.load(json_file)
    website_list = []
    for item in initializers.get('websites'):
        in_url = URL(item[0])
        if not in_url.raw_host:
            logging.warning(f'URL is not valid:{in_url}')
            continue
        in_regex = None
        try:
            regex_string = item[1]
            in_regex = re.compile(regex_string)
        except IndexError:
            # Regex is optional
            pass
        website_list.append(dict(url=in_url, regex=in_regex))
    interval = float(initializers.get('interval_between_requests'))
    logger.info('Website data loaded')
    logger.debug(f'{website_list}')

    return website_list, interval


async def run_in_loop(checker: WebsiteChecker, producer: AIOKafkaProducer,
                      interval: float, loops: float = float('inf')):
    while loops > 0:
        status = await checker.get_website_status()
        logger.debug(f'Checker {checker.url} : {status}')
        logger_fast.info(f'[{checker.url.host}:{status.result[0:3]}]')
        await producer.send("website_check", status.to_package().encode('utf-8'))
        await asyncio.sleep(interval)
        loops -= 1


async def entry_point():
    producer = await set_up_producer('../resources/kafka_certificates.json')
    await producer.start()

    website_list, interval = await set_up_website_data('../resources/websites.json')
    tasks = []
    checkers = []
    for item in website_list:
        checker = await WebsiteChecker().create(item['url'], item['regex'])
        task = asyncio.create_task(run_in_loop(checker, producer, interval))
        tasks.append(task)
        checkers.append(checker)
    try:
        await asyncio.gather(*tasks, return_exceptions=False)
    finally:
        await producer.stop()
        [await checker_to_del.destroy() for checker_to_del in checkers]
        [task_to_del.cancel() for task_to_del in tasks]

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(entry_point())
