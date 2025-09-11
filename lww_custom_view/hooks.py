from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    """Migrasi data lama: company_account -> own_account (aman berulang)"""
    env = api.Environment(cr, SUPERUSER_ID, {})


    env["hr.expense"].sudo().with_context(tracking_disable=True) \
    .search([("payment_mode", "=", "company_account")]) \
    .write({"payment_mode": "own_account"})


    env["hr.expense.sheet"].sudo().with_context(tracking_disable=True) \
    .search([("payment_mode", "=", "company_account")]) \
    .write({"payment_mode": "own_account"})