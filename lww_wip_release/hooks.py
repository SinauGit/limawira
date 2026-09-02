from odoo import api, SUPERUSER_ID


def post_init_hook(env):
    env.cr.execute("""
        UPDATE sale_order
           SET x_original_contract_value = amount_total,
               x_last_contract_value = amount_total
         WHERE state = 'sale'
           AND COALESCE(x_original_contract_value, 0) = 0
    """)