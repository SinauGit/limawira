from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    purchase_discount_product_id = fields.Many2one(
        'product.product',
        string='Purchase Discount Product',
        domain="[('type', '=', 'service'), ('company_id', 'in', [False, id])]",
        help="Product used for applying discount in purchase orders.",
        copy=False,
    ) 