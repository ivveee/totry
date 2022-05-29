import asyncio
import re
import ssl
from re import Pattern
from types import SimpleNamespace

import aiohttp
from aiohttp import TraceRequestEndParams, TraceConfig, ClientSession, ClientTimeout, ClientConnectorCertificateError
from shared.website_check_result import WebsiteCheckResult
from yarl import URL


class WebsiteChecker:
    """A wrapper for AIOHTTP ClientSession that performs async website checks.

    There are some limitations:
    - only checks using GET requests are implemented
    - the size of a body to run regex on is limited to 500 kB
    - the total timeout for site reply is limited to 5 second
    - currently tested for HTTP only
    - GET checks times out in 5 seconds

    TODO: implement POST (and other?) request
    TODO: standardize error messages
    TODO: handle regex on larger bodies
    TODO: handle TLS better
    """

    def __init__(self):
        self._session = None
        self._url: URL = None
        self._initialized: bool = False
        self._regex: Pattern | None = None

    @property
    def url(self):
        return self._url

    @property
    def initialized(self):
        return self._initialized

    async def create(self, url: URL, regex: Pattern = None):
        if self._initialized:
            raise Exception("Website checker has already been created")
        self._url: URL = url
        self._regex: Pattern = regex
        trace_config = TraceConfig()

        async def on_request_start(trace_session, trace_config_ctx: SimpleNamespace, params):
            trace_config_ctx.start = asyncio.get_event_loop().time()

        async def on_request_end(trace_session, trace_config_ctx: SimpleNamespace, params: TraceRequestEndParams):
            elapsed = asyncio.get_event_loop().time() - trace_config_ctx.start
            trace_config_ctx.time = elapsed
            trace_config_ctx.trace_request_ctx.elapsed = elapsed

        trace_config.on_request_start.append(on_request_start)
        trace_config.on_request_end.append(on_request_end)
        self._session = ClientSession(trace_configs=[trace_config], timeout=ClientTimeout(total=5))
        self._initialized = True
        return self

    async def destroy(self):
        if not self._initialized:
            raise Exception("Website checker has never been initialized")
        await self._session.close()

    async def get_website_status(self) -> WebsiteCheckResult:
        if not self._initialized:
            raise Exception("Website checker has never been initialized")
        try:
            request_context = SimpleNamespace()
            async with self._session.get(self._url, trace_request_ctx=request_context) as reply:
                if self._regex:
                    content = await reply.content.read(500000)
                    content_decoded = content.decode("utf-8", errors='ignore')
                    regex_result = bool(self._regex.search(content_decoded))
                else:
                    regex_result = None
                result = WebsiteCheckResult(url=self._url,
                                            result=str(reply.status),
                                            response_time=request_context.elapsed,
                                            regex_result=regex_result)
            return result
        except asyncio.TimeoutError as err:
            return WebsiteCheckResult(url=self._url,
                                      result='Timeout Error',
                                      response_time=None,
                                      regex_result=None)
        except (aiohttp.ClientConnectorError, ssl.SSLCertVerificationError, ClientConnectorCertificateError) as err:
            result_no_commas = re.sub(r"[!@#$%^&*()\[\]{};:,./\\<>?|`~\-=_+\"\']", "-", str(err))
            return WebsiteCheckResult(url=self._url,
                                      result=result_no_commas,
                                      response_time=None,
                                      regex_result=None)
        except aiohttp.ClientError as err:
            return WebsiteCheckResult(url=self._url,
                                      result="Connection Error",
                                      response_time=None,
                                      regex_result=None)





