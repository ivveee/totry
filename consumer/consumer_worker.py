import asyncio
import logging

from aiokafka import AIOKafkaConsumer
from aiopg import Pool
from shared.website_check_result import WebsiteCheckResult

logger = logging.getLogger('verbose')
logger_fast = logging.getLogger('fast')


class ConsumerWorker:
    """Asynchronously Consumes data from a single async Kafka consumer and writes it to a connection pool.


    TODO: implement logging and inner processes of each task
    TODO: implement batch multiline insert (up to 1000 lines)
    """

    def __init__(self):
        self._pool = None
        self._task = None
        self._consumer = None
        self._connection = None

    def create_task(self, pool: Pool, consumer: AIOKafkaConsumer) -> asyncio.Task:
        if self._task:
            return self._task
        else:
            self._task = asyncio.create_task(self.run(pool, consumer))
            return self._task

    async def run(self, pool: Pool, consumer: AIOKafkaConsumer):
        if self._consumer:
            raise Exception("Worker is already running")
        self._pool = pool
        self._consumer = consumer
        await self._consumer.start()

        try:
            async for msg in self._consumer:
                logger.debug(
                    f'Consumed: {msg.topic}, {msg.partition}, {msg.offset}, {msg.key}, {msg.value}, {msg.timestamp}')
                res = WebsiteCheckResult(package_str=msg.value.decode('utf-8'))
                logger_fast.info(f'[{res.url.host}]')
                with (await pool.cursor()) as cur:
                    response_time_formatted = f"'{res.response_time}'" if res.response_time is not None else "NULL"
                    regex_result_formatted = f"'{res.regex_result}'" if res.regex_result is not None else "NULL"
                    await cur.execute(f"INSERT INTO results_log VALUES "
                                      f"('{res.timestamp}', '{res.url}', '{res.result}',"
                                      f" {response_time_formatted}, {regex_result_formatted})")
        finally:
            await self.destroy()

    async def destroy(self):
        await self._consumer.stop()
        await self._task.cancel()
