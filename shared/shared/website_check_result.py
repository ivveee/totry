import time

from yarl import URL


class WebsiteCheckResult:
    """A read-only data structure to store the results of checks.
    """
    precision = 6

    def __init__(self, url: URL | None = None, result: str | None = None, response_time: float | None = None,
                 regex_result: bool | None = None, package_str: str = None):
        if package_str:
            vals = package_str.split(",", 4)
            self._timestamp: float = float(vals[0])
            self._url: URL = URL(vals[1])
            self._result: str = vals[2]

            self._response_time: float = float(vals[3]) if vals[3] else None
            self._regex_result: float = bool(vals[4]) if vals[4] else None

            if url is not None or result is not None:
                raise TypeError("Result object may be constructed either by package or by URL, but both are provided")
            return
        if url is None:
            raise TypeError(" URL not provided")
        if result is None:
            raise TypeError("Result not provided")

        self._timestamp: float = time.time()
        self._url: URL = url
        self._result: str = result
        self._response_time: float | None = response_time
        self._regex_result: bool | None = regex_result

    @property
    def timestamp(self) -> float:
        return self._timestamp

    @property
    def result(self) -> str:
        return self._result

    @property
    def url(self) -> URL:
        return self._url

    @property
    def response_time(self):
        return self._response_time

    @property
    def regex_result(self):
        return self._regex_result

    def __repr__(self):
        return f'[{self.to_package()}]'

    def to_package(self) -> str:
        response_time_string = ""
        if self._response_time:
            response_time_string = f"{self._response_time:.{self.precision}f}"
        return f"{self._timestamp:.{self.precision}f},{self._url}," \
               f"{self._result},{response_time_string},{self._regex_result  or ''}"

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._timestamp == other._timestamp and \
                   self._result == other._result and \
                   self._url == other._url and \
                   self._response_time == other._response_time and \
                   self._regex_result == other._regex_result
        else:
            return False
