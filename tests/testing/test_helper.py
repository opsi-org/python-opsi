# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import json
import os
import ssl
import struct
import time
from base64 import b64decode
from email.message import Message
from email.utils import formatdate
from io import BytesIO, StringIO
from pathlib import Path
from random import randbytes
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock, patch

import pytest
import requests
import websocket

from opsi.compression import compress
from opsi.logging import LOG_INFO, get_logger
from opsi.opsi.service.server import OpsiConfig
from opsi.serialization import msgpack_encode
from opsi.testing.helper import HTTPTestServerRequestHandler, environment, http_test_server, log_stream, memory_usage_monitor, opsi_config
from opsi.testing.helper._http import HTTPTestServer, WebSocketError


def test_environment() -> None:
	assert "TEST_VAR1" not in os.environ
	with environment({"TEST_VAR1": "VAL1"}):
		assert os.environ.get("TEST_VAR1") == "VAL1"
		with environment({"TEST_VAR1": "VAL2"}):
			assert os.environ.get("TEST_VAR1") == "VAL2"
		assert os.environ.get("TEST_VAR1") == "VAL1"
	assert "TEST_VAR1" not in os.environ


def test_memory_usage_monitor() -> None:
	with memory_usage_monitor(interval=0.5) as monitor:
		data = b"x" * 25_000_000
		time.sleep(1)
		del data
		time.sleep(1)

	file = StringIO()
	monitor.print_stats(file)
	data = file.getvalue()
	assert "Memory usage statistics:" in data
	assert "Max increase RSS" in data
	assert monitor.max_increase_rss > 20_000_000
	assert monitor.max_increase_rss < 30_000_000


def test_opsi_config() -> None:
	with opsi_config({"host.id": "host.opsi-test", "service.url": "https://opsi.server:443"}):
		conf = OpsiConfig()
		assert conf.get("host", "id") == "host.opsi-test"
		assert conf.get("service", "url") == "https://opsi.server:443"


def test_log_stream() -> None:
	logger = get_logger()
	with log_stream(LOG_INFO, format="%(levelname)s: %(message)s") as stream:
		logger.info("Test log message INFO")
		logger.notice("Test log message NOTICE")
		logger.debug("Test log message DEBUG")

	data = stream.getvalue()
	assert "Test log message INFO" in data
	assert "Test log message NOTICE" in data
	assert "Test log message DEBUG" not in data


def test_test_http_server_log_file(tmp_path: Path) -> None:
	log_file = tmp_path / "server.log"
	with http_test_server(log_file=log_file) as server:
		res = requests.get(f"http://localhost:{server.port}/dir/file", timeout=10)
		assert res.status_code == 200
	request = json.loads(log_file.read_text(encoding="utf-8").strip())
	assert request["method"] == "GET"
	assert request["client_address"][0] == "127.0.0.1"
	assert request["path"] == "/dir/file"
	assert request["headers"]["Host"].startswith("localhost:")
	log_file.unlink()

	with http_test_server(log_file=None) as server:
		res = requests.get(f"http://localhost:{server.port}/dir/file", timeout=10)
		assert res.status_code == 200

	assert not log_file.exists()


def test_test_http_server_headers() -> None:
	with http_test_server(response_headers={"Server": "test/123", "X-Server-Adress": "{server_address}", "X-Host": "{host}"}) as server:
		res = requests.get(f"http://localhost:{server.port}", timeout=10)
		assert res.status_code == 200
		assert res.headers["Server"] == "test/123"
		assert res.headers["X-Server-Adress"].endswith(f":{server.port}")
		assert res.headers["X-Host"].endswith(f":{server.port}")


def test_test_http_server_response_delay() -> None:
	with http_test_server(response_delay=2) as server:
		start = time.monotonic()
		res = requests.get(f"http://localhost:{server.port}", timeout=10)
		assert res.status_code == 200
		delay = round(time.monotonic() - start)
		assert 6 >= delay >= 2


def test_test_http_server_post() -> None:
	with http_test_server() as server:
		rpc = {"id": 1, "method": "test", "parms": [1, 2]}
		res = requests.post(f"http://localhost:{server.port}", json=rpc, timeout=10)
		assert res.status_code == 200


