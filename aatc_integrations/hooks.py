app_name = "aatc_integrations"
app_title = "AATC Integrations"
app_publisher = "Desmond Wangki"
app_description = "AATC Outbound Integrations"
app_email = "admin@aatc.localhost"
app_license = "mit"

required_apps = ["frappe", "aatc"]

# All three Monday pushes are doc events. The Webhook DocType cannot filter workflow
# transitions on submitted documents, and its headers take literal values only, so it
# cannot carry a token that follows AATC Settings.
doc_events = {
    "LMS Certificate": {
        "on_update_after_submit": "aatc_integrations.events.certificate.on_update_after_submit",
    },
    "Session Lifecycle": {
        "on_update": "aatc_integrations.events.monday.push_closed_session",
        "on_update_after_submit": "aatc_integrations.events.monday.push_closed_session",
    },
    "Nonconformity": {
        "after_insert": "aatc_integrations.events.monday.push_open_ncr",
        "on_update": "aatc_integrations.events.monday.push_open_ncr",
        "on_update_after_submit": "aatc_integrations.events.monday.push_open_ncr",
    },
}

fixtures = [
    {"doctype": "Notification", "filters": [["module", "=", "AATC Integrations"]]},
]

# Testing
before_tests = "aatc_integrations.install.before_tests"

# Export Python type annotations
export_python_type_annotations = True
require_type_annotated_api_methods = True