from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def write(self, vals):
        res = super().write(vals)
        if 'project_id' in vals:
            projects = self.sudo().project_id
            projects._lww_relink_pickings()
            projects._lww_refresh_billing()
        return res