def test_test_http_server_serve_files(tmp_path: Path) -> None:
	test_dir = tmp_path / "dir1"
	test_dir.mkdir()
	test_file1 = test_dir / "file1"
	test_file1.touch()
	test_file2 = test_dir / "file2"
	test_file2.write_text("test2", encoding="utf-8", newline="")
	with http_test_server(serve_directory=tmp_path) as server:
		res = requests.get(f"http://127.0.0.1:{server.port}/dir1", timeout=10)
		assert res.status_code == 200
		assert "Directory listing for /dir1" in res.text

		res = requests.get(f"http://127.0.0.1:{server.port}/dir1/file2", timeout=10)
		assert res.status_code == 200
		assert res.text == "test2"

		res = requests.get(f"http://127.0.0.1:{server.port}/dir1/file2", headers={"Range": "bytes=3-4"}, timeout=10)
		assert res.status_code == 206
		assert res.text == "t2"

		res = requests.get(f"http://127.0.0.1:{server.port}/dir1/file2", headers={"Range": "bytes=3-1024"}, timeout=10)
		assert res.status_code == 206
		assert res.text == "t2"

		(test_dir / "index.html").write_text("index", encoding="utf-8", newline="")

		res = requests.get(f"http://127.0.0.1:{server.port}/dir1", timeout=10)
		assert res.status_code == 200
		assert res.text == "index"

		res = requests.get(f"http://127.0.0.1:{server.port}/dir2/", timeout=10)
		assert res.status_code == 404

		res = requests.get(f"http://127.0.0.1:{server.port}/404", timeout=10)
		assert res.status_code == 404

		date = formatdate(timeval=time.time())
		res = requests.get(f"http://127.0.0.1:{server.port}/dir1/file2", headers={"If-Modified-Since": date}, timeout=10)
		assert res.status_code == 304

		res = requests.get(f"http://127.0.0.1:{server.port}/dir1/file2", headers={"If-Modified-Since": "INVALID"}, timeout=10)
		assert res.status_code == 200

		res = requests.put(f"http://127.0.0.1:{server.port}/dir1/put", data="test", timeout=10)
		assert res.status_code == 201

		res = requests.head(f"http://127.0.0.1:{server.port}/dir1/file1", timeout=10)
		assert res.status_code == 200

		res = requests.delete(f"http://127.0.0.1:{server.port}/dir1/file1", timeout=10)
		assert res.status_code == 204

		res = requests.head(f"http://127.0.0.1:{server.port}/dir1/file1", timeout=10)
		assert res.status_code == 404

		res = requests.request("MKCOL", f"http://127.0.0.1:{server.port}/newdir", timeout=10)
		assert res.status_code == 201


def test_test_http_server_ranges(tmp_path: Path) -> None:
	test_file = tmp_path / "file1"
	data = randbytes(1_000)
	test_file.write_bytes(data)
	with http_test_server(serve_directory=tmp_path) as server:
		res = requests.get(f"http://127.0.0.1:{server.port}/file1", timeout=10, headers={"Range": "bytes=0-99"})
		assert res.status_code == 206
		dat = res.content
		assert len(dat) == 100
		assert dat == data[:100]

		res = requests.get(f"http://127.0.0.1:{server.port}/file1", timeout=10, headers={"Range": "bytes=-99"})
		assert res.status_code == 206
		dat = res.content
		assert len(dat) == 100
		assert dat == data[:100]

		res = requests.get(f"http://127.0.0.1:{server.port}/file1", timeout=10, headers={"Range": "bytes=100-"})
		assert res.status_code == 206
		dat = res.content
		assert len(dat) == 900
		assert dat == data[100:]

		res = requests.get(f"http://127.0.0.1:{server.port}/file1", timeout=10, headers={"Range": "bytes=0-99,200-299"})
		assert res.status_code == 206
		dat = res.content
		boundary = b"\r\n--" + res.headers["Content-Type"].split("boundary=")[1].encode("ascii")
		parts = [p.split(b"\r\n\r\n", 1)[1] for p in dat.split(boundary)[1:-1]]
		assert len(parts) == 2
		assert len(parts[0]) == 100
		assert parts[0] == data[:100]
		assert len(parts[1]) == 100
		assert parts[1] == data[200:300]

		res = requests.get(f"http://127.0.0.1:{server.port}/file1", timeout=10, headers={"Range": "bytes=-399,400-499,500-"})
		assert res.status_code == 206
		dat = res.content
		boundary = b"\r\n--" + res.headers["Content-Type"].split("boundary=")[1].encode("ascii")
		parts = [p.split(b"\r\n\r\n", 1)[1] for p in dat.split(boundary)[1:-1]]
		assert len(parts) == 3
		assert b"".join(parts) == data


