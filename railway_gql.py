#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway GraphQL helpers (shared)
================================
توابع کمکی برای تعامل با API Railway:
  - gql()                     درخواست گراف‌کیوال
  - list_variables()          لیست متغیرهای یک سرویس
  - set_variables()           ست (upsert) متغیرهای یک سرویس

این فایل هم توسط bootstrap.py (داخل کانتینر) و هم توسط deploy.py / run_all.sh
(بیرون) استفاده می‌شود تا PANELS و BOOTSTRAP_READY به سرویس‌ها تزریق شوند.
"""

import json
import os
import urllib.request

URL = "https://backboard.railway.com/graphql/v2"


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "User-Agent": "railway-cli/5.30.4",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def list_variables(token, env_id, service_id):
    """لیست متغیرهای محیطی یک سرویس در یک environment."""
    d = gql(
        token,
        """query($e: String!, $s: String!) {
            variables(environmentId: $e, serviceId: $s) {
                edges { node { id key value } }
            }
        }""",
        {"e": env_id, "s": service_id},
    )
    edges = d["data"]["variables"]["edges"]
    return {e["node"]["key"]: e["node"] for e in edges}


def set_variable(token, env_id, service_id, key, value):
    """
    ست (upsert) یک متغیر روی سرویس.
    اگر کلید از قبل باشد آپدیت می‌شود وگرنه ساخته می‌شود.
    برمی‌گرداند: (ok, message)
    """
    existing = list_variables(token, env_id, service_id)
    node = existing.get(key)
    if node:
        # آپدیت — دو نام mutation را امتحان کن
        d = gql(
            token,
            """mutation($id: String!, $value: String!) {
                variableUpdate(id: $id, value: $value) { id key }
            }""",
            {"id": node["id"], "value": value},
        )
        if not d.get("errors"):
            return True, "updated"
        d = gql(
            token,
            """mutation($e: String!, $s: String!, $key: String!, $value: String!) {
                serviceVariablesUpdate(serviceId: $s, environmentId: $e,
                                       variables: { key: $key, value: $value }) { id }
            }""",
            {"e": env_id, "s": service_id, "key": key, "value": value},
        )
        err = d.get("errors")
        return (False, err[0]["message"]) if err else (True, "updated")
    # ساخت — دو نام mutation را امتحان کن
    d = gql(
        token,
        """mutation($e: String!, $s: String!, $key: String!, $value: String!) {
            variableCreate(environmentId: $e, serviceId: $s, key: $key, value: $value) { id key }
        }""",
        {"e": env_id, "s": service_id, "key": key, "value": value},
    )
    if not d.get("errors"):
        return True, "created"
    d = gql(
        token,
        """mutation($e: String!, $s: String!, $key: String!, $value: String!) {
            serviceVariablesCreate(serviceId: $s, environmentId: $e,
                                   variables: { key: $key, value: $value }) { id }
        }""",
        {"e": env_id, "s": service_id, "key": key, "value": value},
    )
    err = d.get("errors")
    return (False, err[0]["message"]) if err else (True, "created")


def set_variables(token, env_id, service_id, pairs):
    """ست چند متغیر یکجا. برمی‌گرداند: (ok, list_of_failures)"""
    failures = []
    ok = True
    for key, value in pairs.items():
        s, msg = set_variable(token, env_id, service_id, key, value)
        if not s:
            ok = False
            failures.append(f"{key}: {msg}")
    return ok, failures
