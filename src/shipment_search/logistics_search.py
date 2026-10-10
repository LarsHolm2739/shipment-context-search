from dataclasses import dataclass
from math import sqrt

from .infrai_gateway import AIGateway


@dataclass(frozen=True)
class ShipmentDocument:
    document_id: str
    shipment_id: str
    event: str
    occurred_at: str
    details: str
    proof_of_delivery: str | None = None

    def search_text(self) -> str:
        pod = self.proof_of_delivery or "none"
        return (
            f"shipment {self.shipment_id}; event {self.event}; "
            f"time {self.occurred_at}; details {self.details}; proof of delivery {pod}"
        )


@dataclass(frozen=True)
class SearchHit:
    document: ShipmentDocument
    score: float


@dataclass(frozen=True)
class ExceptionAnswer:
    shipment_id: str
    disposition: str
    advice: str
    evidence_ids: list[str]


class LogisticsSearch:
    def __init__(self, ai: AIGateway) -> None:
        self.ai = ai
        self._documents: list[ShipmentDocument] = []
        self._vectors: list[list[float]] = []

    def index(self, documents: list[ShipmentDocument]) -> int:
        vectors = self.ai.embed([document.search_text() for document in documents])
        if len(vectors) != len(documents):
            raise ValueError("Embedding count does not match document count")
        self._documents.extend(documents)
        self._vectors.extend(vectors)
        return len(documents)

    def search(self, query: str, limit: int = 3) -> list[SearchHit]:
        if not self._documents:
            return []
        query_vector = self.ai.embed([query])[0]
        ranked = sorted(
            (
                SearchHit(document=document, score=_cosine(query_vector, vector))
                for document, vector in zip(self._documents, self._vectors, strict=True)
            ),
            key=lambda hit: hit.score,
            reverse=True,
        )
        return ranked[:limit]

    def handle_exception(self, shipment_id: str, question: str) -> ExceptionAnswer:
        hits = [
            hit for hit in self.search(f"shipment {shipment_id}: {question}", limit=5)
            if hit.document.shipment_id == shipment_id
        ]
        if not hits:
            raise LookupError(f"No indexed records for shipment {shipment_id}")

        delivered = any(hit.document.event == "delivered" for hit in hits)
        has_proof = any(hit.document.proof_of_delivery for hit in hits)
        disposition = "review_delivery_proof" if delivered and has_proof else "escalate_carrier"
        context = "\n".join(hit.document.search_text() for hit in hits)
        advice = self.ai.advise(question, context)
        return ExceptionAnswer(
            shipment_id=shipment_id,
            disposition=disposition,
            advice=advice,
            evidence_ids=[hit.document.document_id for hit in hits],
        )


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Embedding dimensions differ")
    magnitude = sqrt(sum(value * value for value in left)) * sqrt(
        sum(value * value for value in right)
    )
    return sum(a * b for a, b in zip(left, right, strict=True)) / magnitude if magnitude else 0.0
