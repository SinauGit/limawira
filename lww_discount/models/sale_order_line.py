from odoo import fields, models


class SaleOrderLine(models.Model):
    """This class inherits "sale.order.line" and adds fields discount,
     total_discount """
    _inherit = "sale.order.line"

    discount = fields.Float(string='Discount (%)', digits=(16, 20), default=0.0)
    total_discount = fields.Float(string="Total Discount", default=0.0,
                                  store=True)
