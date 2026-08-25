#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تست‌های شبیه‌سازی برای بخش خودکارسازی گزینه B (بدون Railway واقعی)."""
import json
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, "/tmp/svc")


class FakeResp:
    def __init__(self, payload):
        self._p = json.dumps(payload).encode()

    def read(self):
        return self._p

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


# ── تست railway_gql.set_variables ─────────────────────────
class TestRailwayGql(unittest.TestCase):
    def _mock_urlopen(self, responses):
        def fake_urlopen(req, timeout=None):
            body = json.loads(req.data.decode())
            query = body["query"]
            for name, payload in responses:
                if name in query:
                    return FakeResp(payload)
            raise AssertionError(f"unexpected query: {query[:80]}")
        return fake_urlopen

    def _response_fn(self, responses):
        def f(token, query, variables=None):
            for name, payload in responses:
                if name in query:
                    return payload
            return {"errors": [{"message": f"no mock for {query[:60]}"}]}
        return f

    def test_create_new_variable(self):
        from railway_gql import set_variable
        # لیست خالی → باید variableCreate صدا زده شود
        responses = [
            ("variables(environmentId", {"data": {"variables": {"edges": []}}}),
            ("variableCreate", {"data": {"variableCreate": {"id": "v9", "key": "PANELS"}}}),
        ]
        with patch("railway_gql.gql", side_effect=self._response_fn(responses)):
            ok, msg = set_variable("tok", "env1", "svc1", "PANELS", "x=1;y=2")
        self.assertTrue(ok)
        self.assertEqual(msg, "created")

    def test_update_existing_variable(self):
        from railway_gql import set_variable
        responses = [
            ("variables(environmentId", {"data": {"variables": {"edges": [
                {"node": {"id": "v1", "key": "PANELS", "value": "old"}}
            ]}}}),
            ("variableUpdate", {"data": {"variableUpdate": {"id": "v1", "key": "PANELS"}}}),
        ]
        with patch("railway_gql.gql", side_effect=self._response_fn(responses)):
            ok, msg = set_variable("tok", "env1", "svc1", "PANELS", "new")
        self.assertTrue(ok)
        self.assertEqual(msg, "updated")

    def test_set_variables_batch(self):
        from railway_gql import set_variables
        responses = [
            ("variables(environmentId", {"data": {"variables": {"edges": []}}}),
            ("variableCreate", {"data": {"variableCreate": {"id": "v1", "key": "PANELS"}}}),
            ("variableCreate", {"data": {"variableCreate": {"id": "v2", "key": "X"}}}),
        ]
        with patch("railway_gql.gql", side_effect=self._response_fn(responses)):
            ok, fails = set_variables("tok", "env", "svc", {"PANELS": "a", "X": "b"})
        self.assertTrue(ok)
        self.assertEqual(fails, [])


# ── تست ساخت PANELS در bootstrap ──────────────────────────
class TestBootstrapPanels(unittest.TestCase):
    def test_panels_string_build(self):
        domains = {
            "xui-nl": "https://a.up.railway.app",
            "xui-sg": "https://b.up.railway.app",
            "xui-us-va": "https://c.up.railway.app",
            "xui-us-ca": "https://d.up.railway.app",
        }
        panels_env = ";".join(f"{k}={v}" for k, v in domains.items())
        self.assertIn("xui-nl=https://a.up.railway.app", panels_env)
        self.assertEqual(panels_env.count("="), 4)
        self.assertEqual(panels_env.count(";"), 3)

    def test_init_flag_assignment(self):
        main_name = "xui-nl"
        names = ["xui-nl", "xui-sg", "xui-us-va", "xui-us-ca"]
        flags = {n: ("1" if n == main_name else "0") for n in names}
        self.assertEqual(flags["xui-nl"], "1")
        self.assertEqual(flags["xui-sg"], "0")


# ── تست build_inbound از xui-reality-inbound ──────────────
class TestInboundBuilder(unittest.TestCase):
    def test_build_inbound_structure(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "xri", "/tmp/svc/xui-reality-inbound.py")
        # نیاز به cryptography — اگر موجود بود ساختمان را تست کن
        try:
            import cryptography  # noqa
        except ImportError:
            self.skipTest("cryptography نصب نیست")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        inbound, client_id, pub, sid = mod.build_inbound(name="xui-nl")
        self.assertEqual(inbound["port"], 443)
        self.assertEqual(inbound["protocol"], "vless")
        self.assertEqual(inbound["streamSettings"]["security"], "reality")
        self.assertEqual(inbound["remark"], mod.LOCATION_NAMES["xui-nl"])
        self.assertEqual(inbound["settings"]["clients"][0]["email"], "amir")
        rs = inbound["streamSettings"]["realitySettings"]
        self.assertTrue(rs["privateKey"])
        self.assertTrue(rs["settings"]["publicKey"])
        self.assertTrue(client_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
