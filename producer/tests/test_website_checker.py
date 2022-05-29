"""Pytest tests for WebsiteChecker.

The tests of how a checker reacts to expected and unexpected website behaviour

TODO: make more tests that handle broken headers, etc.
TODO:
"""

import asyncio
import logging
import re

import aiohttp
import pytest
from aiohttp import web
from shared.website_check_result import WebsiteCheckResult
from yarl import URL

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

@pytest.fixture
async def checker(request) -> WebsiteCheckResult:
    url, regex = request.param
    checker = WebsiteChecker()
    await checker.create(URL(url), regex)
    status = await checker.get_website_status()
    logger.debug("RETURNED STATUS:" + status.to_package())
    yield status
    await checker.destroy()


@pytest.fixture
async def hello_server(aiohttp_server):
    async def hello(request):
        return web.Response(body=b"Hello")

    return await aiohttp_server(await create_app(hello), port=PORT)


@pytest.fixture
async def slow_server(aiohttp_server, request):
    async def slow(request1):
        await asyncio.sleep(request.param[0])
        return web.Response(body=b"Hello")

    return await aiohttp_server(await create_app(slow), port=PORT)


@pytest.fixture
async def erratic_server(aiohttp_raw_server, request):
    async def raise_ex(request1):
        raise aiohttp.web.HTTPInternalServerError()

    return await aiohttp_raw_server(handler=raise_ex, port=PORT)


"""
This tests whether the CheckerResult is formed correctly if server responds with status 200
"""


@pytest.mark.parametrize('checker', [[LOCALHOST, re.compile("H.")]], indirect=True)
async def test_checker_get_ok(hello_server, checker):
    assert checker.result == '200'
    assert str(checker.url) == LOCALHOST
    assert checker._regex_result


@pytest.mark.parametrize('checker', [[LOCALHOST, re.compile("O.")]], indirect=True)
async def test_checker_get_ok_fail_regex(hello_server, checker):
    assert checker.result == '200'
    assert str(checker.url) == LOCALHOST
    assert not checker._regex_result


@pytest.mark.parametrize('checker', [[LOCALHOST, None]], indirect=True)
async def test_checker_get_ok_no_regex(hello_server, checker):
    assert checker.result == '200'
    assert str(checker.url) == LOCALHOST
    assert checker._regex_result is None


"""
This tests how checker deals with non-standard server behaviour
"""


@pytest.mark.parametrize('checker', [[LOCALHOST, re.compile("H.")]], indirect=True)
async def test_checker_get_no_answer(checker):
    assert checker.result  # there is an error message but it is unpredictable
    assert str(checker.url) == LOCALHOST
    assert checker.regex_result is None


@pytest.mark.parametrize('checker, slow_server', [([LOCALHOST, re.compile("H.")], [10])], indirect=True)
async def test_checker_get_answer_after_timeout(checker, slow_server):
    assert checker.result   # there is an error message but it is unpredictable
    assert str(checker.url) == LOCALHOST
    assert checker.regex_result is None


DELAY = 3


@pytest.mark.parametrize('checker, slow_server', [([LOCALHOST, re.compile("H.")], [DELAY])], indirect=True)
async def test_checker_get_answer_after_delay(slow_server, checker):
    assert checker.result == '200'
    assert str(checker.url) == LOCALHOST
    assert checker.response_time >= DELAY
    assert checker.regex_result


"""
This tests how checker deals with server errors
"""


@pytest.mark.parametrize('checker', [[LOCALHOST, re.compile("H.")]], indirect=True)
async def test_checker_get_error_answer(erratic_server, checker):
    assert checker.result == str(aiohttp.web.HTTPInternalServerError.status_code)
    assert str(checker.url) == LOCALHOST
    assert checker.regex_result is False


"""
This tests how checker connects to outside world 
TODO: should check whether outside world is available
"""
sites = "https://httpbin.org/"


@pytest.mark.parametrize('checker', [[sites, re.compile("Response Service")]], indirect=True)
async def test_website_checker_single(checker):
    assert checker.result == '200'
    assert str(checker.url) == sites
    assert checker._regex_result
