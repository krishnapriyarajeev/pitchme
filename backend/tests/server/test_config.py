import pytest

from server.config import Settings


@pytest.fixture
def settings(monkeypatch):
    def make(**env):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        return Settings(_env_file=None)

    return make


def test_db_url_built_from_parts(settings):
    s = settings(POSTGRES_USER="u", POSTGRES_PASSWORD="p", POSTGRES_DB="d")
    assert s.db_url == "postgresql+psycopg://u:p@localhost:5432/d"


def test_database_url_wins(settings):
    s = settings(DATABASE_URL="postgresql+psycopg://a:b@db:5432/x", POSTGRES_USER="u")
    assert s.db_url == "postgresql+psycopg://a:b@db:5432/x"


def test_storage_keys_fall_back_to_minio_root(settings):
    s = settings(MINIO_ROOT_USER="root", MINIO_ROOT_PASSWORD="rootpw")
    assert s.storage_access_key == "root"
    assert s.storage_secret_key == "rootpw"


def test_storage_keys_prefer_s3_values(settings):
    s = settings(MINIO_ROOT_USER="root", S3_ACCESS_KEY="ak", S3_SECRET_KEY="sk")
    assert s.storage_access_key == "ak"
    assert s.storage_secret_key == "sk"


def test_public_urls_fall_back_to_internal(settings):
    s = settings(S3_ENDPOINT="http://localhost:9000", LIVEKIT_URL="ws://localhost:7880")
    assert s.storage_public_endpoint == "http://localhost:9000"
    assert s.livekit_client_url == "ws://localhost:7880"

    s = settings(S3_PUBLIC_ENDPOINT="http://10.0.0.5:9000", LIVEKIT_PUBLIC_URL="ws://10.0.0.5:7880")
    assert s.storage_public_endpoint == "http://10.0.0.5:9000"
    assert s.livekit_client_url == "ws://10.0.0.5:7880"


def test_cors_origins_split(settings):
    s = settings(CORS_ORIGINS="http://a.test, http://b.test")
    assert s.cors_origins == ["http://a.test", "http://b.test"]


def test_secrets_hidden_in_repr(settings):
    s = settings(JWT_SECRET="super-secret-value")
    assert "super-secret-value" not in repr(s)
