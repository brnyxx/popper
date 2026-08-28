"""AC8 - 표준 라이브러리만 쓰는 로컬 단일 페이지 서버.

경로는 셋뿐이다.

  GET  /        완성된 단일 페이지. 첫 응답에 이미 첫 페어가 박혀 있다.
  GET  /state   현재 페어 + 가설 카운터 + 컴파일된 룰 JSON.
  POST /strike  긋기 한 건을 받고 갱신된 같은 JSON을 되돌려준다.

승인/확정 경로는 존재하지 않는다. 서버가 받는 유일한 쓰기 동사는 긋기다.
루프백 주소에만 바인딩하며 외부로 나가는 요청은 한 건도 만들지 않는다.
"""

from __future__ import annotations

import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from popper.events import SchemaViolation
from popper.web.page import render_page
from popper.web.state import ColdOpenSession

logger = logging.getLogger(__name__)

HOST = "127.0.0.1"
EPHEMERAL_PORT = 0

PATH_INDEX = "/"
PATH_STATE = "/state"
PATH_STRIKE = "/strike"

CONTENT_HTML = "text/html; charset=utf-8"
CONTENT_JSON = "application/json; charset=utf-8"

#: 긋기 본문은 대상 이름 하나가 전부라 이보다 커질 이유가 없다.
MAX_BODY_BYTES = 4096


class ColdOpenServer(ThreadingHTTPServer):
    """콜드 오픈 세션 하나를 들고 있는 로컬 서버."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
        session: ColdOpenSession,
    ) -> None:
        self.session = session
        super().__init__(server_address, handler_class)

    @property
    def url(self) -> str:
        host, port = self.server_address[0], self.server_address[1]
        return f"http://{host}:{port}/"


class ColdOpenHandler(BaseHTTPRequestHandler):
    """긋기만 받는 요청 핸들러."""

    server_version = "PopperColdOpen"
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        session = self._session()
        if self.path == PATH_INDEX:
            body = render_page(session.snapshot()).encode("utf-8")
            self._send(HTTPStatus.OK, CONTENT_HTML, body)
            return
        if self.path == PATH_STATE:
            self._send_json(HTTPStatus.OK, session.snapshot().to_dict())
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "unknown_path", "path": self.path})

    def do_POST(self) -> None:
        if self.path != PATH_STRIKE:
            self._send_json(
                HTTPStatus.NOT_FOUND, {"error": "unknown_path", "path": self.path}
            )
            return
        try:
            payload = self._read_json()
        except ValueError as e:
            logger.warning("긋기 본문을 해석하지 못했다", exc_info=True)
            self._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "malformed_body", "detail": str(e)}
            )
            return

        target = payload.get("target")
        try:
            snapshot = self._session().strike(str(target))
        except SchemaViolation as e:
            logger.warning("긋기 대상이 스키마를 위반했다: %r", target, exc_info=True)
            self._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "unknown_target", "detail": str(e)}
            )
            return
        self._send_json(HTTPStatus.OK, snapshot.to_dict())

    def log_message(self, format: str, *args: Any) -> None:
        """접근 로그를 stderr 대신 모듈 로거로 흘린다."""
        logger.debug("%s - %s", self.address_string(), format % args)

    def _session(self) -> ColdOpenSession:
        return self.server.session

    def _read_json(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ValueError("Content-Length 헤더가 없다")
        try:
            length = int(raw_length)
        except ValueError as e:
            raise ValueError(f"Content-Length가 정수가 아니다: {raw_length!r}") from e
        if length < 0 or length > MAX_BODY_BYTES:
            raise ValueError(f"본문 길이가 허용 범위를 벗어났다: {length}")
        try:
            document = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ValueError(f"JSON 본문이 아니다: {e}") from e
        if not isinstance(document, dict):
            raise ValueError("본문 최상위는 객체여야 한다")
        return document

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, CONTENT_JSON, body)

    def _send(self, status: HTTPStatus, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def build_server(
    session: ColdOpenSession | None = None,
    host: str = HOST,
    port: int = EPHEMERAL_PORT,
    repo_root: Path | str | None = None,
) -> ColdOpenServer:
    """바인딩까지 끝난 서버를 돌려준다 - 세션이 없으면 여기서 콜드 오픈한다."""
    active = session if session is not None else ColdOpenSession(repo_root=repo_root)
    server = ColdOpenServer((host, port), ColdOpenHandler, active)
    logger.info("콜드 오픈 서버 대기: %s", server.url)
    return server


def serve(
    host: str = HOST,
    port: int = EPHEMERAL_PORT,
    repo_root: Path | str | None = None,
) -> None:
    """서버를 열고 인터럽트가 올 때까지 요청을 받는다."""
    server = build_server(host=host, port=port, repo_root=repo_root)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("콜드 오픈 서버를 닫는다")
    finally:
        server.shutdown()
        server.server_close()
