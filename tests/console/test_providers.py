from supervisor.adapters.providers import (
    BaseModelProvider,
    get_provider,
    list_providers,
    _derive_provider,
)


class TestGetProvider:
    def test_base_provider(self) -> None:
        p = get_provider("openai")
        assert isinstance(p, BaseModelProvider)
        assert p.name == "openai"
        assert p.use_mock is True


class TestListProviders:
    def test_returns_names(self) -> None:
        names = list_providers()
        assert "openai" in names
        assert "anthropic" in names
        assert "gemini" in names
        assert "litellm" in names
        assert "openrouter" in names
        assert "ollama" in names
        assert "lmstudio" in names
        assert "openai-compatible" in names


class TestDeriveProvider:
    def test_direct_match(self) -> None:
        assert _derive_provider("gpt-4o") == "openai"

    def test_openrouter_prefix(self) -> None:
        assert _derive_provider("openrouter/gpt-4o") == "openrouter"

    def test_claude(self) -> None:
        assert _derive_provider("claude-3.5-sonnet") == "anthropic"

    def test_gemini(self) -> None:
        assert _derive_provider("gemini-1.5-pro") == "gemini"

    def test_ollama(self) -> None:
        assert _derive_provider("ollama/llama3") == "ollama"

    def test_lmstudio(self) -> None:
        assert _derive_provider("lmstudio/local-model") == "lmstudio"

    def test_litellm_prefix(self) -> None:
        assert _derive_provider("litellm/gpt-4o") == "litellm"

    def test_fallback_openai(self) -> None:
        assert _derive_provider("some-unknown-model") == "openai"


class TestBaseProviderMock:
    def test_complete_returns_string(self) -> None:
        p = get_provider("openai")
        result = p.complete("gpt-4o", "Hello", max_output_tokens=10)
        assert isinstance(result.content, str)
        assert len(result.content) > 0
