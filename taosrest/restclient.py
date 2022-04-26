from datetime import datetime
from urllib.request import urlopen, Request
from .errors import ConnectionError, ExecutionError
import json
import socket


class RestClient:
    """
     A wrapper for TDengine RESTful API.
    """

    TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"
    """default time format of /rest/sqlutc api"""

    def __init__(self, host: str, port: int, user: str, password: str, timeout: int = None):
        """
        Create a RestClient object.

        Parameters
        -----------
        - host : host to connect
        - port : port to connect
        - user : username used to log in
        - password : password used to log in
        - timeout : the optional timeout parameter specifies a timeout in seconds for blocking operations
        """
        self.login_url = f"http://{host}:{port}/rest/login/{user}/{password}"
        self.sql_utc_url = f"http://{host}:{port}/rest/sqlutc"
        self.timeout = timeout if timeout is not None else socket._GLOBAL_DEFAULT_TIMEOUT
        self.token = self.get_token()
        self.headers = {
            "Authorization": "Taosd " + self.token
        }

    def get_token(self) -> str:
        """
        Get authorization token.
        """
        response = urlopen(self.login_url, timeout=self.timeout)
        resp = json.load(response)
        if resp["code"] != 0:
            raise ConnectionError(resp["desc"], resp["code"])
        return resp["desc"]

    def sql(self, q: str) -> dict:
        """
        Execute sql and return the json content. This method sent request to API: `/rest/sqlutc` although it's name is `sql()`.

        Parameters
        -----------
        q : SQL statement to execute. Can't be USE statement since RESTful api is stateless.

        Example of Returns
        -------
        ```json
        {
            "status": "succ",
            "head": ["ts","current", …],
            "column_meta": [["ts",9,8],["current",6,4], …],
            "data": [
                [datetime.datetime(2022, 4, 20, 14, 16, 2, 522000, tzinfo=datetime.timezone(datetime.timedelta(seconds=28800))), 10.3, …],
                [datetime.datetime(2022, 4, 20, 14, 16, 12, 522000, tzinfo=datetime.timezone(datetime.timedelta(seconds=28800))), 12.6, …]
            ],
            "rows": 2
        }
        ```

        Column Type
        ----------------
        - 1：BOOL
        - 2：TINYINT
        - 3：SMALLINT
        - 4：INT
        - 5：BIGINT
        - 6：FLOAT
        - 7：DOUBLE
        - 8：BINARY
        - 9：TIMESTAMP
        - 10：NCHAR

        Raises
        ------
        ExecutionError if the return status is "error".
        """

        data = q.encode("utf8")
        request = Request(self.sql_utc_url, data, self.headers)
        response = urlopen(request, timeout=self.timeout)
        resp = json.load(response)
        if resp["status"] == "error":
            raise ExecutionError(resp["desc"], resp["code"])
        self._convert_time(resp)
        return resp

    def _convert_time(self, resp: dict):
        """
        Convert timestamp in string format(RFC 3339) to python's datetime object with time zone info.
        """
        meta = resp["column_meta"]
        data = resp["data"]
        for i in range(len(meta)):
            if meta[i][1] == 9:
                for row in data:
                    row[i] = datetime.strptime(row[i], RestClient.TIME_FORMAT)