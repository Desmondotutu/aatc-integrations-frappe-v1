import frappe
from frappe.tests import IntegrationTestCase


class TestIntegrationReadiness(IntegrationTestCase):
	"""The Monday pushes are doc events; no Webhook DocType record is used anywhere."""

	def test_no_aatc_webhook_records(self):
		webhooks = frappe.get_all("Webhook", filters={"name": ["like", "AATC%"]}, pluck="name")
		self.assertEqual(webhooks, [], f"stale AATC webhooks must be deleted, found {webhooks}")

	def test_no_webhook_posts_to_monday(self):
		urls = [
			webhook.request_url
			for webhook in frappe.get_all("Webhook", fields=["request_url"])
			if webhook.request_url
		]
		self.assertNotIn("https://api.monday.com/v2", urls)

	def test_monday_pushes_are_doc_events(self):
		from aatc_integrations import hooks

		self.assertEqual(
			hooks.doc_events["LMS Certificate"]["on_update_after_submit"],
			"aatc_integrations.events.certificate.on_update_after_submit",
		)
		for event in ("on_update", "on_update_after_submit"):
			self.assertEqual(
				hooks.doc_events["Session Lifecycle"][event],
				"aatc_integrations.events.monday.push_closed_session",
			)
		for event in ("after_insert", "on_update", "on_update_after_submit"):
			self.assertEqual(
				hooks.doc_events["Nonconformity"][event],
				"aatc_integrations.events.monday.push_open_ncr",
			)

	def test_push_guard_fields_allow_on_submit(self):
		for doctype in ("Session Lifecycle", "Nonconformity", "LMS Certificate"):
			field = frappe.get_meta(doctype).get_field("monday_push_sent")
			self.assertIsNotNone(field, f"{doctype} is missing monday_push_sent")
			self.assertTrue(field.allow_on_submit, f"{doctype}.monday_push_sent must allow on submit")
