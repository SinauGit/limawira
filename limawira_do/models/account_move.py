from odoo import models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends('name')
    def _get_report_base_filename(self):
        """Override untuk mengubah nama file report"""
        for record in self:
            record.report_base_filename = 'DPM %s' % (record.name or '')
