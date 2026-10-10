from functools import lru_cache
from typing import Literal

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from .infrai_gateway import InfraiGateway
from .logistics_search import LogisticsSearch, ShipmentDocument


class ShipmentEventRequest(BaseModel):
    document_id: str = Field(min_length=1)
    shipment_id: str = Field(min_length=1)
    event: Literal["picked_up", "in_transit", "delivery_exception", "delivered"]
    occurred_at: str = Field(min_length=1)
    details: str = Field(min_length=1)
    proof_of_delivery: str | None = None


class IndexResponse(BaseModel):
    indexed: int


class ExceptionRequest(BaseModel):
    shipment_id: str = Field(min_length=1)
    question: str = Field(min_length=1)


class ExceptionResponse(BaseModel):
    shipment_id: str
    disposition: Literal["review_delivery_proof", "escalate_carrier"]
    advice: str
    evidence_ids: list[str]


app = FastAPI(title="Shipment context search")


@lru_cache
def get_search() -> LogisticsSearch:
    return LogisticsSearch(InfraiGateway())


@app.post("/documents", response_model=IndexResponse)
def index_documents(
    requests: list[ShipmentEventRequest], search: LogisticsSearch = Depends(get_search)
) -> IndexResponse:
    documents = [ShipmentDocument(**request.model_dump()) for request in requests]
    return IndexResponse(indexed=search.index(documents))


@app.post("/exceptions/resolve", response_model=ExceptionResponse)
def resolve_exception(
    request: ExceptionRequest, search: LogisticsSearch = Depends(get_search)
) -> ExceptionResponse:
    try:
        answer = search.handle_exception(request.shipment_id, request.question)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ExceptionResponse(**answer.__dict__)


def run() -> None:
    uvicorn.run("shipment_search.service:app", host="127.0.0.1", port=8000)