def test_http_server_websocket(tmp_path: Path) -> None:
	log_file = tmp_path / "server.log"
	with http_test_server(log_file=log_file, ws_message_callback=lambda handler, message: handler.ws_send_message(b"response")) as server:
		wsock = websocket.create_connection(f"ws://127.0.0.1:{server.port}/websocket/test")
		wsock.send(b"test")
		assert wsock.recv() == b"response"
		wsock.close()
	time.sleep(1)
	reqs = [json.loads(req) for req in log_file.read_text(encoding="utf-8").strip().split("\n")]

	assert reqs[0]["method"] == "GET"
	assert reqs[0]["client_address"][0] == "127.0.0.1"
	assert reqs[0]["path"] == "/websocket/test"
	assert reqs[0]["headers"]["Host"].startswith("127.0.0.1:")
	assert reqs[0]["headers"]["Connection"] == "Upgrade"
	assert reqs[0]["headers"]["Sec-WebSocket-Key"]
	assert reqs[0]["headers"]["Sec-WebSocket-Version"]

	assert reqs[1]["method"] == "websocket"
	assert reqs[1]["client_address"][0] == "127.0.0.1"
	assert reqs[1]["path"] == "/websocket/test"
	assert reqs[1]["headers"]["Host"].startswith("127.0.0.1:")
	assert b64decode(reqs[1]["request"]) == b"test"


def test_http_server_request_callback() -> None:
	def request_callback(handler: HTTPTestServerRequestHandler, request: dict) -> bool:
		handler.set_response_status(200, "OK")
		handler.set_response_headers({"X-method": request["method"], "Content-Type": "text/plain"})
		handler.set_response_body(request["method"].encode("utf-8"))
		return False

	with http_test_server(request_callback=request_callback) as server:
		res = requests.head(f"http://127.0.0.1:{server.port}/", timeout=10)
		assert res.status_code == 200
		assert res.headers["X-method"] == "HEAD"

		res = requests.get(f"http://127.0.0.1:{server.port}/", timeout=10)
		assert res.status_code == 200
		assert res.headers["X-method"] == "GET"
		assert res.text == "GET"

		res = requests.post(f"http://127.0.0.1:{server.port}/", timeout=10)
		assert res.status_code == 200
		assert res.headers["X-method"] == "POST"
		assert res.text == "POST"

		res = requests.put(f"http://127.0.0.1:{server.port}/", timeout=10)
		assert res.status_code == 200
		assert res.headers["X-method"] == "PUT"
		assert res.headers["X-method"] == "PUT"


def test_http_server_compressed_post_and_send_max_bytes() -> None:
	with http_test_server(send_max_bytes=3, response_body=b"abcdef") as server:
		url = f"http://127.0.0.1:{server.port}/"

		res = requests.get(url, timeout=10)
		assert res.status_code == 200
		assert res.content == b"abc"

		res = requests.post(
			url,
			data=compress(json.dumps({"id": 7, "method": "gzip"}).encode("utf-8"), compression="gzip"),
			headers={"Content-Encoding": "gzip", "Content-Type": "application/json"},
			timeout=10,
		)
		assert res.status_code == 200
		assert res.content == b"abc"

	with http_test_server() as server:
		res = requests.post(
			f"http://127.0.0.1:{server.port}/",
			data=compress(json.dumps({"id": 11, "method": "gzip"}).encode("utf-8"), compression="gzip"),
			headers={"Content-Encoding": "gzip", "Content-Type": "application/json"},
			timeout=10,
		)
		assert res.json() == {"id": 11, "result": []}

		res = requests.post(
			f"http://127.0.0.1:{server.port}/",
			data=compress(msgpack_encode({"id": 12, "method": "lz4"}), compression="lz4"),
			headers={"Content-Encoding": "lz4", "Content-Type": "application/msgpack"},
			timeout=10,
		)
		assert res.json() == {"id": 12, "result": []}


def test_http_server_request_callback_can_short_circuit_response() -> None:
	def request_callback(handler: HTTPTestServerRequestHandler, request: dict) -> bool:
		handler.send_response(204, f"{request['method']} handled")
		handler.end_headers()
		return True

	with http_test_server(request_callback=request_callback) as server:
		for method in ("GET", "POST", "PUT", "MKCOL", "DELETE", "HEAD", "PROPFIND", "CONNECT"):
			res = requests.request(method, f"http://127.0.0.1:{server.port}/callback", timeout=10)
			assert res.status_code == 204


def test_http_server_method_fallbacks_and_status_overrides() -> None:
	with http_test_server(response_status=(202, "Accepted"), response_body=b"propfind") as server:
		url = f"http://127.0.0.1:{server.port}/"

		res = requests.head(url, timeout=10)
		assert res.status_code == 202

		res = requests.put(url, data=b"test", timeout=10)
		assert res.status_code == 202

		res = requests.request("PROPFIND", url, timeout=10)
		assert res.status_code == 202
		assert res.content == b"propfind"

	with http_test_server() as server:
		url = f"http://127.0.0.1:{server.port}/"

		res = requests.get(url, headers={"X-Response-Status": "201 Created"}, timeout=10)
		assert res.status_code == 201
		assert res.text == "OK"

		res = requests.request("MKCOL", url, timeout=10)
		assert res.status_code == 500

		res = requests.delete(url, timeout=10)
		assert res.status_code == 500

		res = requests.request("PROPFIND", url, timeout=10)
		assert res.status_code == 207
		assert res.content == b""

		res = requests.request("CONNECT", url, timeout=10)
		assert res.status_code == 501


