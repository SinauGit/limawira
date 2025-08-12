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