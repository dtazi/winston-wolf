"""The Drafter seam contract (FR-015): anything satisfying the Protocol works;
the named-account guard is code-enforced."""

from ww_engine.drafting.base import (
    DraftRequest,
    DraftResult,
    Drafter,
    violates_named_account_guard,
)


class FakeDrafter:
    def draft(self, req: DraftRequest) -> DraftResult:
        return DraftResult(
            subject=f"Touch {req.touch_number}",
            body_text=f"Re: {req.value_angle}",
            message_recipe={"angle": req.value_angle, "touch": req.touch_number},
            token_usage=[{"stage": "drafting", "model": "fake",
                          "input_tokens": 1, "output_tokens": 1}],
        )


def test_fake_drafter_satisfies_protocol_and_contract():  # happy path
    d: Drafter = FakeDrafter()
    req = DraftRequest(lead={}, pitch={}, brief_excerpt={},
                       value_angle="china_plus_one", touch_number=2,
                       personalization={"level": "dataset", "facts": ["x"]})
    res = d.draft(req)
    assert res.subject and res.body_text
    assert res.message_recipe["angle"] == "china_plus_one"
    assert res.token_usage[0]["stage"] == "drafting"


def test_named_account_guard_blocks_ikea():  # error path (FR-013)
    assert violates_named_account_guard("we supply IKEA globally") is True
    assert violates_named_account_guard("we supply major retailers") is False
