from odoo import api, models

class StockMove(models.Model):
    _inherit = "stock.move"

    @api.model_create_multi
    def create(self, vals_list):
        # Prefill dari vals sebelum create
        for vals in vals_list:
            if not vals.get("analytic_distribution"):
                analytic = self._extract_analytic_from_vals(vals)
                if analytic:
                    vals["analytic_distribution"] = analytic

        moves = super().create(vals_list)

        # Post-fill setelah create jika masih kosong
        for move in moves.filtered(lambda m: not m.analytic_distribution):
            analytic = move._compute_auto_analytic_distribution()
            if analytic:
                move.analytic_distribution = analytic
        return moves

    def write(self, vals):
        # Tangkap perubahan relasi penting setelah write
        picking_changed = 'picking_id' in vals
        sale_line_changed = 'sale_line_id' in vals
        res = super().write(vals)
        if picking_changed or sale_line_changed:
            for move in self.filtered(lambda m: not m.analytic_distribution and m.state not in ('done', 'cancel')):
                analytic = move._compute_auto_analytic_distribution()
                if analytic:
                    # gunakan super untuk menghindari triggering inverse yang tidak perlu
                    super(StockMove, move).write({'analytic_distribution': analytic})
        return res

    # ---------- Helpers ----------
    def _extract_analytic_from_vals(self, vals):
        """Ambil analytic_distribution berbasis Project di DO (picking.project_id),
        fallback Project dari SO (sale_line_id.order_id.project_id bila ada), atau dari return."""
        # 1) Project dari DO (picking.project_id)
        picking_id = vals.get("picking_id")
        if picking_id:
            picking = self.env["stock.picking"].browse(picking_id)
            analytic = self._analytic_from_project(getattr(picking, "project_id", False))
            if analytic:
                return analytic

        # 2) Fallback: Project dari SO (via sale_line_id -> order_id.project_id) — safe check
        sl_id = vals.get("sale_line_id")
        if sl_id:
            sol = self.env["sale.order.line"].browse(sl_id)
            order = getattr(sol, "order_id", False)
            project = getattr(order, "project_id", False)
            analytic = self._analytic_from_project(project)
            if analytic:
                return analytic

        # 3) Return (copy dari move asal)
        origin_id = vals.get("origin_returned_move_id")
        if origin_id:
            origin = self.env["stock.move"].browse(origin_id)
            if origin and origin.analytic_distribution:
                return origin.analytic_distribution

        return False

    def _compute_auto_analytic_distribution(self):
        """Ambil analytic_distribution setelah record terbentuk (Project di DO / SO->Project / Return)."""
        self.ensure_one()

        # 1) Project pada DO
        project = getattr(self.picking_id, "project_id", False)
        analytic = self._analytic_from_project(project)
        if analytic:
            return analytic

        # 2) Fallback: Project dari SO (jika ada relasi sale_line_id dan field project_id ada)
        if getattr(self, "sale_line_id", False) and self.sale_line_id:
            order = getattr(self.sale_line_id, "order_id", False)
            project = getattr(order, "project_id", False)
            analytic = self._analytic_from_project(project)
            if analytic:
                return analytic

        # 3) Return
        if self.origin_returned_move_id and self.origin_returned_move_id.analytic_distribution:
            return self.origin_returned_move_id.analytic_distribution

        return False

    @api.model
    def _analytic_from_project(self, project):
        """Konversi Project menjadi analytic_distribution secara defensif."""
        if not project:
            return False

        # a) Bila project punya distribution langsung (jika modul Anda menambahkannya)
        if "analytic_distribution" in project._fields and project.analytic_distribution:
            return project.analytic_distribution

        # b) Bila project hanya punya analytic_account_id (standar Odoo/umum)
        if "analytic_account_id" in project._fields and project.analytic_account_id:
            return {project.analytic_account_id.id: 100}

        return False