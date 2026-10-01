"""Headless Chromium regression checks for the static course's keyboard UX.

This test uses only Python's standard library and an already-installed Chromium.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


REPOSITORY = Path(__file__).resolve().parents[2]
COURSE = REPOSITORY / "docs" / "index.html"
CHROMIUM = shutil.which("chromium") or shutil.which("chromium-browser")
if not CHROMIUM and Path("/repl/tools/bin/chromium").is_file():
    CHROMIUM = "/repl/tools/bin/chromium"


def unused_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


class DevTools:
    """Minimal synchronous Chrome DevTools Protocol client using stdlib sockets."""

    def __init__(self, websocket_url):
        from urllib.parse import urlsplit

        endpoint = urlsplit(websocket_url)
        self.socket = socket.create_connection((endpoint.hostname, endpoint.port), timeout=10)
        self.socket.settimeout(10)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        path = endpoint.path + (f"?{endpoint.query}" if endpoint.query else "")
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {endpoint.netloc}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.socket.sendall(request.encode("ascii"))
        response = b""
        while b"\r\n\r\n" not in response:
            response += self.socket.recv(4096)
        headers, body = response.split(b"\r\n\r\n", 1)
        headers = headers.decode("latin1")
        expected = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        if " 101 " not in headers or f"Sec-WebSocket-Accept: {expected}" not in headers:
            raise RuntimeError(f"Chromium DevTools websocket handshake failed: {headers} {body!r}")
        self.next_id = 0

    def _send_frame(self, opcode, payload):
        payload = payload if isinstance(payload, bytes) else payload.encode("utf-8")
        mask = os.urandom(4)
        length = len(payload)
        if length < 126:
            header = bytes((0x80 | opcode, 0x80 | length))
        elif length < 65536:
            header = bytes((0x80 | opcode, 0x80 | 126)) + struct.pack("!H", length)
        else:
            header = bytes((0x80 | opcode, 0x80 | 127)) + struct.pack("!Q", length)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self.socket.sendall(header + mask + masked)

    def _read_exactly(self, length):
        data = bytearray()
        while len(data) < length:
            chunk = self.socket.recv(length - len(data))
            if not chunk:
                raise RuntimeError("Chromium closed the DevTools websocket")
            data.extend(chunk)
        return bytes(data)

    def _read_message(self):
        chunks = []
        while True:
            first, second = self._read_exactly(2)
            opcode = first & 0x0F
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exactly(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exactly(8))[0]
            mask = self._read_exactly(4) if second & 0x80 else None
            payload = self._read_exactly(length)
            if mask:
                payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
            if opcode == 9:
                self._send_frame(10, payload)
                continue
            if opcode == 8:
                raise RuntimeError("Chromium closed the DevTools websocket")
            chunks.append(payload)
            if first & 0x80:
                return json.loads(b"".join(chunks).decode("utf-8"))

    def call(self, method, params=None):
        self.next_id += 1
        command_id = self.next_id
        self._send_frame(1, json.dumps({
            "id": command_id, "method": method, "params": params or {},
        }))
        while True:
            message = self._read_message()
            if message.get("id") == command_id:
                if "error" in message:
                    raise RuntimeError(f"{method} failed: {message['error']}")
                return message.get("result", {})

    def evaluate(self, expression):
        result = self.call("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        })
        if result.get("exceptionDetails"):
            raise AssertionError(f"Browser evaluation failed: {result['exceptionDetails']}")
        return result.get("result", {}).get("value")

    def key(self, key, *, shift=False, text=None):
        codes = {"Tab": 9, "Enter": 13, "Escape": 27}
        params = {
            "key": key,
            "code": key,
            "windowsVirtualKeyCode": codes[key],
            "nativeVirtualKeyCode": codes[key],
            "modifiers": 8 if shift else 0,
        }
        if text is not None:
            params["text"] = text
        self.call("Input.dispatchKeyEvent", dict(params, type="keyDown"))
        self.call("Input.dispatchKeyEvent", dict(params, type="keyUp"))

    def close(self):
        try:
            self._send_frame(8, b"")
        except OSError:
            pass
        self.socket.close()


@unittest.skipUnless(CHROMIUM, "headless Chromium is not installed")
class CourseKeyboardNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not COURSE.is_file():
            raise RuntimeError(f"Static course not found: {COURSE}")
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="course-keyboard-test-")
        cls.server_port = unused_port()
        cls.chrome_port = unused_port()
        cls.server = subprocess.Popen(
            [
                sys.executable,
                "-m", "http.server", str(cls.server_port),
                "--bind", "127.0.0.1", "--directory", str(REPOSITORY / "docs"),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        cls.chrome = subprocess.Popen(
            [
                CHROMIUM, "--headless", "--no-sandbox", "--disable-gpu",
                "--disable-dev-shm-usage", "--disable-background-networking",
                "--no-first-run", "--no-default-browser-check",
                "--remote-allow-origins=*",
                f"--remote-debugging-address=127.0.0.1",
                f"--remote-debugging-port={cls.chrome_port}",
                f"--user-data-dir={cls.temp_dir.name}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        cls.base_url = f"http://127.0.0.1:{cls.server_port}/"
        cls.devtools_url = f"http://127.0.0.1:{cls.chrome_port}"
        cls._wait_for_service(cls.base_url)
        cls._wait_for_service(cls.devtools_url + "/json/version")

    @classmethod
    def _wait_for_service(cls, url):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if cls.server.poll() is not None or cls.chrome.poll() is not None:
                raise RuntimeError("The static server or Chromium exited during startup")
            try:
                with urlopen(url, timeout=1):
                    return
            except (URLError, OSError):
                time.sleep(0.1)
        raise RuntimeError(f"Service did not start in time: {url}")

    @classmethod
    def tearDownClass(cls):
        for process in (getattr(cls, "chrome", None), getattr(cls, "server", None)):
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        if hasattr(cls, "temp_dir"):
            cls.temp_dir.cleanup()

    def setUp(self):
        target_url = self.base_url
        request = Request(
            f"{self.devtools_url}/json/new?{quote(target_url, safe=':/')}",
            method="PUT",
        )
        with urlopen(request, timeout=5) as response:
            target = json.load(response)
        self.browser = DevTools(target["webSocketDebuggerUrl"])
        self.browser.call("Page.enable")
        self.browser.call("Runtime.enable")
        self.browser.call("Page.navigate", {"url": target_url})
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.browser.evaluate("document.readyState") == "complete":
                break
            time.sleep(0.1)
        else:
            self.fail("The course page did not finish loading")

    def tearDown(self):
        if hasattr(self, "browser"):
            self.browser.close()

    def tab(self, count=1, *, shift=False):
        for _ in range(count):
            self.browser.key("Tab", shift=shift)

    def enter(self):
        self.browser.key("Enter", text="\r")

    def active_focus(self):
        return self.browser.evaluate("""
          (() => {
            const el = document.activeElement;
            return {tag: el.tagName, id: el.id, text: (el.innerText || el.getAttribute('aria-label') || '').trim()};
          })()
        """)

    def tab_until(self, predicate, limit=250):
        for _ in range(limit):
            if self.browser.evaluate(predicate):
                return
            self.tab()
        self.fail(f"Could not reach keyboard target within {limit} Tab presses")

    def test_course_serves_with_landmarks_focus_ring_and_reachable_visible_controls(self):
        response = urlopen(self.base_url, timeout=5)
        self.assertEqual(response.status, 200)
        self.assertIn("PM Workbench", response.read().decode("utf-8"))
        loaded = self.browser.evaluate("""
          (() => ({
            title: document.title,
            language: document.documentElement.lang,
            main: document.querySelectorAll('main').length,
            header: document.querySelectorAll('body > header').length,
            footer: document.querySelectorAll('body > footer').length,
            navLabel: document.querySelector('nav[aria-label="Course view"]') !== null,
            heading: document.querySelector('.view.active h1')?.textContent.trim() || '',
            activeView: document.querySelector('.view.active')?.id || '',
          }))()
        """)
        self.assertEqual(loaded["language"], "en")
        self.assertEqual(loaded["main"], 1)
        self.assertEqual(loaded["header"], 1)
        self.assertEqual(loaded["footer"], 1)
        self.assertTrue(loaded["navLabel"])
        self.assertTrue(loaded["heading"], "Main course heading must load")
        self.assertTrue(loaded["activeView"], "The course's initial view must be active")

        controls = self.browser.evaluate("""
          (() => {
            const selector = 'a[href],button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex]:not([tabindex="-1"])';
            return [...document.querySelectorAll(selector)].filter(el =>
              el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden' &&
              !el.closest('[inert],[aria-hidden="true"]')
            ).map((el, index) => {
              el.dataset.keyboardTestIndex = String(index);
              return {index, tag: el.tagName, id: el.id, text: (el.innerText || el.getAttribute('aria-label') || '').trim()};
            });
          })()
        """)
        self.assertGreater(len(controls), 5, "The loaded course should expose keyboard controls")
        self.tab()
        ring = self.browser.evaluate("""
          (() => {
            const el = document.activeElement;
            const style = getComputedStyle(el);
            return {tag: el.tagName, outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth, outlineColor: style.outlineColor};
          })()
        """)
        self.assertNotEqual(ring["outlineStyle"], "none", f"Keyboard focus needs a visible outline: {ring}")
        self.assertGreater(float(ring["outlineWidth"].replace("px", "")), 0, f"Focus outline has no width: {ring}")

        visited = set()
        for _ in range(len(controls) + 2):
            active = self.browser.evaluate(
                "document.activeElement.getAttribute('data-keyboard-test-index')"
            )
            if active is None:
                break
            index = int(active)
            if index in visited:
                break
            visited.add(index)
            self.tab()
        expected = {control["index"] for control in controls}
        missing = [control for control in controls if control["index"] not in visited]
        self.assertFalse(
            missing,
            "Visible controls skipped by sequential Tab navigation: " +
            ", ".join(f"{item['tag']}#{item['id']} {item['text'][:35]}" for item in missing),
        )

    def test_keyboard_navigation_and_workspace_file_dialog_focus_containment_and_restoration(self):
        self.tab()
        self.assertEqual(self.active_focus()["tag"], "BUTTON")
        self.assertEqual(self.active_focus()["text"].lower(), "pmworkbench")

        # Reach and activate the home view's course entry with the actual Tab/Enter keys.
        self.tab_until("document.activeElement.matches('.home-actions button')")
        self.enter()
        self.assertTrue(self.browser.evaluate("document.querySelector('.view.active h1')?.textContent.trim()"))
        self.assertEqual(self.browser.evaluate("document.activeElement.tagName"), "H1")
        self.assertEqual(self.browser.evaluate("document.activeElement.tabIndex"), -1)
        lesson_controls = self.browser.evaluate("""
          (() => {
            const selector = 'a[href],button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex]:not([tabindex="-1"])';
            return [...document.querySelectorAll(selector)].filter(el =>
              el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden' &&
              !el.closest('[inert],[aria-hidden="true"]')
            ).map((el, index) => {
              el.dataset.keyboardTestIndex = String(index);
              return {index, tag: el.tagName, id: el.id, text: (el.innerText || el.getAttribute('aria-label') || '').trim()};
            });
          })()
        """)
        self.assertGreater(len(lesson_controls), 5, "The lesson view should expose keyboard controls")
        # The heading is programmatically focused after navigation but not in the
        # normal Tab order. Reverse-tab to the first sequential control, then audit
        # the complete cycle including the shared header.
        for _ in range(30):
            if self.browser.evaluate("document.activeElement.matches('.brand')"):
                break
            self.tab(shift=True)
        else:
            self.fail("Could not reverse-tab from the lesson heading to the first course control")
        lesson_visited = set()
        for _ in range(len(lesson_controls) + 2):
            active = self.browser.evaluate(
                "document.activeElement.getAttribute('data-keyboard-test-index')"
            )
            if active is None:
                break
            index = int(active)
            if index in lesson_visited:
                break
            lesson_visited.add(index)
            self.tab()
        lesson_missing = [control for control in lesson_controls if control["index"] not in lesson_visited]
        self.assertFalse(
            lesson_missing,
            "Visible lesson controls skipped by sequential Tab navigation: " +
            ", ".join(f"{item['tag']}#{item['id']} {item['text'][:35]}" for item in lesson_missing),
        )

        # Workspace drawer is non-modal: its close control is focused and Escape returns
        # to the invoking header button. It is inert while closed.
        self.tab_until("document.activeElement.matches('.wsbtn')")
        self.enter()
        self.assertEqual(self.browser.evaluate("document.activeElement.getAttribute('aria-label')"), "Close workspace")
        self.assertTrue(self.browser.evaluate("document.getElementById('ws').classList.contains('open')"))
        self.assertFalse(self.browser.evaluate("document.getElementById('ws').inert"))
        self.browser.key("Escape")
        self.assertEqual(self.browser.evaluate("document.activeElement.matches('.wsbtn')"), True)
        self.assertEqual(self.browser.evaluate("document.querySelector('.wsbtn').getAttribute('aria-expanded')"), "false")
        self.assertTrue(self.browser.evaluate("document.getElementById('ws').inert"))

        # Re-open, tab to an actual workspace file and activate it by keyboard.
        self.enter()
        self.tab()
        self.enter()
        self.assertTrue(self.browser.evaluate("document.getElementById('modal').classList.contains('open')"))
        self.assertEqual(self.browser.evaluate("document.activeElement.getAttribute('aria-label')"), "Close file")
        self.assertTrue(self.browser.evaluate("document.getElementById('modal').getAttribute('aria-modal') === 'true'"))
        self.assertTrue(self.browser.evaluate("document.querySelector('header').inert"))

        # With only one modal control, both Tab and Shift+Tab must remain contained.
        self.tab()
        self.assertEqual(self.browser.evaluate("document.activeElement.getAttribute('aria-label')"), "Close file")
        self.tab(shift=True)
        self.assertEqual(self.browser.evaluate("document.activeElement.getAttribute('aria-label')"), "Close file")
        self.browser.key("Escape")
        self.assertFalse(self.browser.evaluate("document.getElementById('modal').classList.contains('open')"))
        self.assertEqual(
            self.browser.evaluate("document.activeElement.matches('#wsFiles button')"),
            True,
            "Closing the file dialog should restore focus to the file that opened it",
        )
        self.assertFalse(self.browser.evaluate("document.querySelector('header').inert"))


if __name__ == "__main__":
    unittest.main()