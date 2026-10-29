from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


def test_login_success(client: TestClient):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "ChangeMeAdmin123!"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_failure(client: TestClient):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_viewer_cannot_write(client: TestClient):
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "viewer", "password": "ViewerDemo123!"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    wells = client.get("/api/v1/wells", headers=headers)
    assert wells.status_code == 200
    well_id = wells.json()["items"][0]["id"]
    ingest = client.post(
        "/api/v1/telemetry",
        headers=headers,
        json={
            "well_id": well_id,
            "points": [
                {
                    "parameter_code": "temperature",
                    "value": 70,
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        },
    )
    assert ingest.status_code == 403


def test_wells_list_and_detail(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/wells", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    well_id = body["items"][0]["id"]
    detail = client.get(f"/api/v1/wells/{well_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["name"]


def test_telemetry_ingest_and_query(client: TestClient, auth_headers: dict):
    wells = client.get("/api/v1/wells", headers=auth_headers).json()["items"]
    well_id = wells[0]["id"]
    ts = datetime.now(timezone.utc)
    ingest = client.post(
        "/api/v1/telemetry",
        headers=auth_headers,
        json={
            "well_id": well_id,
            "batch_id": "test-batch-1",
            "points": [
                {
                    "parameter_code": "temperature",
                    "value": 75.5,
                    "recorded_at": ts.isoformat(),
                    "idempotency_key": "t1",
                }
            ],
        },
    )
    assert ingest.status_code == 200
    assert ingest.json()["accepted"] >= 1

    # duplicate
    again = client.post(
        "/api/v1/telemetry",
        headers=auth_headers,
        json={
            "well_id": well_id,
            "batch_id": "test-batch-1",
            "points": [
                {
                    "parameter_code": "temperature",
                    "value": 75.5,
                    "recorded_at": ts.isoformat(),
                    "idempotency_key": "t1",
                }
            ],
        },
    )
    assert again.status_code == 200
    assert again.json()["skipped_duplicates"] >= 1

    series = client.get(
        f"/api/v1/telemetry/wells/{well_id}",
        headers=auth_headers,
        params={
            "date_from": (ts - timedelta(hours=1)).isoformat(),
            "date_to": (ts + timedelta(hours=1)).isoformat(),
            "parameters": "temperature",
        },
    )
    assert series.status_code == 200
    assert isinstance(series.json(), list)


def test_events_and_analytics_alerts_reports(client: TestClient, auth_headers: dict):
    wells = client.get("/api/v1/wells", headers=auth_headers).json()["items"]
    well_id = wells[0]["id"]

    failure = client.post(
        "/api/v1/events/failures",
        headers=auth_headers,
        json={
            "well_id": well_id,
            "failure_type": "Тестовый отказ",
            "severity": "medium",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "description": "pytest",
        },
    )
    assert failure.status_code == 201

    analytics = client.post(
        "/api/v1/analytics/run",
        headers=auth_headers,
        params={"well_id": well_id},
    )
    assert analytics.status_code == 200
    body = analytics.json()
    assert "wells_processed" in body

    preds = client.get(
        "/api/v1/analytics/predictions",
        headers=auth_headers,
        params={"well_id": well_id},
    )
    assert preds.status_code == 200

    alerts = client.get("/api/v1/alerts", headers=auth_headers)
    assert alerts.status_code == 200

    report = client.post(
        "/api/v1/reports",
        headers=auth_headers,
        json={
            "report_type": "fund_summary",
            "period_start": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
            "period_end": datetime.now(timezone.utc).isoformat(),
            "export_format": "json",
        },
    )
    assert report.status_code == 201
    rid = report.json()["id"]
    got = client.get(f"/api/v1/reports/{rid}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["content_json"] is not None


def test_missing_well(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/wells/999999", headers=auth_headers)
    assert resp.status_code == 404
