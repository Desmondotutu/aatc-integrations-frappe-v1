import frappe

# Both Monday pushes are doc events in aatc_integrations.events.monday. Their Webhook
# records fired on the wrong events and could only carry a literal token in the header,
# so they are deleted rather than left disabled.
WEBHOOKS = ("AATC Session Closed", "AATC NCR Open")


def execute():
	for name in WEBHOOKS:
		if frappe.db.exists("Webhook", name):
			frappe.delete_doc("Webhook", name, force=True, ignore_permissions=True)
	frappe.db.commit()
	frappe.client_cache.delete_value("webhooks")


def rollback():
	pass
