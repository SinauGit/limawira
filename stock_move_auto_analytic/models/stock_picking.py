from odoo import api, models

class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.onchange("project_id")
    def _onchange_project_id_fill_move_analytic(self):
        for picking in self:
            analytic = self.env["stock.move"]._analytic_from_project(getattr(picking, "project_id", False))
            if analytic:
                for move in picking.move_ids_without_package.filtered(lambda m: not m.analytic_distribution):
                    move.analytic_distribution = analytic
