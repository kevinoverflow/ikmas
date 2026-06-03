from app.backend import auth, sqlite_store


def test_create_and_authenticate_user(tmp_path, monkeypatch):
    monkeypatch.setattr(sqlite_store, "DB_PATH", tmp_path / "ikmas.db")

    user = auth.create_user("Ada Lovelace", "ADA@example.com", "password123")

    assert user.name == "Ada Lovelace"
    assert user.email == "ada@example.com"
    assert user.user_id

    authenticated = auth.authenticate_user("ada@example.com", "password123")

    assert authenticated == user
    assert auth.authenticate_user("ada@example.com", "wrong-password") is None


def test_create_user_rejects_duplicate_email(tmp_path, monkeypatch):
    monkeypatch.setattr(sqlite_store, "DB_PATH", tmp_path / "ikmas.db")

    auth.create_user("Ada Lovelace", "ada@example.com", "password123")

    try:
        auth.create_user("Another Ada", "ADA@example.com", "password456")
    except auth.AuthError as e:
        assert "already exists" in str(e)
    else:
        raise AssertionError("Expected duplicate email to raise AuthError")


def test_auth_migrates_existing_users_table(tmp_path, monkeypatch):
    db_path = tmp_path / "ikmas.db"
    monkeypatch.setattr(sqlite_store, "DB_PATH", db_path)

    with sqlite_store.get_conn() as conn:
        conn.execute("CREATE TABLE users (user_id TEXT PRIMARY KEY, profile_json TEXT)")

    user = auth.create_user("Grace Hopper", "grace@example.com", "password123")

    assert auth.authenticate_user("grace@example.com", "password123") == user


def test_auth_session_round_trip_stores_only_token_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(sqlite_store, "DB_PATH", tmp_path / "ikmas.db")
    user = auth.create_user("Katherine Johnson", "katherine@example.com", "password123")

    raw_token = auth.create_auth_session(user.user_id)
    restored = auth.authenticate_session_token(raw_token)

    assert restored == user
    with sqlite_store.get_conn() as conn:
        row = conn.execute("SELECT token_hash FROM auth_sessions").fetchone()

    assert row["token_hash"] == auth.hash_session_token(raw_token)
    assert row["token_hash"] != raw_token


def test_auth_session_rejects_revoked_token(tmp_path, monkeypatch):
    monkeypatch.setattr(sqlite_store, "DB_PATH", tmp_path / "ikmas.db")
    user = auth.create_user("Dorothy Vaughan", "dorothy@example.com", "password123")
    raw_token = auth.create_auth_session(user.user_id)

    auth.revoke_auth_session(raw_token)

    assert auth.authenticate_session_token(raw_token) is None


def test_auth_session_rejects_expired_token(tmp_path, monkeypatch):
    monkeypatch.setattr(sqlite_store, "DB_PATH", tmp_path / "ikmas.db")
    user = auth.create_user("Mary Jackson", "mary@example.com", "password123")
    raw_token = auth.create_auth_session(user.user_id, ttl_days=-1)

    assert auth.authenticate_session_token(raw_token) is None
