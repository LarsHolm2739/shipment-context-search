from collections.abc import Sequence

from shipment_search.logistics_search import LogisticsSearch, ShipmentDocument


class DeterministicAI:
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[1.0, 0.0] if "SHP-42" in text else [0.0, 1.0] for text in texts]

    def advise(self, question: str, context: str) -> str:
        assert "Address inaccessible" in context
        return "Confirm the receiving window. Ask the carrier to attempt delivery again."


def test_exception_without_delivery_proof_escalates_carrier() -> None:
    search = LogisticsSearch(DeterministicAI())
    search.index(
        [
            ShipmentDocument(
                document_id="event-42",
                shipment_id="SHP-42",
                event="delivery_exception",
                occurred_at="2026-09-05T09:30:00Z",
                details="Address inaccessible; parcel remains with carrier.",
            )
        ]
    )

    answer = search.handle_exception("SHP-42", "What should operations do next?")

    assert answer.disposition == "escalate_carrier"
    assert answer.evidence_ids == ["event-42"]
    assert "attempt delivery again" in answer.advice
