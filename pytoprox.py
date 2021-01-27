import http.server
import http.client


class ProxyRequestHandler(http.server.SimpleHTTPRequestHandler):
    __slots__ = []

    def do_X(self):
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
            message = f"unknown protocol {protocol}"
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
        try:
            conn.request(method = self.command,
                         url = self.path,
                         headers = self.headers,
                         body = body)
            resp = conn.getresponse()
        except Exception as e:
            print(f" An error {e} occurred while getting response")
            return
        self.send_response(resp.status)
        for k, v in resp.getheaders():
            self.send_header(k, v)
        self.end_headers()
        self.copyfile(resp, self.wfile)

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
                print(f"SPOOFED {part}")
                break
        return "&".join(parts)

class ProxyServer(http.server.ThreadingHTTPServer):
    __slots__ = []

    def __init__(self, addr: str, port: int):
        super().__init__((addr, port), ProxyRequestHandler)

if __name__ == "__main__":
    try:
        ProxyServer("localhost", 8080).serve_forever()
    except KeyboardInterrupt:
        pass
