#!/usr/bin/env python3
"""
MIT License

Copyright (c) 2021 Ninjananas

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import sys
from typing import Union

try:
    import http.server
    import http.client
except ImportError:
    print(
        "Error while importing needed modules,"
        " maybe your version of Python is too old..."
    )
    sys.exit(1)

if sys.version_info.major != 3 or sys.version_info.minor < 8:
    print("This script runs only in Python 3.8+, exiting...")
    sys.exit(1)


__version__ = "1.0"

DEFAULT_PORT = 8080
DEFAULT_ADDRESS = "localhost"


def noop(*_, **__) -> None:
    return


info = print
debug = noop

_UNITS = ["B", "KiB", "MiB", "GiB", "TiB"]


def display_bytes(amount: Union[int, float]):
    i = 0
    while (x := amount / 1024.) > 1.1:
        i += 1
        amount = x
    return f"{round(amount, 2)} {_UNITS[i]}"


class ProxyRequestHandler(http.server.SimpleHTTPRequestHandler):
    __slots__ = []

    log_request = noop

    def do_X(self) -> None:
        debug(f"Received request {hash(self)}")
        if self.path[0] == "/":
            self.path = f"http://{self.headers['Host']}{self.path}"

        protocol, rest = self.path.split("://", 1)
        address, rest = rest.split("/", 1)
        self.path = "/" + rest
        if protocol == "http":
            conn = http.client.HTTPConnection(address)
        elif protocol == "https":
            conn = http.client.HTTPSConnection(address)
        else:
            message = f"Unknown protocol {protocol}"
            self.log_error(message)
            self.send_error(400, message)
            return
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length else None
        if body:
            body = self.spoof_download(body)
            self.headers['Content-Length'] = str(len(body.encode()))
        # downloaded=X is often in path
        self.path = self.spoof_download(self.path)
        self.filter_headers(self.headers)
        debug(f"Transfering request {hash(self)}")
        try:
            conn.request(method=self.command,
                         url=self.path,
                         headers=self.headers,
                         body=body)
            resp = conn.getresponse()
        except Exception as e:
            info(f"An error occurred while getting response: {e}")
            return
        debug(f"Received response {hash(self)}")
        self.send_response(resp.status)
        for k, v in resp.getheaders():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.copyfile(resp, self.wfile)
        except BrokenPipeError:
            pass
        debug(f"Transfered response {hash(self)}")

    do_HEAD = do_X
    do_GET = do_X
    do_POST = do_X
    do_PUT = do_X
    do_DELETE = do_X
    do_OPTIONS = do_X
    do_CONNECT = do_X

    @staticmethod
    def filter_headers(headers: dict) -> None:
        for k in ("connection", "keep-alive", "proxy-authenticate",
                  "upgrade", "proxy-authorization", "te", "trailers",
                  "transfer-encoding",):
            del headers[k]

    @staticmethod
    def spoof_download(body: str):
        parts = body.split("&")
        for i in range(len(parts)):
            part = parts[i]
            if part.startswith("downloaded="):
                parts[i] = "downloaded=0"
                try:
                    amount = int(part.split("=")[1])
                    if amount:
                        info(f"Spoofed {display_bytes(amount)}!")
                except Exception as e:
                    info(
                        f"An exception {e} occurred during download spoofing!")
                break
        return "&".join(parts)


class ProxyServer(http.server.ThreadingHTTPServer):
    __slots__ = []

    def __init__(self, addr: str, port: int):
        super().__init__((addr, port), ProxyRequestHandler)

    def serve_forever(self):
        info(
            f"Pytoprox v{__version__} serving at"
            f" {self.server_name}:{self.server_port}"
        )
        super().serve_forever()


DESCRIPTION = (
    "HTTP Proxy to spoof downloaded bytes to trackers.\n"
    "Launch me and tell your bittorrent client"
    " to use this proxy to contact trackers."
)

if __name__ == "__main__":
    import argparse
    argparser = argparse.ArgumentParser(description=DESCRIPTION)

    argparser.add_argument(
        "-p", "--port", type=int, default=DEFAULT_PORT,
        dest="port",
        help=f"Set the listening port of the proxy (default {DEFAULT_PORT})")
    argparser.add_argument(
        "-a", "--address", type=str, default=DEFAULT_ADDRESS,
        dest="address",
        help=f"Set the address of the proxy (default {DEFAULT_ADDRESS})")
    argparser.add_argument(
        "-q", "--quiet", action="store_true", default=False,
        dest="quiet",
        help="If set, pytoprox will try to not display anything")
    argparser.add_argument(
        "-v", "--verbose", action="store_true", default=False,
        dest="verbose",
        help="If set, pytoprox will display additional debug info")

    args = argparser.parse_args()

    info = noop if args.quiet else print
    debug = info if args.verbose else noop

    try:
        ProxyServer(args.address, args.port).serve_forever()
    except KeyboardInterrupt:
        pass
