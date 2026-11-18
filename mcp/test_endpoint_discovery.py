"""Endpoint discovery uses isolated files and mocked HTTP, never a real daemon."""

import json
import ctypes
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

import unlim_mcp as mcp


class EndpointDiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "api_endpoint")
        for name, value in (("ENDPOINT_PATH", self.path),
                            ("API_HOST", "127.0.0.1"), ("API_PORT", None)):
            p = patch.object(mcp, name, value)
            p.start()
            self.addCleanup(p.stop)

    def test_missing_record_does_not_probe_default_port(self):
        with patch.object(mcp.urllib.request, "urlopen") as request:
            self.assertFalse(mcp._daemon_alive())
            request.assert_not_called()

    def test_invalid_record_does_not_probe_default_port(self):
        with open(self.path, "w") as f:
            json.dump({"host": "192.0.2.1", "port": 9800}, f)
        os.chmod(self.path, 0o600)
        with patch.object(mcp.urllib.request, "urlopen") as request:
            self.assertFalse(mcp._daemon_alive())
            request.assert_not_called()

    def test_recorded_endpoint_is_preserved(self):
        with open(self.path, "w") as f:
            json.dump({"host": "127.0.0.1", "port": 12345, "pid": os.getpid()}, f)
        os.chmod(self.path, 0o600)
        self.assertEqual(mcp._endpoint(), ("127.0.0.1", 12345))

    def test_record_without_pid_is_not_used(self):
        with open(self.path, "w") as f:
            json.dump({"host": "127.0.0.1", "port": 12345}, f)
        os.chmod(self.path, 0o600)
        self.assertIsNone(mcp._endpoint())

    def test_dead_or_foreign_process_is_not_used(self):
        with open(self.path, "w") as f:
            json.dump({"host": "127.0.0.1", "port": 12345, "pid": 123}, f)
        os.chmod(self.path, 0o600)
        with patch.object(mcp, "_process_owned_and_alive", return_value=False, create=True), \
                patch.object(mcp.urllib.request, "urlopen") as request:
            self.assertFalse(mcp._daemon_alive())
            request.assert_not_called()

    @unittest.skipIf(os.name == "nt", "POSIX file permissions")
    def test_nonprivate_record_is_not_used(self):
        with open(self.path, "w") as f:
            json.dump({"host": "127.0.0.1", "port": 12345, "pid": os.getpid()}, f)
        os.chmod(self.path, 0o644)
        self.assertIsNone(mcp._endpoint())

    @unittest.skipIf(os.name == "nt", "POSIX process ownership")
    def test_process_owner_and_liveness(self):
        for output, code, want in ((f"{os.geteuid()} S", 0, True),
                                   (f"{os.geteuid() + 1} S", 0, False),
                                   (f"{os.geteuid()} Z", 0, False),
                                   ("", 1, False), ("invalid", 0, False)):
            with self.subTest(output=output, code=code), \
                    patch.object(mcp.subprocess, "run", return_value=Mock(stdout=output, returncode=code)):
                self.assertEqual(mcp._process_owned_and_alive(123), want)

    def test_invalid_pids_never_query_system(self):
        with patch.object(mcp.subprocess, "run") as run, \
                patch.object(mcp, "_windows_process_owned_and_alive") as windows:
            for pid in (None, True, 0, -1, "123", 1.5, 0x100000000):
                self.assertFalse(mcp._process_owned_and_alive(pid))
            run.assert_not_called()
            windows.assert_not_called()

    def test_windows_inaccessible_process_is_rejected(self):
        kernel, security = Mock(), Mock()
        kernel.OpenProcess.return_value = 0
        with patch.object(ctypes, "WinDLL", side_effect=[kernel, security], create=True):
            self.assertFalse(mcp._windows_process_owned_and_alive(123))
        kernel.OpenProcess.assert_called_once_with(0x101000, False, 123)
        kernel.CloseHandle.assert_not_called()

    def test_windows_token_failure_still_closes_process(self):
        kernel, security = Mock(), Mock()
        kernel.OpenProcess.return_value = 10
        kernel.WaitForSingleObject.return_value = 0x102
        kernel.GetCurrentProcess.return_value = -1
        security.OpenProcessToken.return_value = False
        with patch.object(ctypes, "WinDLL", side_effect=[kernel, security], create=True):
            self.assertFalse(mcp._windows_process_owned_and_alive(123))
        kernel.CloseHandle.assert_called_once_with(10)
        security.EqualSid.assert_not_called()

    def test_windows_identity_success_failure_and_cleanup(self):
        for mode, expected in (("same", True), ("foreign", False),
                               ("info-failure", False), ("exited", False)):
            with self.subTest(mode=mode):
                kernel, security = Mock(), Mock()
                kernel.OpenProcess.return_value = 10
                kernel.GetCurrentProcess.return_value = -1
                kernel.WaitForSingleObject.side_effect = [0x102, 0 if mode == "exited" else 0x102]
                tokens = []

                def open_token(process, access, out):
                    self.assertEqual(access, 0x0008)
                    handle = 100 + len(tokens)
                    tokens.append(handle)
                    out._obj.value = handle
                    return True

                def token_info(token, kind, buf, length, needed):
                    self.assertEqual(kind, 1)
                    needed._obj.value = 64
                    if buf is None:
                        return False
                    if mode == "info-failure" and token.value == 100:
                        return False
                    sid = 43 if mode == "foreign" and token.value == 100 else 42
                    ctypes.cast(buf, ctypes.POINTER(ctypes.c_void_p))[0] = sid
                    return True

                security.OpenProcessToken.side_effect = open_token
                security.GetTokenInformation.side_effect = token_info
                security.EqualSid.side_effect = lambda a, b: a == b
                with patch.object(ctypes, "WinDLL", side_effect=[kernel, security], create=True):
                    self.assertEqual(mcp._windows_process_owned_and_alive(123), expected)
                closed = [getattr(call.args[0], "value", call.args[0]) for call in kernel.CloseHandle.call_args_list]
                self.assertEqual(closed, [100, 101, 10])

    def test_explicit_endpoint_is_preserved(self):
        with patch.object(mcp, "API_PORT", 12346):
            self.assertEqual(mcp._endpoint(), ("127.0.0.1", 12346))

    def test_explicit_remote_endpoint_is_rejected(self):
        with patch.object(mcp, "API_HOST", "192.0.2.1"), \
                patch.object(mcp, "API_PORT", 12346):
            with self.assertRaises(ValueError):
                mcp._endpoint()

    def test_unrecorded_listener_cannot_receive_token(self):
        process = Mock()
        process.poll.return_value = 1
        process.returncode = 1
        process.stderr.read.return_value = b"synthetic startup failure"
        with patch.object(mcp.subprocess, "Popen", return_value=process), \
                patch.object(mcp, "_daemon", None), \
                patch.object(mcp, "_token") as token, \
                patch.object(mcp.urllib.request, "urlopen") as request:
            with self.assertRaises(RuntimeError):
                mcp._api("GET", "/api/status")
            token.assert_not_called()
            request.assert_not_called()

    def test_reuses_the_endpoint_that_was_probed(self):
        first = ("127.0.0.1", 12345)
        with patch.object(mcp, "_endpoint", side_effect=[first, ("127.0.0.1", 12346)]) as endpoint, \
                patch.object(mcp.urllib.request, "urlopen"), \
                patch.object(mcp.subprocess, "Popen") as spawn:
            self.assertEqual(mcp._start_daemon(), first)
            self.assertEqual(endpoint.call_count, 1)
            spawn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
