from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.errors import EmailTaken, InvalidCredentials, NotFound, install_error_handlers

app = FastAPI()
install_error_handlers(app)


@app.get("/conflict")
def conflict():
    raise EmailTaken()


@app.get("/unauthorized")
def unauthorized():
    raise InvalidCredentials()


@app.get("/missing")
def missing():
    raise NotFound("Session not found")


client = TestClient(app)


def test_conflict_maps_to_409():
    response = client.get("/conflict")
    assert response.status_code == 409
    assert response.json() == {
        "detail": "An account with this email already exists.",
        "code": "email_taken",
    }


def test_unauthorized_sets_www_authenticate():
    response = client.get("/unauthorized")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_custom_message():
    response = client.get("/missing")
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"
