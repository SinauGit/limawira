from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    sale_id = fields.Many2one('sale.order', string='Sale Order', related='invoice_line_ids.sale_line_ids.order_id', store=True, readonly=True)

    def has_downpayment_product(self):
        self.ensure_one()
        for line in self.invoice_line_ids:
            if line.product_id and line.product_id.name.lower() == 'down payment':
                return True
        return False

    def print_invoice_pdf(self):
        self.ensure_one()
        if self.has_downpayment_product():
            report_action = self.env.ref('custom_downpayment_invoice.downpayment_invoice_report')
        else:
            report_action = self.env.ref('account.account_invoices_without_payment')
        return report_action.report_action(self)
