import frappe
import requests
from frappe import _

MONDAY_URL = "https://api.monday.com/v2"

CREATE_ITEM = """mutation ($board_id: ID!, $item_name: String!, $column_values: JSON!) {
  create_item (board_id: $board_id, item_name: $item_name, column_values: $column_values) { id }
}"""


def on_update_after_submit(doc, method: str | None = None) -> None:
	"""Push an approved certificate to the Monday.com certificate board exactly once.

	A workflow transition on a submitted document fires only on_update_after_submit,
	which the Webhook DocType cannot register, so the push lives here. `monday_push_sent`
	makes it idempotent: later transitions (e.g. Distribute) do not push again.
	"""
	if doc.status != "Approved" or not doc.hot_approved_at or doc.monday_push_sent:
		return

	settings = frappe.get_single("AATC Settings")
	# monday_api_token is a Password field: the attribute holds the mask, not the token.
	token = settings.get_password("monday_api_token", raise_exception=False)
	board_id = settings.monday_certificate_board_id
	if not token or not board_id:
		frappe.log_error(
			title=_("Certificate not pushed to Monday"),
			message=_("AATC Settings is missing the Monday API token or certificate board ID."),
			reference_doctype=doc.doctype,
			reference_name=doc.name,
		)
		return

	try:
		response = requests.post(
			MONDAY_URL,
			headers={"Authorization": token, "Content-Type": "application/json"},
			data=frappe.as_json(
				{
					"query": CREATE_ITEM,
					"variables": {
						"board_id": board_id,
						"item_name": f"Certificate {doc.certificate_number} - {doc.member_name}",
						"column_values": {
							"certificate_number": doc.certificate_number,
							"member": doc.member_name,
							"course": doc.course_title,
							"issue_date": str(doc.issue_date) if doc.issue_date else "",
							"expiry_date": str(doc.expiry_date) if doc.expiry_date else "",
							"status": doc.status,
						},
					},
				}
			),
			timeout=30,
		)
		response.raise_for_status()
	except requests.RequestException as exc:
		frappe.log_error(
			title=_("Certificate not pushed to Monday"),
			message=f"{exc}\n\n{getattr(exc.response, 'text', '')}",
			reference_doctype=doc.doctype,
			reference_name=doc.name,
		)
		return

	doc.db_set("monday_push_sent", 1, update_modified=False)