def test_http_server_propfind_and_delete_directory(tmp_path: Path) -> None:
	root_dir = tmp_path / "webdav"
	root_dir.mkdir()
	(root_dir / "file.txt").write_text("content", encoding="utf-8")
	subdir = root_dir / "subdir"
	subdir.mkdir()
	(subdir / "child.txt").write_text("child", encoding="utf-8")
	with http_test_server(serve_directory=tmp_path) as server:
		url = f"http://127.0.0.1:{server.port}/webdav"

		res = requests.request("PROPFIND", url, timeout=10)
		assert res.status_code == 207
		assert "application/xml" in res.headers["Content-Type"]
		assert "<d:href>/webdav</d:href>" in res.text
		assert "<d:href>/webdav/subdir/</d:href>" in res.text

		res = requests.request("PROPFIND", f"{url}/file.txt", timeout=10)
		assert res.status_code == 207
		assert "<d:getcontentlength>7</d:getcontentlength>" in res.text

		res = requests.request("PROPFIND", f"http://127.0.0.1:{server.port}/missing", timeout=10)
		assert res.status_code == 404

		res = requests.delete(f"{url}/subdir", timeout=10)
		assert res.status_code == 204
		assert not subdir.exists()

		res = requests.delete(f"{url}/subdir", timeout=10)
		assert res.status_code == 404


def _make_headers(values: dict[str, str]) -> Message:
	headers = Message()
	for name, value in values.items():
		headers[name] = value
	return headers


def _make_http_handler() -> HTTPTestServerRequestHandler:
	test_server = SimpleNamespace(
		log_file=None,
		response_headers={},
		response_status=None,
		response_body=None,
		response_delay=None,
		request_callback=None,
		ws_connect_callback=None,
		ws_message_callback=None,
		serve_directory=None,
		send_max_bytes=None,
	)

	class FakeServer:
		def __init__(self, state: SimpleNamespace) -> None:
			self.test_server = state
			self.log_file = None
			self.request_callback = None
			self.ws_connect_callback = None
			self.ws_message_callback = None
			self.serve_directory = None
			self.send_max_bytes = None
			self.server_address = ("127.0.0.1", 4444)
			self.stopping = False

		@property
		def response_headers(self) -> dict[str, str]:
			return self.test_server.response_headers

		@property
		def response_status(self) -> tuple[int, str] | None:
			return self.test_server.response_status

		@property
		def response_body(self) -> bytes | None:
			return self.test_server.response_body

		@property
		def response_delay(self) -> float | None:
			return self.test_server.response_delay

	handler = HTTPTestServerRequestHandler.__new__(HTTPTestServerRequestHandler)
	cast(Any, handler).server = FakeServer(test_server)
	handler.headers = _make_headers({"Host": "example.invalid"})
	handler.client_address = ("127.0.0.1", 12345)
	handler.path = "/websocket"
	handler.rfile = BytesIO()
	handler.wfile = BytesIO()
	handler.connection = Mock()
	cast(Any, handler)._headers_buffer = []
	handler.request_version = "HTTP/1.1"
	handler.command = "GET"
	handler.requestline = "GET /websocket HTTP/1.1"
	handler.close_connection = False
	handler._ws_connected = False
	handler._ws_opcode = 0
	return handler


def test_http_request_handler_helper_methods() -> None:
	handler = _make_http_handler()
	handler_any = cast(Any, handler)
	handler.set_response_status(206, "Partial")
	handler.set_response_headers({"Server": "custom/1.0"})
	handler.set_response_body(b"body")

	assert handler.server.test_server.response_status == (206, "Partial")
	assert handler.server.test_server.response_headers == {"Server": "custom/1.0"}
	assert handler.server.test_server.response_body == b"body"
	assert handler.version_string() == "custom/1.0"

	handler.server.test_server.response_headers = {"Server": "skip-me", "X-Server": "{server_address}", "X-Host": "{host}"}
	handler.server.test_server.response_delay = 0.5
	with (
		patch("opsi.testing.helper._http.time.sleep") as sleep_mock,
		patch("http.server.SimpleHTTPRequestHandler.end_headers", autospec=True) as super_end_headers,
	):
		sent_headers: list[tuple[str, str]] = []
		handler_any.send_header = lambda name, value: sent_headers.append((name, value))
		handler.end_headers()

		sleep_mock.assert_called_once_with(0.5)
		super_end_headers.assert_called_once_with(handler)
		assert sent_headers == [("X-Server", "'127.0.0.1':4444"), ("X-Host", "example.invalid")]

	with patch("http.server.BaseHTTPRequestHandler.handle_one_request", side_effect=BrokenPipeError):
		handler.handle_one_request()

	logged_codes: list[int] = []
	sent_headers = []
	handler.server.test_server.response_headers = {}
	handler_any.log_request = lambda code, size="-": logged_codes.append(int(code))
	handler_any.send_response_only = lambda code, message=None: None
	handler_any.version_string = lambda: "custom/2.0"
	handler_any.date_time_string = lambda timestamp=None: "Thu, 27 Mar 2026 10:00:00 GMT"
	handler_any.send_header = lambda name, value: sent_headers.append((name, value))
	handler.send_response(200, "OK")

	assert logged_codes == [200]
	assert ("Server", "custom/2.0") in sent_headers
	assert ("Date", "Thu, 27 Mar 2026 10:00:00 GMT") in sent_headers

	handler.server.test_server.response_headers = {"Date": "preset"}
	sent_headers = []
	handler.send_response(204, "No Content")
	assert ("Date", "Thu, 27 Mar 2026 10:00:00 GMT") not in sent_headers

	handler.headers = _make_headers({"Range": "bytes=2-4,8-99"})
	assert handler._get_ranges(10) == [(2, 4), (8, 9)]


