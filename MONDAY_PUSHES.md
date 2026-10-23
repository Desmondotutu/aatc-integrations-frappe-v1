# Monday.com pushes: doc events, not Webhooks

All three outbound Monday.com pushes are `doc_events` in
`aatc_integrations/hooks.py`. **No Webhook DocType record is used anywhere in this
bench** — `frappe.get_all("Webhook")` must return zero rows.

| DocType | Event | Handler | Guard |
| --- | --- | --- | --- |
| LMS Certificate | `on_update_after_submit` | `events.certificate.on_update_after_submit` | `status == "Approved"` and `hot_approved_at` set |
| Session Lifecycle | `on_update`, `on_update_after_submit` | `events.monday.push_closed_session` | `status == "CLOSED"` |
| Nonconformity | `after_insert`, `on_update`, `on_update_after_submit` | `events.monday.push_open_ncr` | `status == "Open"` and previous status was not `"Open"` |

## Why not a Webhook record

1. **Wrong events.** `run_webhooks` only fires for events in `supported_events`.
   A workflow transition on a submitted document produces only
   `on_update_after_submit`, so a Webhook configured for `on_update` never fires
   and one configured for `on_update_after_submit` fires on every unrelated save.
2. **No dynamic auth header.** `get_webhook_headers` copies header values
   verbatim. Only `request_url` (when `is_dynamic_url` is set) and `webhook_json`
   go through `render_template`, so a `{{ ... }}` header would be sent literally.
   A doc event reads the token from AATC Settings at send time instead.

## Idempotency

Each of the three doctypes carries a hidden `monday_push_sent` Custom Field with
`allow_on_submit: 1` (without `allow_on_submit` the flag cannot be written after
submission). The handlers set it with `doc.db_set(...)` only after the HTTP
response passes `raise_for_status()`. A failed send logs an Error Log and leaves
the flag clear, so the next save retries.

## Credentials

`AATC Settings.monday_api_token` is a **Password** field: `settings.monday_api_token`
returns the mask (`****************`). Always read it with
`settings.get_password("monday_api_token", raise_exception=False)`. Board IDs come
from `monday_certificate_board_id`, `monday_session_board_id` and
`monday_capa_board_id`. If the token or the relevant board ID is empty, the
handler logs and returns without sending.

## Version portability

The three AATC apps set no `use_json_request_body` hook. That hook only changes
the request body the desk frontend sends to *a given app's own* endpoints
(`frappe.boot.json_request_apps`, consumed by `frappe.request.app_uses_json` in
`frappe/public/js/frappe/request.js`). None of the AATC apps expose an endpoint
whose callers depend on the encoding, and the Monday pushes leave the browser
entirely via `requests.post`, so the hook had no effect here beyond making the
hooks files differ between v16 (where the hook does not exist) and v17.

## Re-enabling a Webhook record

Don't. If an integration genuinely needs a Webhook (e.g. a third-party
listener), add a new record with `is_dynamic_url` and a literal header, and keep
it off the three doctypes above so pushes are not sent twice.

The record-level cleanup lives in
`aatc_integrations/patches/retire_monday_webhooks.py` (it deletes
"AATC Session Closed" and "AATC NCR Open"); the guard fields are added by
`aatc/patches/add_monday_push_sent_fields.py` and
`aatc/patches/add_certificate_monday_push_sent.py`.
