from odoo import api, models

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("analytic_distribution"):
                move_id = vals.get("move_id")
                if move_id:
                    move = self.env["stock.move"].sudo().browse(move_id)
                    if move and move.analytic_distribution:
                        vals["analytic_distribution"] = move.analytic_distribution
        return super().create(vals_list)
