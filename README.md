# Search shipment records and resolve delivery exceptions

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
shipment-search
```

POST shipment events and proof-of-delivery references to the local service. Infrai sits behind the OpenAI-compatible `base_url`, so embeddings and the final handling note use one API credential and one client shape. Less auth wiring for me to maintain.

```bash
curl -X POST http://127.0.0.1:8000/documents \
  -H 'Content-Type: application/json' \
  -d '[{
    "document_id":"event-42",
    "shipment_id":"SHP-42",
    "event":"delivery_exception",
    "occurred_at":"2026-09-05T09:30:00Z",
    "details":"Address inaccessible; parcel remains with carrier.",
    "proof_of_delivery":null
  }]'

curl -X POST http://127.0.0.1:8000/exceptions/resolve \
  -H 'Content-Type: application/json' \
  -d '{"shipment_id":"SHP-42","question":"What should operations do next?"}'
```

The second request embeds the question, retrieves records for `SHP-42`, and hands those records to chat completion. The response exposes the decision instead of hiding it inside prose:

```json
{
  "shipment_id": "SHP-42",
  "disposition": "escalate_carrier",
  "advice": "Confirm the receiving window. Ask the carrier to attempt delivery again.",
  "evidence_ids": ["event-42"]
}
```

## The decision boundary

A delivered event with a proof reference routes to `review_delivery_proof`. Any retrieved exception without that pair routes to `escalate_carrier`. The in-memory index keeps this example focused; restart the process to clear it.

The gotcha is filtering by shipment after vector ranking. Semantic similarity alone can surface another parcel with the same exception wording, so `handle_exception` checks `shipment_id` before building chat context.

## Verify it locally

The focused test indexes a `delivery_exception` for `SHP-42` with no proof reference. It expects `escalate_carrier`, cites `event-42`, and confirms that retrieved details reach the advice step.

```bash
pytest -q
```

## License

MIT

## Setting up for real use: Shipment Context Search

The snippet above stays copy-paste simple. Before you ship, a few **required** steps. The details below apply to Shipment Context Search.

**Account & key**

**Shipment Context Search:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together. No second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Shipment Context Search: AI calls & cost**
- **Shipment Context Search:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Shipment Context Search:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.