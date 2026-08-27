from odoo import models
class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'
    def create_invoices(self):
        order = self.sale_order_ids
        invoices_before = order.invoice_ids
        action = super().create_invoices()
        if self.advance_payment_method != 'delivered':
            new_invoices = order.invoice_ids - invoices_before
            new_dp_invoices = new_invoices.filtered(
                lambda inv: inv.move_type in ('out_invoice', 'out_refund') and not inv.dp_installment_no
            )
            if new_dp_invoices:
                existing_count = self.env['account.move'].search_count([
                    ('invoice_origin', '=', order.name),
                    ('dp_installment_no', '>', 0),
                    ('state', '!=', 'cancel'),
                ])
                for idx, invoice in enumerate(new_dp_invoices.sorted('id'), start=existing_count + 1):
                    invoice.dp_installment_no = idx
        return action
