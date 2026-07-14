from supervisor.console.connections import list_connections, validate_connection


class TestListConnections:
    def test_returns_all_providers(self) -> None:
        conns = list_connections(real_mode=False)
        names = {c.provider for c in conns}
        assert "openai" in names
        assert "anthropic" in names
        assert all(c.masked_key is not None for c in conns)

    def test_mock_mode_status(self) -> None:
        conns = list_connections(real_mode=False)
        for c in conns:
            assert c.status in ("mock", "real-missing")


class TestValidateConnection:
    def test_mock_mode_ok(self) -> None:
        ok, reason = validate_connection("openai", real=False)
        assert ok is True
        assert "mock" in reason.lower()

    def test_real_missing_credentials_ok_in_mock(self) -> None:
        ok, reason = validate_connection("openai", real=False)
        assert ok is True
