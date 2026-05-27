from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

API_URL = "https://platform.xiaomimimo.com/api/v1/tokenPlan/usage"
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
ACCOUNTS_FILE = BASE_DIR / "accounts.json"
FRONTEND_DIST_DIR = PROJECT_DIR / "frontend" / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"

app = FastAPI(title="Xiaomi Token Usage API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
if FRONTEND_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_ASSETS_DIR)), name="assets")


def load_accounts() -> list[dict[str, Any]]:
    if not ACCOUNTS_FILE.exists():
        return []
    with ACCOUNTS_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise HTTPException(status_code=500, detail="accounts.json must be an array")
    return data


@app.get("/")
def serve_index() -> FileResponse:
    index_file = FRONTEND_DIST_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=503, detail="frontend dist not found, run frontend build first")
    return FileResponse(index_file)


def save_accounts(accounts: list[dict[str, Any]]) -> None:
    with ACCOUNTS_FILE.open("w", encoding="utf-8") as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)


class CreateAccountRequest(BaseModel):
    name: str
    cookie: str
    referer: str | None = None
    timezone: str | None = None
    userAgent: str | None = None


class UpdateAccountRequest(BaseModel):
    name: str
    cookie: str
    referer: str | None = None
    timezone: str | None = None
    userAgent: str | None = None


def find_account(account_id: str) -> dict[str, Any]:
    accounts = load_accounts()
    for item in accounts:
        if item.get("id") == account_id:
            return item
    raise HTTPException(status_code=404, detail="Account not found")


def format_usage(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") or {}
    usage = data.get("usage") or {}
    month_usage = data.get("monthUsage") or {}

    usage_items = usage.get("items") or []
    month_items = month_usage.get("items") or []

    def pick(items: list[dict[str, Any]], name: str) -> dict[str, Any]:
        for row in items:
            if row.get("name") == name:
                return row
        return {"name": name, "used": 0, "limit": 0, "percent": 0}

    plan = pick(usage_items, "plan_total_token")
    compensation = pick(usage_items, "compensation_total_token")
    month_plan = pick(month_items, "month_total_token")

    return {
        "monthUsage": {
            "percent": month_usage.get("percent", 0),
            "items": month_items,
            "monthPlan": month_plan,
        },
        "usage": {
            "percent": usage.get("percent", 0),
            "items": usage_items,
            "plan": plan,
            "compensation": compensation,
        },
    }


@app.get("/api/accounts")
def get_accounts() -> dict[str, Any]:
    accounts = load_accounts()
    safe_accounts = [{"id": x.get("id"), "name": x.get("name")} for x in accounts]
    return {"data": safe_accounts}


@app.post("/api/accounts")
def create_account(payload: CreateAccountRequest) -> dict[str, Any]:
    name = payload.name.strip()
    cookie = payload.cookie.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Account name is required")
    if not cookie:
        raise HTTPException(status_code=400, detail="Account cookie is required")

    accounts = load_accounts()
    if any((item.get("name") or "").strip() == name for item in accounts):
        raise HTTPException(status_code=400, detail="Account name already exists")

    account = {
        "id": str(uuid4()),
        "name": name,
        "cookie": cookie,
        "referer": (payload.referer or "").strip() or "https://platform.xiaomimimo.com/console/plan-manage",
        "timezone": (payload.timezone or "").strip() or "Asia/Shanghai",
        "userAgent": (payload.userAgent or "").strip()
        or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    }

    accounts.append(account)
    save_accounts(accounts)
    return {"data": {"id": account["id"], "name": account["name"]}}


@app.put("/api/accounts/{account_id}")
def update_account(account_id: str, payload: UpdateAccountRequest) -> dict[str, Any]:
    name = payload.name.strip()
    cookie = payload.cookie.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Account name is required")
    if not cookie:
        raise HTTPException(status_code=400, detail="Account cookie is required")

    accounts = load_accounts()
    target_idx = -1
    for idx, item in enumerate(accounts):
        if item.get("id") == account_id:
            target_idx = idx
            break

    if target_idx == -1:
        raise HTTPException(status_code=404, detail="Account not found")

    if any((item.get("name") or "").strip() == name and item.get("id") != account_id for item in accounts):
        raise HTTPException(status_code=400, detail="Account name already exists")

    updated = dict(accounts[target_idx])
    updated["name"] = name
    updated["cookie"] = cookie
    updated["referer"] = (payload.referer or "").strip() or updated.get("referer") or "https://platform.xiaomimimo.com/console/plan-manage"
    updated["timezone"] = (payload.timezone or "").strip() or updated.get("timezone") or "Asia/Shanghai"
    updated["userAgent"] = (payload.userAgent or "").strip() or updated.get("userAgent") or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"

    accounts[target_idx] = updated
    save_accounts(accounts)
    return {"data": {"id": updated["id"], "name": updated["name"]}}


@app.get("/api/usage")
async def get_usage(accountId: str = Query(..., min_length=1)) -> dict[str, Any]:
    account = find_account(accountId)
    cookie = (account.get("cookie") or "").strip()
    if not cookie:
        raise HTTPException(status_code=400, detail="Account cookie is empty")

    headers = {
        "accept": "*/*",
        "accept-language": "zh",
        "content-type": "application/json",
        "cookie": cookie,
        "referer": account.get("referer") or "https://platform.xiaomimimo.com/console/plan-manage",
        "user-agent": account.get("userAgent")
        or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "x-timezone": account.get("timezone") or "Asia/Shanghai",
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(API_URL, headers=headers)
            resp.raise_for_status()
            upstream = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {e}") from e

    if upstream.get("code") != 0:
        raise HTTPException(
            status_code=502,
            detail=f"Upstream returned code={upstream.get('code')}, message={upstream.get('message', '')}",
        )

    return {"data": format_usage(upstream)}
