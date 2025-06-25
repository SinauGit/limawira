from odoo import models

class AccountMove(models.Model):
    _inherit = 'account.move'

    def has_exactly_one_down_payment(self):
        """
        Check if invoice has exactly one down payment line
        Returns True only if there's exactly 1 down payment line
        """
        down_payment_count = 0
        for line in self.invoice_line_ids:
            # Check in line name
            if line.name and 'down payment' in line.name.lower():
                down_payment_count += 1
            # Check in product name
            elif line.product_id and 'down payment' in line.product_id.name.lower():
                down_payment_count += 1
        
        return down_payment_count == 1

    def has_down_payment(self):
        """
        Legacy method - kept for backward compatibility
        Check if invoice has any down payment lines
        """
        for line in self.invoice_line_ids:
            if 'down payment' in (line.name or '').lower() or (line.product_id and 'down payment' in line.product_id.name.lower()):
                return True
        return False

    def get_down_payment_count(self):
        """
        Get the exact count of down payment lines
        """
        count = 0
        for line in self.invoice_line_ids:
            if line.name and 'down payment' in line.name.lower():
                count += 1
            elif line.product_id and 'down payment' in line.product_id.name.lower():
                count += 1
        return count

    def get_related_sale_order_lines(self):
        """
        Get related sale order lines based on invoice origin
        """
        self.ensure_one()
        if not self.invoice_origin:
            return []
        
        SaleOrder = self.env['sale.order']
        sale_order = SaleOrder.search([('name', '=', self.invoice_origin)], limit=1)
        return sale_order.order_line if sale_order else []

    def should_show_downpayment_template(self):
        """
        Main method to determine if downpayment template should be shown
        Returns True only if there's exactly 1 down payment line
        """
        return self.has_exactly_one_down_payment() and bool(self.get_related_sale_order_lines())