def test_http_request_handler_websocket_helpers() -> None:
	handler = _make_http_handler()
	handler_any = cast(Any, handler)
	server_any = cast(Any, handler.server)
	connected: list[bool] = []
	messages: list[bytes] = []
	server_any.ws_connect_callback = lambda current: connected.append(current is handler)
	server_any.ws_message_callback = lambda current, message: messages.append(message)

	handler.headers = _make_headers({"Upgrade": "http"})
	handler._ws_handshake()
	assert handler._ws_connected is False

	handler.headers = _make_headers({"Upgrade": "websocket", "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ=="})
	response_headers: list[tuple[str, str]] = []
	handler_any.send_response = lambda code, message=None: response_headers.append(("status", f"{code} {message}"))
	handler_any.send_header = lambda name, value: response_headers.append((name, value))
	handler_any.end_headers = lambda: response_headers.append(("end", ""))
	handler._ws_handshake()

	assert handler._ws_connected is True
	assert connected == [True]
	assert ("status", "101 Switching Protocols") in response_headers
	assert any(name == "Sec-WebSocket-Accept" for name, _value in response_headers)

	handler.on_ws_message(b"payload")
	assert messages == [b"payload"]

	ping_calls: list[tuple[int, bytes]] = []
	close_calls: list[tuple[int, str]] = []
	data_messages: list[bytes] = []
	handler_any._ws_send_message = lambda opcode, message: ping_calls.append((opcode, message))
	handler_any._ws_close = lambda code=1005, reason="": close_calls.append((code, reason))
	handler_any.on_ws_message = lambda message: data_messages.append(message)

	handler._ws_opcode = handler._opcode_ping
	handler._ws_process_message(b"ping")
	assert ping_calls == [(handler._opcode_pong, b"ping")]

	handler._ws_opcode = handler._opcode_pong
	handler._ws_process_message(b"pong")

	handler._ws_opcode = handler._opcode_text
	handler._ws_process_message(b"text")
	assert data_messages == [b"text"]

	handler._ws_opcode = handler._opcode_close
	handler._ws_process_message(b"")
	assert close_calls == [(1005, "")]


@pytest.mark.parametrize("message_length, expected_prefix", [(2, b"\x82\x02"), (126, b"\x82\x7e"), (65536, b"\x82\x7f")])
def test_http_request_handler_ws_send_message_encodes_frame_lengths(message_length: int, expected_prefix: bytes) -> None:
	handler = _make_http_handler()
	message = b"a" * message_length
	handler._ws_send_message(handler._opcode_binary, message)

	frame = cast(BytesIO, handler.wfile).getvalue()
	assert frame.startswith(expected_prefix)
	assert frame.endswith(message)


