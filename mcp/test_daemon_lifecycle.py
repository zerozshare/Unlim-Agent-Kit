"""Daemon startup regressions; all process and network calls are mocked."""

import unittest
from unittest.mock import Mock, patch

import unlim_mcp as mcp


class DaemonLifecycleTest(unittest.TestCase):
    def setUp(self):
        explicit = patch.object(mcp, "API_PORT", None)
        explicit.start()
        self.addCleanup(explicit.stop)

    def test_unreachable_explicit_port_does_not_spawn(self):
        with patch.object(mcp, "API_PORT", 12345), \
                patch.object(mcp, "_reachable_endpoint", return_value=None), \
                patch.object(mcp.subprocess, "Popen") as spawn:
            with self.assertRaises(RuntimeError):
                mcp._start_daemon(timeout=0)
            spawn.assert_not_called()

    def test_timeout_does_not_replace_a_live_owned_daemon(self):
        owned = Mock()
        owned.poll.return_value = None
        with patch.object(mcp, "_daemon", owned), \
                patch.object(mcp, "_reachable_endpoint", return_value=None), \
                patch.object(mcp.subprocess, "Popen") as spawn:
            with self.assertRaises(RuntimeError):
                mcp._start_daemon(timeout=0)
            spawn.assert_not_called()
            self.assertIs(mcp._daemon, owned)

    def test_repeated_timeout_starts_only_one_daemon(self):
        owned = Mock()
        owned.poll.return_value = None
        with patch.object(mcp, "_daemon", None), \
                patch.object(mcp, "_reachable_endpoint", return_value=None), \
                patch.object(mcp.subprocess, "Popen", return_value=owned) as spawn:
            for _ in range(2):
                with self.assertRaises(RuntimeError):
                    mcp._start_daemon(timeout=0)
            self.assertEqual(spawn.call_count, 1)
            self.assertIs(mcp._daemon, owned)

    def test_delayed_endpoint_reuses_owned_daemon(self):
        owned = Mock()
        owned.poll.return_value = None
        endpoint = ("127.0.0.1", 12345)
        with patch.object(mcp, "_daemon", owned), \
                patch.object(mcp, "_reachable_endpoint", side_effect=[None, endpoint]), \
                patch.object(mcp.subprocess, "Popen") as spawn:
            self.assertEqual(mcp._start_daemon(), endpoint)
            spawn.assert_not_called()

    def test_exited_owned_daemon_can_be_replaced(self):
        old = Mock()
        old.poll.return_value = 1
        new = Mock()
        new.poll.return_value = None
        endpoint = ("127.0.0.1", 12345)
        with patch.object(mcp, "_daemon", old), \
                patch.object(mcp, "_reachable_endpoint", side_effect=[None, endpoint]), \
                patch.object(mcp.subprocess, "Popen", return_value=new) as spawn:
            self.assertEqual(mcp._start_daemon(), endpoint)
            spawn.assert_called_once()
            self.assertIs(mcp._daemon, new)


if __name__ == "__main__":
    unittest.main()
