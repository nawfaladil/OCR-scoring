"""
We use the testing database for tests instead of real data, and we clean it after usage
"""
import os
import json
import asyncio
import pytest
from fastapi.testclient import TestClient
from main_tool.core.api.app import app
from main_tool.core.database.db_test import get_user_db, Base
from tests.db_forTest import create_db_and_tables, get_user_db_override, engine_test

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    asyncio.run(create_db_and_tables())
    yield
    async def do_drop():
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    asyncio.run(do_drop())
    try:
        os.remove("./test_tmp.db")
    except Exception:
        pass

app.dependency_overrides[get_user_db] = get_user_db_override
client = TestClient(app)

def test_get_config_unauthenticated():
    resp = client.get("/config")
    assert resp.status_code == 401

def test_register_and_get_config():
    # make a user for testing, login and get its config
    user_data = {"email": "testuser@example.com", "password": "mysecurepassword"}
    resp = client.post("/auth/register", json=user_data)
    assert resp.status_code == 201
    resp = client.post("/auth/jwt/login",
                       data={"username": user_data["email"], "password": user_data["password"]})
    assert resp.status_code == 204
    cookies = resp.cookies.get("fastapiusersauth")
    resp = client.get("/config", cookies={"fastapiusersauth": cookies})
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)

def test_registration_password_too_short():
    # password should be rejected (too short)
    user_data = {"email": "shortpwd@example.com", "password": "short"}
    resp = client.post("/auth/register", json=user_data)
    assert resp.status_code == 400 or resp.status_code == 422
    assert "Password should be at least 8 characters" in resp.text

def test_registration_password_contains_email():
    # password with the email should be rejected
    email = "emailinpwd@example.com"
    user_data = {"email": email, "password": f"12345678{email}"}
    resp = client.post("/auth/register", json=user_data)
    assert resp.status_code == 400 or resp.status_code == 422
    assert "Password should not contain e-mail" in resp.text

def test_false_login():
    # Try to login with an incorrect password
    user_data = {"email": "willfail@example.com", "password": "goodpassword"}
    # Register first
    resp = client.post("/auth/register", json=user_data)
    assert resp.status_code == 201
    # Use wrong password
    resp = client.post("/auth/jwt/login",
                       data={"username": user_data["email"], "password": "wrongpassword"})
    assert resp.status_code == 400 or resp.status_code == 401

def test_evaluate_endpoint(tmp_path):
    """
    This assumes you have a test GT file and predictions ZIP available locally, provide their path
    """
    user_data = {"email": "evaluser@example.com", "password": "evaluategood"}
    resp = client.post("/auth/register", json=user_data)
    assert resp.status_code == 201
    resp = client.post("/auth/jwt/login",
                       data={"username": user_data["email"], "password": user_data["password"]})
    assert resp.status_code == 204
    cookies = resp.cookies.get("fastapiusersauth")

    # You must provide correct local paths to your test files
    gt_path = "data/GT/PISTE AUDIT DOSSIERS TESTS (1).xlsx"
    predictions_path = "data/april_layout.zip"
    assert os.path.exists(gt_path), "Ground truth file not found for test"
    assert os.path.exists(predictions_path), "Predictions ZIP file not found for test"

    # Get config
    resp_config = client.get("/config", cookies={"fastapiusersauth": cookies})
    assert resp_config.status_code == 200
    config = resp_config.json()

    data = {
        "config": json.dumps(config)
    }
    with open(gt_path, "rb") as gt_file, open(predictions_path, "rb") as pred_file:
        files = {
            "ground_truth": ("gt_test.xlsx", gt_file,
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            "predictions": ("predictions_test.zip",pred_file, "application/zip")
        }
        resp_eval = client.post(
            "/evaluate/",
            data={"config": json.dumps(config)},
            files=files,
            cookies={"fastapiusersauth": cookies}
        )
    assert resp_eval.status_code == 200, f"Failed evaluation: {resp_eval.text}"
    # Optionally check the response content type
    assert resp_eval.headers['content-type'].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
