from odoo import models

class AccountMove(models.Model):
    _inherit = 'account.move'

    def unlink(self):
        downpayment_lines = self.mapped('line_ids.purchase_line_id').filtered(
            lambda line: line.is_downpayment and line.invoice_lines <= self.mapped('line_ids'))
        res = super(AccountMove, self).unlink()
        if downpayment_lines:
            downpayment_lines.unlink()
        return res
