from odoo import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    requires_down_payment = fields.Boolean(
        string="Requires Down Payment", 
        default=False,
        help="If checked, this customer requires a down payment before delivery."
    ) 