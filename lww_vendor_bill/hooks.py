from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
                                                                           
    env = api.Environment(cr, SUPERUSER_ID, {})


    env["hr.expense"].sudo().with_context(tracking_disable=True)\
    .search([("payment_mode", "=", "company_account")])\
    .write({"payment_mode": "own_account"})


                                                                          
                                                           
                                             