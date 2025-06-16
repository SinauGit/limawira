from odoo import models, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    def has_downpayment_product(self):
        self.ensure_one()
        for line in self.invoice_line_ids:
            if line.product_id and line.product_id.name.lower() == 'down payment':
                return True
        return False

    def print_invoice_pdf(self):
        self.ensure_one()
        if self.has_downpayment_product():
            report_name = 'custom_downpayment_invoice.downpayment_invoice_report'
        else:
            report_name = 'account.report_invoice'
        return self.env.ref(report_name).report_action(self)