def test_http_request_handler_ws_send_and_read_error_paths() -> None:
	handler = _make_http_handler()
	handler_any = cast(Any, handler)
	close_calls: list[tuple[int, str]] = []
	handler_any._ws_close = lambda code=1005, reason="": close_calls.append((code, reason))

	class SocketFailingWriter:
		def write(self, _data: bytes) -> None:
			raise OSError("broken")

	handler_any.wfile = SocketFailingWriter()
	handler._ws_send_message(handler._opcode_binary, b"data")
	assert close_calls == [(1005, "")]

	close_calls.clear()

	class GenericFailingWriter:
		def write(self, _data: bytes) -> None:
			raise RuntimeError("boom")

	handler_any.wfile = GenericFailingWriter()
	handler._ws_send_message(handler._opcode_binary, b"data")
	assert close_calls == [(1005, "")]

	handler = _make_http_handler()
	handler._ws_connected = True
	handler.rfile = BytesIO(b"\x81~\x00")
	with pytest.raises(WebSocketError, match="read aborted while listening"):
		handler._ws_read_next_message()

	handler._ws_connected = False
	handler.rfile = BytesIO(b"\x81~\x00")
	handler._ws_read_next_message()

	handler = _make_http_handler()
	processed_messages: list[bytes] = []
	handler_any = cast(Any, handler)
	handler_any._ws_process_message = lambda message: processed_messages.append(message)
	mask = b"\x01\x02\x03\x04"
	payload = b"hello"
	masked_payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
	handler.rfile = BytesIO(b"\x82\x05" + mask + masked_payload)
	handler._ws_read_next_message()
	assert processed_messages == [payload]

	handler = _make_http_handler()
	handler_any = cast(Any, handler)
	handler_any._ws_process_message = lambda message: processed_messages.append(message)
	payload_126 = b"b" * 126
	masked_payload_126 = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload_126))
	handler.rfile = BytesIO(b"\x82\x7e" + struct.pack(">H", len(payload_126)) + mask + masked_payload_126)
	handler._ws_read_next_message()
	assert processed_messages[-1] == payload_126

	handler = _make_http_handler()
	handler_any = cast(Any, handler)
	handler_any._ws_process_message = lambda message: processed_messages.append(message)
	payload_127 = b"c" * 130
	masked_payload_127 = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload_127))
	handler.rfile = BytesIO(b"\x82\x7f" + struct.pack(">Q", len(payload_127)) + mask + masked_payload_127)
	handler._ws_read_next_message()
	assert processed_messages[-1] == payload_127

	handler = _make_http_handler()
	handler.wfile = BytesIO()
	handler._ws_send_close(0, "closing")
	frame = handler.wfile.getvalue()
	assert frame[:2] == b"\x88\x09"
	assert frame[2:4] == struct.pack("!H", 1000)
	assert frame[4:] == b"closing"


def test_http_request_handler_ws_read_messages_closes_on_errors() -> None:
	handler = _make_http_handler()
	handler_any = cast(Any, handler)
	handler._ws_connected = True
	close_calls: list[tuple[int, str]] = []
	handler_any._ws_close = lambda code=1005, reason="": close_calls.append((code, reason))

	def read_sequence() -> None:
		if len(close_calls) == 0:
			raise OSError("fail")

	handler_any._ws_read_next_message = read_sequence
	handler._ws_read_messages()
	assert close_calls == [(1005, "")]

	handler = _make_http_handler()
	handler_any = cast(Any, handler)
	handler._ws_connected = True
	close_calls = []
	handler_any._ws_close = lambda code=1005, reason="": close_calls.append((code, reason))
	handler_any._ws_read_next_message = Mock(side_effect=RuntimeError("fail"))
	handler._ws_read_messages()
	assert close_calls == [(1005, "")]

	handler = _make_http_handler()
	handler_any = cast(Any, handler)
	handler._ws_connected = True
	handler.server.stopping = True
	read_next_message = Mock()
	handler_any._ws_read_next_message = read_next_message
	handler._ws_read_messages()
	read_next_message.assert_not_called()

	handler = _make_http_handler()
	handler_any = cast(Any, handler)
	handler._ws_connected = True
	close_calls = []
	handler_any._ws_close = lambda code=1005, reason="": close_calls.append((code, reason))
	handler_any._ws_read_next_message = Mock(side_effect=[ssl.SSLWantReadError(), WebSocketError("unexpected")])
	with patch("opsi.testing.helper._http.time.sleep") as sleep_mock:
		handler._ws_read_messages()
		sleep_mock.assert_called_once_with(0.1)
	assert close_calls == [(1005, "")]


