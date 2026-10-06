def test_owner_cookie_survives_browser_restart_for_saved_creation_resume(client):
    response = client.get("/api/creations")
    cookie = response.headers["Set-Cookie"]
    assert "Expires=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    with client.session_transaction() as session:
        assert session.permanent
