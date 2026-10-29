import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

base = "http://localhost:8000"


def req(method, path, data=None, token=None, params=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if params:
        path = path + ("&" if "?" in path else "?") + urllib.parse.urlencode(params)
    body = None if data is None else json.dumps(data).encode()
    request = urllib.request.Request(base + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request) as resp:
        raw = resp.read().decode()
        return resp.status, json.loads(raw) if raw else None



def main() -> None:
    print("health", req("GET", "/health")[1])
    _, login = req(
        "POST",
        "/api/v1/auth/login",
        {"username": "admin", "password": "ChangeMeAdmin123!"},
    )
    token = login["access_token"]
    print("login ok", "token_len", len(token))

    _, wells = req("GET", "/api/v1/wells", token=token)
    print("wells total", wells["total"], "first", wells["items"][0]["name"])
    wid = wells["items"][0]["id"]

    _, dash = req("GET", "/api/v1/dashboard", token=token)
    print("dashboard alerts", dash["active_alerts"], "wells", dash["total_wells"])

    _, detail = req("GET", f"/api/v1/wells/{wid}", token=token)
    print("detail", detail["name"], "has_pred", bool(detail.get("latest_prediction")))

    now = datetime.now(timezone.utc)
    frm = (now - timedelta(days=2)).isoformat()
    to = now.isoformat()
    _, series = req(
        "GET",
        f"/api/v1/telemetry/wells/{wid}",
        token=token,
        params={
            "date_from": frm,
            "date_to": to,
            "parameters": "temperature,vibration",
        },
    )
    print("telemetry series", len(series), "points", sum(len(s["points"]) for s in series))

    _, an = req("POST", f"/api/v1/analytics/run?well_id={wid}", token=token)
    print("analytics", an)

    _, preds = req("GET", f"/api/v1/analytics/predictions?well_id={wid}", token=token)
    print(
        "predictions",
        len(preds),
        "p",
        preds[0]["failure_probability"] if preds else None,
    )

    _, alerts = req("GET", "/api/v1/alerts?page=1&page_size=5", token=token)
    print("alerts total", alerts["total"])

    _, report = req(
        "POST",
        "/api/v1/reports",
        {
            "report_type": "fund_summary",
            "period_start": (now - timedelta(days=7)).isoformat(),
            "period_end": now.isoformat(),
            "export_format": "json",
        },
        token=token,
    )
    print("report", report["id"], report["title"])

    _, vlogin = req(
        "POST",
        "/api/v1/auth/login",
        {"username": "viewer", "password": "ViewerDemo123!"},
    )
    vtoken = vlogin["access_token"]
    try:
        req("POST", "/api/v1/analytics/run", token=vtoken)
        print("viewer_write UNEXPECTED OK")
    except urllib.error.HTTPError as exc:
        print("viewer_write blocked", exc.code)

    print("E2E_OK")

if __name__ == "__main__":
    main()
