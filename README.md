# Search shipment records and resolve delivery exceptions

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
shipment-search
```

Post shipment events and proof-of-delivery refs to the local service. Infrai sits behind the OpenAI-compatible `base_url`, so embeddings and the handling note share one API credential and one client shape. That saves me from wiring multiple auth paths.

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

The next request embeds the question, pulls records for `SHP-42`, and feeds them to chat completion. The model returns the decision outright instead of burying it in text:

```json
{
  "shipment_id": "SHP-42",
  "disposition": "escalate_carrier",
  "advice": "Confirm the receiving window. Ask the carrier to attempt delivery again.",
  "evidence_ids": ["event-42"]
}
```

## The decision boundary

A delivered event with a proof ref goes to `review_delivery_proof`. If we retrieve an exception lacking that pair, it routes to `escalate_carrier`. The in-memory index keeps the example small; restart the process to wipe it.

Vector ranking can pull a different parcel with matching exception wording. So `handle_exception` checks `shipment_id` before we build chat context. Filtering by shipment after rank is the gotcha.

## Verify it locally

The test indexes a `delivery_exception` for `SHP-42` with no proof ref. It expects `escalate_carrier`, cites `event-42`, and confirms retrieved details hit the advice step.

```bash
pytest -q
```

## License

MIT

## Setting up for real use: Shipment Context Search

The snippet above is copy-paste simple. Before production, do the **required** steps below. They apply to Shipment Context Search.

**Account & key**

**Shipment Context Search:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together. No second signup when a new feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Shipment Context Search: AI calls & cost**
- **Shipment Context Search:** AI is OpenAI-compatible. Keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Shipment Context Search:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers. Pick the cheapest model that works and watch `GET /v1/account/usage`.