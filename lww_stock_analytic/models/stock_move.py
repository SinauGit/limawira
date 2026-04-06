from odoo import api, models

class StockMove(models.Model):
    _inherit = "stock.move"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("analytic_distribution"):
                                                           
                sl_id = vals.get("sale_line_id")
                if sl_id:
                    sol = self.env["sale.order.line"].sudo().browse(sl_id)
                    if sol and sol.analytic_distribution:
                        vals["analytic_distribution"] = sol.analytic_distribution
                        continue
                                                                        
                pol_id = vals.get("purchase_line_id")
                if pol_id:
                    pol = self.env["purchase.order.line"].sudo().browse(pol_id)
                    if pol and pol.analytic_distribution:
                        vals["analytic_distribution"] = pol.analytic_distribution
                        continue

                origin_id = vals.get("origin_returned_move_id")
                if origin_id:
                    origin = self.env["stock.move"].sudo().browse(origin_id)
                    if origin and origin.analytic_distribution:
                        vals["analytic_distribution"] = origin.analytic_distribution
                        continue
        return super().create(vals_list)

    @api.model
    def _analytic_from_project(self, project):
        if not project:
            return False
        project = project.sudo()

        if 'analytic_distribution' in project._fields and project.analytic_distribution:
            return project.analytic_distribution
        # Odoo 18: project.project menggunakan field 'account_id'
        if 'account_id' in project._fields and project.account_id:
            return {str(project.account_id.id): 100.0}
        # fallback untuk field lama
        if 'analytic_account_id' in project._fields and project.analytic_account_id:
            return {str(project.analytic_account_id.id): 100.0}
        if 'analytic_account_ids' in project._fields and project.analytic_account_ids:
            aa = project.analytic_account_ids[:1]
            if aa:
                return {str(aa.id): 100.0}
        return False
