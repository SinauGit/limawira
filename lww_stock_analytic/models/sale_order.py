from odoo import api, models

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        res = super().action_confirm()
        # Setelah konfirmasi, isi analytic_distribution pada DO yang terkait SO ini, jika masih kosong
        for order in self:
            pickings = []
            if "picking_ids" in order._fields:
                pickings = order.picking_ids
            if not pickings:
                pickings = order.order_line.mapped("move_ids").mapped("picking_id")
            for picking in pickings:
                picking._fill_moves_analytic_from_sol()
        return res