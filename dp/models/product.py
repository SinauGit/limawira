from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    requires_down_payment = fields.Boolean(
        string="Requires Down Payment", 
        default=False,
        help="If checked, this product requires a down payment before delivery."
    )