def test_http_request_handler_additional_http_branches(tmp_path: Path) -> None:
	handler = _make_http_handler()
	handler_any = cast(Any, handler)
	status_codes: list[tuple[int, str | None]] = []
	headers_sent: list[tuple[str, str]] = []
	handler_any.send_response = lambda code, message=None: status_codes.append((code, message))
	handler_any.send_header = lambda name, value: headers_sent.append((name, value))
	handler_any.end_headers = lambda: None

	handler.headers = _make_headers({"Content-Length": "4", "Content-Encoding": "", "Content-Type": "text/plain"})
	handler.rfile = BytesIO(b"test")
	handler.wfile = BytesIO()
	handler.do_POST()
	assert status_codes[-1] == (200, "OK")
	assert ("Content-Length", "0") in headers_sent
	assert handler.wfile.getvalue() == b""

	status_codes.clear()
	handler.headers = _make_headers({"Upgrade": "websocket"})
	handler.server.test_server.response_status = (403, "Denied")
	handler.do_GET()
	assert status_codes[-1] == (403, "Denied")

	status_codes.clear()
	handler.server.test_server.response_status = None
	handler.headers = _make_headers({})
	handler.do_HEAD()
	assert status_codes[-1] == (200, "OK")

	status_codes.clear()
	handler.headers = _make_headers({"Content-Length": "4"})
	handler.rfile = BytesIO(b"data")
	handler.do_PUT()
	assert status_codes[-1] == (500, "Not implemented")

	handler = _make_http_handler()
	handler_any = cast(Any, handler)
	server_any = cast(Any, handler.server)
	server_any.serve_directory = str(tmp_path)
	server_any.send_max_bytes = 3
	handler.wfile = BytesIO()
	handler_any.send_head = lambda: BytesIO(b"abcdef")
	handler.do_GET()
	assert handler.wfile.getvalue() == b"abc"

	handler = _make_http_handler()
	handler_any = cast(Any, handler)
	server_any = cast(Any, handler.server)
	server_any.serve_directory = str(tmp_path)
	handler.server.test_server.response_body = b"custom-propfind"
	handler.server.test_server.request_callback = lambda _current, _request: False
	handler.path = "/"
	handler.wfile = BytesIO()
	handler_any.translate_path = lambda path: str(tmp_path)
	status_codes = []
	headers_sent = []
	handler_any.send_response = lambda code, message=None: status_codes.append((code, message))
	handler_any.send_header = lambda name, value: headers_sent.append((name, value))
	handler_any.end_headers = lambda: None
	handler.do_PROPFIND()
	assert status_codes[-1] == (207, "Multi-Status")
	assert ("Content-Type", "application/xml") in headers_sent
	assert handler.wfile.getvalue() == b"custom-propfind"

	handler = _make_http_handler()
	handler_any = cast(Any, handler)
	handler.server.test_server.request_callback = lambda _current, _request: False
	callback_methods: list[str] = []
	handler_any.send_response = lambda code, message=None: callback_methods.append(f"{code}:{message}")
	handler_any.end_headers = lambda: None
	handler.headers = _make_headers({"Content-Length": "0"})
	handler.do_MKCOL()
	handler.do_DELETE()
	handler.do_CONNECT()
	assert callback_methods == ["500:Not implemented", "500:Not implemented", "501:I am not a proxy"]


def test_http_request_handler_send_head_and_websocket_misc_branches(tmp_path: Path) -> None:
	handler = _make_http_handler()
	handler_any = cast(Any, handler)
	file_mock = Mock()
	file_mock.fileno.return_value = 1
	handler.path = "/file.txt"
	handler.headers = _make_headers({"If-Modified-Since": "Sun, 06 Nov 1994 08:49:37"})
	handler_any.translate_path = lambda path: str(tmp_path / "file.txt")
	handler_any.guess_type = lambda path: "text/plain"
	handler_any.send_response = lambda code, message=None: None
	handler_any.send_header = lambda name, value: None
	handler_any.end_headers = lambda: None
	handler_any.date_time_string = lambda timestamp=None: "Thu, 27 Mar 2026 10:00:00 GMT"
	with patch("builtins.open", return_value=file_mock), patch("opsi.testing.helper._http.os.fstat", side_effect=RuntimeError("boom")):
		with pytest.raises(RuntimeError, match="boom"):
			handler.send_head()
	file_mock.close.assert_called_once()

	handler = _make_http_handler()
	handler.wfile = BytesIO()
	handler._ws_send_message(handler._opcode_binary, b"")
	assert handler.wfile.getvalue() == b"\x82\x00"

	handler = _make_http_handler()
	handler_any = cast(Any, handler)
	handler.server.test_server.ws_message_callback = None
	handler.on_ws_message(b"payload")

	handler._ws_connected = False
	handler._ws_close()
	assert handler.close_connection is False

	handler = _make_http_handler()
	handler_any = cast(Any, handler)
	closed: list[bool] = []
	handler._ws_connected = True
	handler_any._ws_send_close = Mock(side_effect=RuntimeError("close failed"))
	handler_any.on_ws_closed = lambda: closed.append(True)
	with patch("opsi.testing.helper._http.time.sleep"):
		handler._ws_close(1000, "bye")
	assert closed == [True]
	assert handler.close_connection is True

	handler = _make_http_handler()
	handler_any = cast(Any, handler)
	data_messages: list[bytes] = []
	handler_any.on_ws_message = lambda message: data_messages.append(message)
	handler._ws_opcode = 0x3
	handler._ws_process_message(b"ignored")
	assert data_messages == []


