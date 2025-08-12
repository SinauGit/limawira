from odoo import api, models

class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.onchange("project_id")
    def _onchange_project_id_fill_moves_from_sol(self):
        for picking in self:
            picking._fill_moves_analytic_from_sol()

    def write(self, vals):
        res = super().write(vals)
        if "project_id" in vals:
            for picking in self:
                picking._fill_moves_analytic_from_sol()
        return res

    def _pre_action_done_hook(self):
        for picking in self:
            picking._fill_moves_analytic_from_sol()
        return super()._pre_action_done_hook()

    def _fill_moves_analytic_from_sol(self):
        for picking in self:
            # 1) Kumpulkan kandidat SOL: dari sale_id jika ada; jika tidak, dari Project
            sol_domain = [("analytic_distribution", "!=", False)]
            order = getattr(picking, "sale_id", False)
            project = getattr(picking, "project_id", False)

            if order:
                sol_domain += [("order_id", "=", order.id)]
            elif project:
                sol_domain += [("order_id.project_id", "=", project.id)]
            else:
                continue

            SaleOrderLine = self.env["sale.order.line"]
            sol_candidates = SaleOrderLine.search(sol_domain, order="id desc", limit=0)
            if not sol_candidates:
                # fallback: kalau Project punya analitik langsung
                analytic = self.env["stock.move"]._analytic_from_project(project) if project else False
                if analytic:
                    for move in picking.move_ids_without_package.filtered(lambda m: not m.analytic_distribution and m.state not in ("done", "cancel")):
                        move.analytic_distribution = analytic
                        for ml in move.move_line_ids.filtered(lambda x: not x.analytic_distribution):
                            ml.analytic_distribution = analytic
                continue

            for move in picking.move_ids_without_package.filtered(lambda m: not m.analytic_distribution and m.state not in ("done", "cancel")):
                analytic = False
                # Prioritas 1: SOL dengan product yang sama
                same_prod = sol_candidates.filtered(lambda l: l.product_id == move.product_id and l.analytic_distribution)
                if same_prod:
                    analytic = same_prod[0].analytic_distribution
                else:
                    # Prioritas 2: SOL pertama yang punya analytic
                    first_with_analytic = sol_candidates.filtered(lambda l: l.analytic_distribution)
                    if first_with_analytic:
                        analytic = first_with_analytic[0].analytic_distribution
                if not analytic and project:
                    # Prioritas 3 (fallback): Project -> analytic
                    analytic = self.env["stock.move"]._analytic_from_project(project)

                if analytic:
                    move.analytic_distribution = analytic
                    for ml in move.move_line_ids.filtered(lambda x: not x.analytic_distribution):
                        ml.analytic_distribution = analytic