from odoo import api, models

class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.onchange("project_id")
    def _onchange_project_id_fill_move_analytic(self):
        """Jika user memilih Project pada DO manual (belum disave), isi analytic_distribution di semua move yang kosong."""
        for picking in self:
            analytic = self.env["stock.move"]._analytic_from_project(getattr(picking, "project_id", False))
            if analytic:
                for move in picking.move_ids_without_package.filtered(lambda m: not m.analytic_distribution):
                    move.analytic_distribution = analytic

    def write(self, vals):
        # Setelah DO di-save dan project_id berubah, isi analytic untuk moves yang belum punya
        res = super().write(vals)
        if "project_id" in vals:
            for picking in self:
                analytic = self.env["stock.move"]._analytic_from_project(getattr(picking, "project_id", False))
                if analytic:
                    picking.move_ids_without_package.filtered(
                        lambda m: not m.analytic_distribution and m.state not in ("done", "cancel")
                    ).write({"analytic_distribution": analytic})
        return res