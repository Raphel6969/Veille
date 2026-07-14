from supervisor.adapters.providers import (
    BaseModelProvider,
    _derive_provider,
    get_provider,
    list_providers,
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


class TestIndividualProviderClasses:
    """Every provider class should have correct name, api_key_env, and mock mode."""

    def _check_provider(self, name: str, expected_env: str) -> None:
        from supervisor.adapters.providers import (
            AnthropicProvider,
            GeminiProvider,
            LiteLLMProvider,
            LMStudioProvider,
            OpenAIProvider,
            OpenRouterProvider,
        )

        cls_map = {
            "openai": OpenAIProvider,
            "litellm": LiteLLMProvider,
            "openrouter": OpenRouterProvider,
            "anthropic": AnthropicProvider,
            "gemini": GeminiProvider,
            "lmstudio": LMStudioProvider,
        }
        cls = cls_map.get(name)
        if cls is None:
            return
        inst = cls(use_mock=True)
        assert inst.name == name
        assert inst.api_key_env == expected_env
        assert inst.use_mock is True
        result = inst.complete("mock-synthesis", "test prompt")
        assert result.content.startswith("[mock response from")

    def test_openai_provider(self) -> None:
        self._check_provider("openai", "OPENAI_API_KEY")

    def test_litellm_provider(self) -> None:
        self._check_provider("litellm", "OPENAI_API_KEY")

    def test_openrouter_provider(self) -> None:
        self._check_provider("openrouter", "OPENROUTER_API_KEY")

    def test_anthropic_provider(self) -> None:
        self._check_provider("anthropic", "ANTHROPIC_API_KEY")

    def test_gemini_provider(self) -> None:
        self._check_provider("gemini", "GEMINI_API_KEY")

    def test_lmstudio_provider(self) -> None:
        self._check_provider("lmstudio", "LMSTUDIO_BASE_URL")
