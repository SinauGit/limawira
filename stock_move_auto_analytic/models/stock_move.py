from odoo import api, models

class StockMove(models.Model):
    _inherit = "stock.move"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("analytic_distribution"):
                analytic = self._extract_analytic_from_vals(vals)
                if analytic:
                    vals["analytic_distribution"] = analytic
        moves = super().create(vals_list)
        for move in moves.filtered(lambda m: not m.analytic_distribution):
            analytic = move._compute_auto_analytic_distribution()
            if analytic:
                move.analytic_distribution = analytic
        return moves

    def _extract_analytic_from_vals(self, vals):
        picking_id = vals.get("picking_id")
        if picking_id:
            picking = self.env["stock.picking"].browse(picking_id)
            analytic = self._analytic_from_project(getattr(picking, "project_id", False))
            if analytic:
                return analytic
        origin_id = vals.get("origin_returned_move_id")
        if origin_id:
            origin = self.env["stock.move"].browse(origin_id)
            if origin and origin.analytic_distribution:
                return origin.analytic_distribution
        return False

    def _compute_auto_analytic_distribution(self):
        self.ensure_one()
        project = getattr(self.picking_id, "project_id", False)
        analytic = self._analytic_from_project(project)
        if analytic:
            return analytic
        if self.origin_returned_move_id and self.origin_returned_move_id.analytic_distribution:
            return self.origin_returned_move_id.analytic_distribution
        return False

    @api.model
    def _analytic_from_project(self, project):
        if not project:
            return False
        if "analytic_distribution" in project._fields and project.analytic_distribution:
            return project.analytic_distribution
        if "analytic_account_id" in project._fields and project.analytic_account_id:
            return {project.analytic_account_id.id: 100}
        return False
