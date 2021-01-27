import http.server
import http.client

__version__ = "1.0"

DEFAULT_PORT=8080
DEFAULT_ADDRESS="localhost"

pprint = print
cprint = lambda *x, **y: None

_units = ["o", "Kio", "Mio", "Gio", "Tio"]
def display_bytes(amount):
    i = 0
    while (x := amount / 1024.) > 1.1:
        i += 1
        amount = x
    return f"{round(amount, 2)} {_units[i]}"


class ProxyRequestHandler(http.server.SimpleHTTPRequestHandler):
    __slots__ = []

    log_request = lambda *x, **y: None

    def do_X(self):
        vprint(f"Received request {hash(self)}")
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
        self.path = self.spoof_download(self.path)
        self.filter_headers(self.headers)
        vprint(f"Transfering request {hash(self)}")
        try:
            conn.request(method = self.command,
                         url = self.path,
                         headers = self.headers,
                         body = body)
            resp = conn.getresponse()
        except Exception as e:
            pprint(f"An error {e} occurred while getting response")
            return
        vprint(f"Received response {hash(self)}")
        self.send_response(resp.status)
        for k, v in resp.getheaders():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.copyfile(resp, self.wfile)
        except BrokenPipeError:
            pass
        vprint(f"Transfered response {hash(self)}")

    do_HEAD = do_X
    do_GET = do_X
    do_POST = do_X
    do_PUT = do_X
    do_DELETE = do_X
    do_OPTIONS = do_X

    @staticmethod
    def filter_headers(headers):
        for k in ("connection", "keep-alive", "proxy-authenticate", "upgrade",
                  "proxy-authorization", "te", "trailers", "transfer-encoding",):
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
                        pprint(f"Spoofed {display_bytes(amount)}!")
                except:
                    pass
                break
        return "&".join(parts)

class ProxyServer(http.server.ThreadingHTTPServer):
    __slots__ = []

    def __init__(self, addr: str, port: int):
        super().__init__((addr, port), ProxyRequestHandler)

    def serve_forever(self):
        pprint(f"Pytoprox v{__version__} serving at {self.server_name}:{self.server_port}")
        super().serve_forever()

if __name__ == "__main__":
    import argparse
    argparser = argparse.ArgumentParser()

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
        help=f"If set, pytoprox will try to not display anything (default False)")
    argparser.add_argument(
        "-v", "--verbose", action="store_true", default=False,
        dest="verbose",
        help=f"If set, pytoprox will display additional debug info (default False)")

    args = argparser.parse_args()

    pprint = (lambda *x, **y: None) if args.quiet else print
    vprint = pprint if args.verbose else (lambda *x, **y: None)

    try:
        ProxyServer(args.address, args.port).serve_forever()
    except KeyboardInterrupt:
        pass
