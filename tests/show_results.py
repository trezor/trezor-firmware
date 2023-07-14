#!/usr/bin/env python3

import http.server
import json
import multiprocessing
import os
import posixpath
import sys
import time
import webbrowser
from pathlib import Path
from urllib.parse import unquote

import click

from ui_tests.common import SCREENS_DIR, TestResult, write_fixtures_complete
from ui_tests.reporting import testreport  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

sys.path.append(str(ROOT / "tests"))


class NoCacheRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        return super().end_headers()

    def log_message(self, format, *args) -> None:
        pass

    def translate_path(self, path: str) -> str:
        # XXX
        # Copy-pasted from Python 3.8 BaseHTTPRequestHandler so that we can inject
        # the `directory` parameter.
        # Otherwise, to keep compatible with 3.6, we'd need to mess with CWD. Which is
        # unstable when we expect it to be erased and recreated under us.
        path = path.split("?", 1)[0]
        path = path.split("#", 1)[0]
        # Don't forget explicit trailing slash when normalizing. Issue17324
        trailing_slash = path.rstrip().endswith("/")
        try:
            path = unquote(path, errors="surrogatepass")
        except UnicodeDecodeError:
            path = unquote(path)
        path = posixpath.normpath(path)
        words = path.split("/")
        words = filter(None, words)
        path = str(testreport.TESTREPORT_PATH)  # XXX this is the only modified line
        for word in words:
            if os.path.dirname(word) or word in (os.curdir, os.pardir):
                # Ignore components that are not a simple file/directory name
                continue
            path = os.path.join(path, word)
        if trailing_slash:
            path += "/"
        return path

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            testreport.index()

        return super().do_GET()

    def do_POST(self) -> None:
        if self.path == "/fixtures.json":

            length = int(self.headers.get("content-length"))
            field_data = self.rfile.read(length)
            data = json.loads(field_data)

            test_name = data.get("test")
            test_hash = data.get("hash")

            if test_name is not None and test_hash is not None:
                test_path = SCREENS_DIR / test_name
                result = TestResult.load(test_path)
                assert result.actual_hash == test_hash
                write_fixtures_complete([result])

            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()


def launch_http_server(port: int) -> None:
    http.server.test(HandlerClass=NoCacheRequestHandler, bind="localhost", port=port)  # type: ignore [test is defined]


@click.command()
@click.option("-p", "--port", type=int, default=8000)
def main(port: int):
    httpd = multiprocessing.Process(target=launch_http_server, args=(port,))
    httpd.start()
    time.sleep(0.5)
    webbrowser.open(f"http://localhost:{port}/")
    httpd.join()


if __name__ == "__main__":
    main()
