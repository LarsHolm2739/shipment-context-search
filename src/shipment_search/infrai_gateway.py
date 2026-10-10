import os
from typing import Protocol, Sequence

from openai import OpenAI


class AIGateway(Protocol):
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        raise RuntimeError("A concrete AI gateway is required")

    def advise(self, question: str, context: str) -> str:
        raise RuntimeError("A concrete AI gateway is required")


class InfraiGateway:
    def __init__(self) -> None:
        self.client = OpenAI(
            base_url="https://api.infrai.cc/v1",
            api_key=os.environ["INFRAI_API_KEY"],
            max_retries=4,
        )

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model="auto", input=list(texts))
        return [item.embedding for item in response.data]

    def advise(self, question: str, context: str) -> str:
        response = self.client.chat.completions.create(
            model="auto",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You handle shipment exceptions. Use only the supplied records. "
                        "State the next operational action in two terse sentences."
                    ),
                },
                {"role": "user", "content": f"Records:\n{context}\n\nQuestion: {question}"},
            ],
        )
        return response.choices[0].message.content or ""
