"""The Engine seam contract: a fake engine satisfies it; results carry usage."""

from __future__ import annotations

from ww_llm.base import CompletionRequest, CompletionResult, Engine, Usage


class FakeEngine:
    name = "fake"

    def complete(self, req: CompletionRequest) -> CompletionResult:
        return CompletionResult(
            text="ok",
            usage=Usage(tokens_in=10, tokens_out=5, cost_usd=0.0),
            engine=self.name,
            json={"echo": req.prompt} if req.response_schema else None,
        )


def test_fake_engine_satisfies_protocol():
    assert isinstance(FakeEngine(), Engine)


def test_complete_returns_usage_and_engine():
    res = FakeEngine().complete(CompletionRequest(prompt="hi"))
    assert res.text == "ok"
    assert res.engine == "fake"
    assert res.usage.tokens_in == 10 and res.usage.tokens_out == 5


def test_response_schema_yields_json():
    res = FakeEngine().complete(
        CompletionRequest(prompt="x", response_schema={"type": "object"})
    )
    assert res.json == {"echo": "x"}
