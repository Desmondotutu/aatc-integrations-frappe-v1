import frappe

def before_tests():
    """Run before tests"""
    frappe.flags.in_test = True
    frappe.local.conf.rate_limit = False
    # Disable user creation throttle for tests
    frappe.local.conf.throttle_user_limit = 1000000