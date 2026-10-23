import frappe
import requests
from frappe import _

from aatc_integrations.events.certificate import CREATE_ITEM, MONDAY_URL


def _send(doc, board_id, item_name, column_values):
	"""POST one Monday item. Returns the response, or logs and returns None on failure."""
	settings = frappe.get_single("AATC Settings")
	# monday_api_token is a Password field: the attribute holds the mask, not the token.
	token = settings.get_password("monday_api_token", raise_exception=False)
	if not token or not board_id:
		frappe.log_error(
			title=_("Record not pushed to Monday"),
			message=_("AATC Settings is missing the Monday API token or the board ID for this push."),
			reference_doctype=doc.doctype,
			reference_name=doc.name,
		)
		return None

	try:
		response = requests.post(
			MONDAY_URL,
			headers={"Authorization": token, "Content-Type": "application/json"},
			data=frappe.as_json(
				{
					"query": CREATE_ITEM,
					"variables": {
						"board_id": board_id,
						"item_name": item_name,
						"column_values": column_values,
					},
				}
			),
			timeout=30,
		)
		response.raise_for_status()
	except requests.RequestException as exc:
		frappe.log_error(
			title=_("Record not pushed to Monday"),
			message=f"{exc}\n\n{getattr(exc.response, 'text', '')}",
			reference_doctype=doc.doctype,
			reference_name=doc.name,
		)
		return None

	doc.db_set("monday_push_sent", 1, update_modified=False)
	return response


def push_closed_session(doc, method: str | None = None) -> None:
	"""Push a Session Lifecycle to the Monday session board once, when it closes."""
	if doc.status != "CLOSED" or doc.monday_push_sent:
		return

	board_id = frappe.get_single("AATC Settings").monday_session_board_id
	_send(
		doc,
		board_id,
		f"Session {doc.session_title} - CLOSED",
		{
			"session_title": doc.session_title,
			"course": doc.course,
			"status": doc.status,
			"start_date": str(doc.start_date or ""),
			"end_date": str(doc.end_date or ""),
		},
	)


def push_open_ncr(doc, method: str | None = None) -> None:
	"""Push a Nonconformity to the Monday CAPA board on the transition into Open.

	A workflow transition on a submitted document fires only on_update_after_submit,
	which a plain on_update hook never sees, so both events route here.
	"""
	if doc.status != "Open" or doc.monday_push_sent:
		return

	previous = doc.get_doc_before_save()
	if previous is not None and previous.status == "Open":
		return

	board_id = frappe.get_single("AATC Settings").monday_capa_board_id
	_send(
		doc,
		board_id,
		f"NCR {doc.name} - {(doc.exception_nature or '')[:50]}",
		{
			"ncr_number": doc.name,
			"exception_nature": doc.exception_nature,
			"priority": doc.priority_level,
			"responsible_person": doc.responsible_person,
			"status": doc.status,
		},
	)
