"""Phase 3 context engine: deterministic per-step context manifests."""

from __future__ import annotations

from pydantic import BaseModel, Field

ROLE_KEYWORDS: dict[str, list[str]] = {
    "researcher": ["question", "research", "source", "competitor", "policy"],
    "analyst": ["evidence", "verif", "rubric", "constraint", "claim"],
    "writer": ["fact", "audience", "format", "brief", "draft"],
}


class ContextManifest(BaseModel):
    step_id: str
    role: str
    included: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=list)
    compressed: list[str] = Field(default_factory=list)
    estimated_tokens: int = 0
    reason: str = ""


def _estimate_tokens(text: str) -> int:
    return max(1, round(len(text.split()) / 0.75))


class ContextEngine:
    """Builds a role-sensitive context manifest from a master context.

    Deterministic: each ``slice`` is a string whose leading topic word is matched
    against role keywords. Matching slices are ``included``; non-matching long
    slices are ``compressed``; short non-matching slices are ``excluded``.
    """

    def build_manifest(self, master_context: list[str], role: str, step_id: str) -> ContextManifest:
        keywords = ROLE_KEYWORDS.get(role, ["question", "policy"])
        included: list[str] = []
        compressed: list[str] = []
        excluded: list[str] = []
        for slice_text in master_context:
            topic = slice_text.strip().split(" ", 1)[0].lower()
            if any(k in topic or k in slice_text.lower() for k in keywords):
                included.append(slice_text)
            elif len(slice_text.split()) > 20:
                compressed.append(slice_text)
            else:
                excluded.append(slice_text)
        tokens = sum(_estimate_tokens(s) for s in included + compressed)
        reason = (
            f"Role '{role}' includes {len(included)} relevant slice(s); "
            f"compressed {len(compressed)} long; excluded {len(excluded)}."
        )
        return ContextManifest(
            step_id=step_id,
            role=role,
            included=included,
            excluded=excluded,
            compressed=compressed,
            estimated_tokens=tokens,
            reason=reason,
        )
