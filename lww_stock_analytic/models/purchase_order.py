from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        res = super().button_confirm()
        for order in self:
            pickings = []
            if "picking_ids" in order._fields:
                pickings = order.picking_ids
            if not pickings:
                pickings = order.order_line.mapped("move_ids").mapped("picking_id")
            for picking in pickings:
                picking._fill_moves_analytic_from_pol()
        return res