def test_http_test_server_run_and_restart_branches() -> None:
	server = HTTPTestServer(generate_cert=True)
	fake_socket1 = Mock()
	fake_socket2 = Mock()
	fake_server1 = SimpleNamespace(socket=fake_socket1, serve_forever=Mock(side_effect=lambda: setattr(server, "_restart_server", True)))
	fake_server2 = SimpleNamespace(socket=fake_socket2, serve_forever=Mock(side_effect=lambda: setattr(server, "_restart_server", False)))

	with (
		patch("opsi.testing.helper._http.ThreadingHTTPServer", side_effect=[fake_server1, fake_server2]),
		patch.object(server, "_generate_cert") as generate_cert,
		patch.object(server, "_init_ssl_socket") as init_ssl_socket,
		patch("opsi.testing.helper._http.time.sleep") as sleep_mock,
	):
		server.run()

	generate_cert.assert_called()
	assert generate_cert.call_count == 2
	assert init_ssl_socket.call_count == 2
	sleep_mock.assert_called_once_with(3)

	server = HTTPTestServer()
	cast(Any, server).server = SimpleNamespace()
	with patch.object(server, "stop") as stop_mock, patch.object(server, "wait_for_server_socket") as wait_mock:
		server.restart(new_cert=True)

	stop_mock.assert_called_once_with(False)
	wait_mock.assert_called_once_with()


def test_http_test_server_certificate_and_socket_helpers(tmp_path: Path) -> None:
	server = HTTPTestServer(generate_cert=True)
	server.set_option("response_delay", 1.5)
	assert server.response_delay == 1.5
	assert server.wait_for_server_socket(timeout=0) is False

	existing_key = tmp_path / "server.key"
	existing_cert = tmp_path / "server.crt"
	existing_key.write_text("key", encoding="utf-8")
	existing_cert.write_text("cert", encoding="utf-8")
	server.server_key = existing_key
	server.server_cert = existing_cert
	server._generate_cert()
	assert server.server_key == existing_key
	assert server.server_cert == existing_cert

	server.server_key = None
	server.server_cert = None
	with (
		patch("opsi.testing.helper._http.create_ca", return_value=("ca-cert", "ca-key")),
		patch("opsi.testing.helper._http.create_server_cert", return_value=("server-cert", "server-key")),
		patch("opsi.testing.helper._http.as_pem", side_effect=lambda value: f"pem:{value}"),
	):
		server._generate_cert()

		assert server.ca_key and server.ca_key.exists()
		assert server.ca_cert and server.ca_cert.exists()
		assert server.server_key and server.server_key.exists()
		assert server.server_cert and server.server_cert.exists()

	server._cleanup_cert()
	assert server.ca_key and not server.ca_key.exists()
	assert server.ca_cert and not server.ca_cert.exists()
	assert server.server_key and not server.server_key.exists()
	assert server.server_cert and not server.server_cert.exists()

	key_file = tmp_path / "tls.key"
	cert_file = tmp_path / "tls.crt"
	ca_file = tmp_path / "ca.crt"
	for path in (key_file, cert_file, ca_file):
		path.write_text("pem", encoding="utf-8")

	cast(Any, server).server = SimpleNamespace(socket="socket")
	server.server_key = key_file
	server.server_cert = cert_file
	server.ca_cert = ca_file
	context = Mock()
	context.wrap_socket.return_value = "wrapped"
	with patch("opsi.testing.helper._http.ssl.SSLContext", return_value=context) as ssl_context:
		server._init_ssl_socket()

		ssl_context.assert_called_once()
		context.load_cert_chain.assert_called_once_with(keyfile=str(key_file), certfile=str(cert_file))
		context.load_verify_locations.assert_called_once_with(cafile=str(ca_file))
		context.wrap_socket.assert_called_once_with(sock="socket", server_side=True)
		assert server.server.socket == "wrapped"


def test_http_test_server_stop_restart_and_context_manager_failure() -> None:
	server = HTTPTestServer()
	server.restart()

	fake_socket = Mock()
	fake_server = SimpleNamespace(stopping=False, socket=fake_socket, shutdown=Mock())
	cast(Any, server).server = fake_server
	server._restart_server = True
	with patch("opsi.testing.helper._http.platform.system", return_value="Linux"):
		server.stop(cleanup_cert=False)
		fake_socket.close.assert_called_once()
		fake_server.shutdown.assert_called_once()

	fake_socket = Mock()
	fake_server = SimpleNamespace(stopping=False, socket=fake_socket, shutdown=Mock())
	cast(Any, server).server = fake_server
	server._restart_server = True
	with patch("opsi.testing.helper._http.platform.system", return_value="Windows"):
		server.stop(cleanup_cert=False)
		fake_server.shutdown.assert_called_once()
		fake_socket.close.assert_called_once()

	server.server = None
	server.stop(cleanup_cert=False)
	assert server._cleanup_done.is_set()

	with (
		patch("opsi.testing.helper._http.HTTPTestServer.start", autospec=True),
		patch("opsi.testing.helper._http.HTTPTestServer.wait_for_server_socket", return_value=False),
		pytest.raises(RuntimeError, match="Failed to start HTTPTestServer"),
		http_test_server(),
	):
		pass
