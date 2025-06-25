from odoo import models

class AccountMove(models.Model):
    _inherit = 'account.move'

    def has_down_payment(self):
        for line in self.invoice_line_ids:
            if 'down payment' in (line.name or '').lower() or (line.product_id and 'down payment' in line.product_id.name.lower()):
                return True
        return False

    def count_down_payment_products(self):
        count = 0
        for line in self.invoice_line_ids:
            if line.product_id and 'down payment' in line.product_id.name.lower():
                count += 1
        return count

    def get_related_sale_order_lines(self):
        self.ensure_one()
        if not self.invoice_origin:
            return []
        SaleOrder = self.env['sale.order']
        sale_order = SaleOrder.search([('name', '=', self.invoice_origin)], limit=1)
        return sale_order.order_line if sale_order else []

    def _get_name_invoice_report(self):
        count_dp = self.count_down_payment_products()
        # Jika ada tepat 1 produk Down Payment, gunakan template custom
        if count_dp == 1:
            return 'downpayment_report.report_invoice_downpayment_document'
        # Jika ada lebih dari 1 atau tidak ada produk Down Payment, gunakan template standar Odoo
        return 'account.report_invoice_document'
