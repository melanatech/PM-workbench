# Data request — {{release_id}}

## Fulfillment protocol

1. Agent emits this file with `status: open` — **does not** query warehouses or invent CSVs.
2. Human (or approved tool) drops exports under `outputs/releases/{{release_id}}/data/`.
3. Human sets each request below to `status: fulfilled` and names the file.
4. `/report ship-signal` resumes measuring-impact / readout only after fulfillment.

## Requests

### dr-1

- **status:** open
- **Blocks proposal:**
- **Need:** (metric, window, grain, filters)
- **Drop file as:** `data/dr-1.csv` (or note format)
- **fulfilled_file:**
