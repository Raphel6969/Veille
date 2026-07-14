from supervisor.console.config import (
    VeilleSettings,
    mask_secret,
    provider_env_var,
    secret_for_provider,
)


class TestMaskSecret:
    def test_none(self) -> None:
        assert mask_secret(None) == "(not set)"

    def test_shows_last_four(self) -> None:
        m = mask_secret("sk-abc12345")
        assert m.endswith("2345")

    def test_masks_middle(self) -> None:
        m = mask_secret("sk-abc12345")
        assert m.startswith("…")
        assert len(m) < 12


class TestProviderEnvVar:
    def test_known(self) -> None:
        assert provider_env_var("openai") == "OPENAI_API_KEY"
        assert provider_env_var("anthropic") == "ANTHROPIC_API_KEY"
        assert provider_env_var("ollama") == "OLLAMA_BASE_URL"

    def test_unknown_returns_fallback(self) -> None:
        assert provider_env_var("nonexistent") == "NONEXISTENT_API_KEY"

    def test_dynamic_lookup_matches_static(self) -> None:
        """Dynamic env-var mapping should return expected values."""
        assert provider_env_var("openai") == "OPENAI_API_KEY"
        assert provider_env_var("anthropic") == "ANTHROPIC_API_KEY"
        assert provider_env_var("ollama") == "OLLAMA_BASE_URL"
        assert provider_env_var("nonexistent") == "NONEXISTENT_API_KEY"


class TestSecretForProvider:
    def test_returns_env_var_when_set(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        assert secret_for_provider("openai") == "sk-test"

    def test_returns_none_when_not_set(self) -> None:
        assert secret_for_provider("openai") is None


class TestVeilleSettingsDefaults:
    def test_all_defaults_are_off(self) -> None:
        s = VeilleSettings()
        assert s.real_mode is False
        assert s.cache_approved is False
        assert s.optimize is False
        assert s.enforce is False
        assert s.context_compression is False
        assert s.context_diversification is False

    def test_provider_default(self) -> None:
        s = VeilleSettings()
        assert s.provider == "litellm"

    def test_model_default(self) -> None:
        s = VeilleSettings()
        assert s.model == ""
