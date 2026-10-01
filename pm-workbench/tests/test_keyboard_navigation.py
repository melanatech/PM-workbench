"""Headless Chromium regression checks for the static course's keyboard UX.

This test uses only Python's standard library and an already-installed Chromium.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import signal
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
CHROMIUM = (
    shutil.which("chromium") or shutil.which("chromium-browser")
    or shutil.which("google-chrome") or shutil.which("google-chrome-stable")
)
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
        cls.addClassCleanup(cls.temp_dir.cleanup)
        # Registered before starting either process so partial setup failures
        # still stop any subprocesses before removing the Chromium profile.
        cls.addClassCleanup(cls._stop_processes)
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
            start_new_session=True,
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
            start_new_session=True,
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
    def _group_is_alive(cls, process):
        process.poll()  # Reap an exited group leader before checking the group.
        try:
            os.killpg(process.pid, 0)
            return True
        except ProcessLookupError:
            return False

    @classmethod
    def _terminate_process_group(cls, process, name):
        if not process:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

        deadline = time.monotonic() + 5
        while cls._group_is_alive(process) and time.monotonic() < deadline:
            time.sleep(0.05)
        if cls._group_is_alive(process):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            deadline = time.monotonic() + 5
            while cls._group_is_alive(process) and time.monotonic() < deadline:
                time.sleep(0.05)
        if cls._group_is_alive(process):
            raise RuntimeError(f"{name} process group {process.pid} would not stop")
        process.wait(timeout=1)

    @classmethod
    def _stop_processes(cls):
        chrome = getattr(cls, "chrome", None)
        devtools_url = getattr(cls, "devtools_url", None)
        if chrome and devtools_url and cls._group_is_alive(chrome):
            # Ask Chromium to flush and close its profile before terminating its
            # isolated process group. A closed DevTools socket is acceptable only
            # if the process-group check below confirms that shutdown completed.
            browser_socket = None
            try:
                with urlopen(devtools_url + "/json/version", timeout=2) as response:
                    browser_endpoint = json.load(response)["webSocketDebuggerUrl"]
                browser_socket = DevTools(browser_endpoint)
                browser_socket.call("Browser.close")
            except (OSError, RuntimeError, URLError, KeyError, ValueError):
                pass
            finally:
                if browser_socket:
                    browser_socket.close()

        failures = []
        for name, process in (("Chromium", chrome), ("Static server", getattr(cls, "server", None))):
            try:
                cls._terminate_process_group(process, name)
            except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
                failures.append(f"{name} cleanup failed: {exc}")
        if failures:
            raise RuntimeError("; ".join(failures))

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

    def wait_until(self, predicate, description, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.browser.evaluate(predicate):
                return
            time.sleep(0.1)
        self.fail(f"Timed out waiting for {description}")

    def assert_visible_controls_keyboard_accessible(self):
        self.wait_until(
            "Number(getComputedStyle(document.querySelector('.view.active')).opacity) > 0.99",
            "the active course view's entry transition to finish",
            timeout=5,
        )
        controls = self.browser.evaluate("""
          (() => {
            const selector = 'a[href],button,input,select,textarea,[role="button"],[tabindex]:not([tabindex="-1"])';
            const isVisiblyDisplayed = el => {
              if (!el.getClientRects().length) return false;
              for (let node = el; node; node = node.parentElement) {
                const style = getComputedStyle(node);
                if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) return false;
                if (style.transform !== 'none') {
                  const rect = node.getBoundingClientRect();
                  if (rect.right <= 0 || rect.left >= innerWidth || rect.bottom <= 0) return false;
                }
              }
              return true;
            };
            const visible = [...document.querySelectorAll(selector)].filter(isVisiblyDisplayed);
            return visible.map((el, index) => {
              el.dataset.keyboardAuditIndex = String(index);
              return {
                index,
                tag: el.tagName,
                id: el.id,
                text: (el.innerText || el.getAttribute('aria-label') || '').trim(),
                disabled: el.matches(':disabled'),
                inert: Boolean(el.closest('[inert]')),
                ariaHidden: Boolean(el.closest('[aria-hidden="true"]')),
                tabIndex: el.tabIndex,
              };
            });
          })()
        """)
        self.assertGreater(len(controls), 5, "The visible course view should expose keyboard controls")
        disabled = [control for control in controls if control["disabled"]]
        inaccessible = [
            control for control in controls
            if not control["disabled"] and (
                control["inert"] or control["ariaHidden"] or control["tabIndex"] < 0
            )
        ]
        describe = lambda items: ", ".join(
            f"{item['tag']}#{item['id']} {item['text'][:35]}" for item in items
        )
        self.assertFalse(
            inaccessible,
            "Visibly displayed enabled controls must not be inert, aria-hidden, or removed from Tab order: " +
            describe(inaccessible),
        )
        expected = {control["index"] for control in controls if not control["disabled"]}

        # Start the real sequential keyboard traversal from the document's natural
        # unfocused state. Inert/aria-hidden controls were collected above, rather
        # than filtered out as though their ineligibility made them non-existent.
        self.browser.evaluate("document.activeElement.blur()")
        for _ in range(len(controls) + 2):
            active = self.browser.evaluate(
                "document.activeElement.getAttribute('data-keyboard-audit-index')"
            )
            if active == "0":
                break
            self.tab(shift=True)
        else:
            self.fail("Could not reverse-tab to the first visible control before the reachability audit")
        ring = self.browser.evaluate("""
          (() => {
            const style = getComputedStyle(document.activeElement);
            return {outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth};
          })()
        """)
        self.assertNotEqual(ring["outlineStyle"], "none", f"Keyboard focus needs a visible outline: {ring}")
        self.assertGreater(float(ring["outlineWidth"].replace("px", "")), 0, f"Focus outline has no width: {ring}")

        visited = set()
        for _ in range(len(controls) + 2):
            active = self.browser.evaluate(
                "document.activeElement.getAttribute('data-keyboard-audit-index')"
            )
            if active is None:
                break
            index = int(active)
            if index in visited:
                break
            visited.add(index)
            self.tab()
        missing = [
            control for control in controls
            if not control["disabled"] and control["index"] not in visited
        ]
        self.assertFalse(
            missing,
            "Visibly displayed enabled controls skipped by sequential Tab navigation: " +
            describe(missing) + f"; visited indexes: {sorted(visited)}",
        )
        return controls

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
        self.assert_visible_controls_keyboard_accessible()

    def test_visible_inert_and_aria_hidden_controls_fail_the_keyboard_oracle(self):
        selector = ".home-actions button:first-child"
        for attribute, value, expected_message in (
            ("inert", "", "inert"),
            ("aria-hidden", "true", "aria-hidden"),
        ):
            previous = self.browser.evaluate(
                f"document.querySelector('{selector}').getAttribute('{attribute}')"
            )
            self.browser.evaluate(
                f"document.querySelector('{selector}').setAttribute('{attribute}', {json.dumps(value)})"
            )
            try:
                with self.assertRaisesRegex(AssertionError, expected_message):
                    self.assert_visible_controls_keyboard_accessible()
            finally:
                self.browser.evaluate(f"""
                  (() => {{
                    const control = document.querySelector('{selector}');
                    const previous = {json.dumps(previous)};
                    if (previous === null) control.removeAttribute('{attribute}');
                    else control.setAttribute('{attribute}', previous);
                  }})()
                """)
            self.assertEqual(
                self.browser.evaluate(f"document.querySelector('{selector}').getAttribute('{attribute}')"),
                previous,
                f"The {attribute} regression mutation should be restored after its check",
            )
            self.assert_visible_controls_keyboard_accessible()

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
        self.assert_visible_controls_keyboard_accessible()
        self.assertGreater(
            self.browser.evaluate("document.querySelectorAll('#v-l0 .preserved-stage-button').length"),
            1,
            "The initial lesson needs multiple keyboard-selectable stages",
        )

        # Select a different lesson stage with Tab/Enter and verify the disclosure
        # state and active panel stay synchronized.
        self.tab_until("document.activeElement.matches('#v-l0 .preserved-stage-button:nth-child(2)')")
        self.enter()
        switched_stage = self.browser.evaluate("""
          (() => {
            const button = document.querySelector('#v-l0 .preserved-stage-button:nth-child(2)');
            const panel = document.getElementById(button.dataset.stageTarget);
            return {
              focused: document.activeElement === button,
              expanded: button.getAttribute('aria-expanded'),
              active: button.classList.contains('active'),
              panelVisible: panel.classList.contains('active') && panel.getAttribute('aria-hidden') === 'false',
            };
          })()
        """)
        self.assertTrue(switched_stage["focused"])
        self.assertEqual(switched_stage["expanded"], "true")
        self.assertTrue(switched_stage["active"])
        self.assertTrue(switched_stage["panelVisible"])

        # Navigate through several distinct lesson views via their keyboard-accessible
        # course rail, auditing each view's displayed controls before continuing.
        for rail_index, view_id in ((2, "v-l1"), (3, "v-l2"), (5, "v-l4")):
            target = f".view.active .preserved-rail button:nth-child({rail_index})"
            self.tab_until(f"document.activeElement.matches('{target}')")
            self.enter()
            self.assertEqual(
                self.browser.evaluate("document.querySelector('.view.active').id"),
                view_id,
            )
            self.assertEqual(self.browser.evaluate("document.activeElement.tagName"), "H1")
            self.assert_visible_controls_keyboard_accessible()

        # Reach the weekly simulation stage in Meetings, run it from its keyboard
        # control, then activate both the generated and follow-up choices by keyboard.
        self.tab_until("""
          [...document.querySelectorAll('.view.active .preserved-stage-button')].some(button =>
            button === document.activeElement && button.textContent.includes('Draft the weekly update')
          )
        """)
        self.enter()
        self.assertTrue(self.browser.evaluate("""
          document.querySelector('#v-l4 [data-sim="weekly"]')
            ?.closest('.preserved-stage').classList.contains('active')
        """))
        self.tab_until("document.activeElement.matches('#v-l4 [data-sim=\"weekly\"] .runbtn')")
        self.enter()
        try:
            self.wait_until(
                "!!document.querySelector('#v-l4 [data-sim=\"weekly\"] .choices button')",
                "the weekly simulation's first generated choice",
            )
        except AssertionError:
            state = self.browser.evaluate("""
              (() => {
                const term = document.querySelector('#v-l4 [data-sim="weekly"]');
                return {active: document.activeElement.outerHTML.slice(0, 200), disabled: term.querySelector('.runbtn').disabled,
                  body: term.querySelector('.term-body').innerText.slice(-500), stageActive: term.closest('.preserved-stage').classList.contains('active')};
              })()
            """)
            self.fail(f"Weekly simulation failed to create its choice: {state}")
        self.assert_visible_controls_keyboard_accessible()
        self.tab_until("document.activeElement.matches('#v-l4 [data-sim=\"weekly\"] .choices button')")
        self.assertTrue(self.browser.evaluate("!!document.activeElement.closest('.choices')"))
        self.enter()
        self.wait_until(
            "!!document.querySelector('#v-l4 [data-sim=\"weekly\"] .choices button')",
            "the weekly simulation's follow-up choice",
        )
        self.assert_visible_controls_keyboard_accessible()
        self.tab_until("document.activeElement.matches('#v-l4 [data-sim=\"weekly\"] .choices button')")
        self.enter()
        self.wait_until(
            "!!document.querySelector('#v-l4 [data-sim=\"weekly\"] .done-tag')",
            "the weekly simulation to finish after keyboard choice",
        )
        self.assertTrue(self.browser.evaluate("state.simsDone.has('weekly')"))

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