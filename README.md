# Before building an agent, map the workflow

A reproducible companion to the article. Source: [subodhjena/before-building-an-agent](https://github.com/subodhjena/before-building-an-agent). This is a read-only workflow example around candidate model output, not a deployed agent or payment service.

## Run it

Requires Python 3.11 or later. No dependencies, credentials, model calls, or network access are needed.

```bash
python3 -m unittest -v
python3 workflow.py
```

Run from this directory. `workflow.py` prints twelve fixture outcomes and writes `results.json` in the current directory. `sample-output.txt` records an actual run on 17 October 2026 with Python 3.14.5. The fixture clock (`2026-08-12`) is synthetic and is not the run date.

## Files

| File                    | Purpose                                                                                                              |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `workflow.py`           | Validate a proposal, retrieve a record, check ownership and example policy, prepare a review packet                  |
| `test_workflow.py`      | Check outcomes, checkpoints, ownership, invalid inputs, policy boundaries, dependency failures, and unchanged ledger |
| `fixtures.json`         | Invented orders, candidate interpretations, expected outcomes, and simulated dependency failures                     |
| `proposal.schema.json`  | Document the candidate interpretation's allowed shape                                                                |
| `proposal-prompt.txt`   | Example prompt for a future interpretation component; not executed                                                   |
| `sample-output.txt`     | Observed output of `python3 workflow.py`                                                                             |
| `workflow.mmd`          | Editable Mermaid source for the proposed process                                                                     |
| `workflow-worksheet.md` | Blank discovery worksheet for a different workflow                                                                   |

## What the example establishes

The fixtures supply hand-authored model-like proposals, including bad ones. They demonstrate application routing under those inputs. The tests do not measure natural-language interpretation, injection resistance, production reliability, or business savings.

The `Request.customer_id` value is assumed to come from an authenticated application. The example does not authenticate anyone. An actual service also needs account-scoped reads at its data-access boundary, appropriate permissions, and a safe customer-facing response. The trace and packet here contain synthetic identifiers; production logging needs its own privacy design.

The invented `example-v1` policy permits a review packet for delivered orders aged 0 through 14 days, priced at 1 through 5,000 USD cents. Exceptions go to review. Already-refunded orders produce no new action. There are no partial refunds, returns, tax calculations, disputed charges, or payment writes. These thresholds and simplifications describe the example only.

`review_ready` means a packet was prepared in memory. `waiting_for_system` means the dependency failed. Neither state implements a persistent queue, worker, retry, approval, or recovery mechanism. The Mermaid diagram extends to a reviewer wait to show the next responsibility, beyond the executable example.

Policy and money values come from checked record fields, not from the candidate model output. Ownership and known/unknown order outcomes are checked locally. No refund is issued and no customer is notified.

Research citations are in the article. All example code, policy, data, diagram, and worksheet were prepared for this article; no benchmark code or customer records are bundled.

## License

The companion code, synthetic fixtures, diagram, and worksheet are available under the [MIT license](LICENSE).

## Article snapshot

Read the [GitHub-readable article](article.md) or the [canonical website article](https://subodhjena.com/blog/before-building-an-agent-map-the-workflow). The snapshot and selected watercolor cover were added on 17 October 2026. The original executable code remains at revision `972e6d29c22e86b35078823c57d1ccd21b9af647`.
