from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    dp_installment_no = fields.Integer(copy=False)

    def _backfill_dp_installment_no(self):
        dp_invoices = self.search([
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('state', '!=', 'cancel'),
            ('invoice_origin', '!=', False),
            ('invoice_line_ids.sale_line_ids.is_downpayment', '=', True),
        ])

        origins = set(dp_invoices.mapped('invoice_origin'))
        for origin in origins:
            invoices = dp_invoices.filtered(lambda inv: inv.invoice_origin == origin)
            invoices = invoices.sorted(key=lambda inv: (inv.invoice_date or fields.Date.today(), inv.id))
            for idx, invoice in enumerate(invoices, start=1):
                invoice.dp_installment_no = idx

        return True
