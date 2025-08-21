from odoo import api, models

class StockMove(models.Model):
    _inherit = "stock.move"

    @api.model_create_multi
    def create(self, vals_list):
        # Prefill dari SOL (untuk alur SO) atau dari return
        for vals in vals_list:
            if not vals.get("analytic_distribution"):
                # 1) Jika ada sale_line_id, ambil dari SOL
                sl_id = vals.get("sale_line_id")
                if sl_id:
                    sol = self.env["sale.order.line"].browse(sl_id)
                    if sol and sol.analytic_distribution:
                        vals["analytic_distribution"] = sol.analytic_distribution
                        continue
                # 2) Return: copy dari move asal
                origin_id = vals.get("origin_returned_move_id")
                if origin_id:
                    origin = self.env["stock.move"].browse(origin_id)
                    if origin and origin.analytic_distribution:
                        vals["analytic_distribution"] = origin.analytic_distribution
                        continue
        return super().create(vals_list)

    @api.model
    def _analytic_from_project(self, project):
        """
        Kembalikan analytic_distribution (dict), prioritas:
          1) project.analytic_distribution (jika field ada & terisi),
          2) project.analytic_account_id (jika ada),
          3) project.analytic_account_ids[:1] (ambil 1 akun pertama).
        Hasil: {analytic_account_id: 100.0} atau False.
        """
        if not project:
            return False

        # 1) Jika project punya distribusi analitik langsung
        if 'analytic_distribution' in project._fields and project.analytic_distribution:
            return project.analytic_distribution

        # 2) Jika project punya 1 akun analitik (M2O)
        if 'analytic_account_id' in project._fields and project.analytic_account_id:
            return {project.analytic_account_id.id: 100.0}

        # 3) Jika project punya banyak akun analitik (M2M) -> ambil satu yang pertama
        if 'analytic_account_ids' in project._fields and project.analytic_account_ids:
            aa = project.analytic_account_ids[:1]
            if aa:
                return {aa.id: 100.0}

        return False