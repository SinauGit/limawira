from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    discount = fields.Float(string='Discount (%)', digits=(16, 20), default=0.0)
    total_discount = fields.Float(string="Total Discount", default=0.0,
                                store=True)

    def _prepare_account_move_line(self, move=False):
        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move)
        res.update({'discount': self.discount})
        return res
