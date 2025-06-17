from odoo import models

class AccountMove(models.Model):
    _inherit = 'account.move'

    def has_down_payment(self):
        for line in self.invoice_line_ids:
            if 'down payment' in (line.name or '').lower() or (line.product_id and 'down payment' in line.product_id.name.lower()):
                return True
        return False

    def get_related_sale_order_lines(self):
        self.ensure_one()
        if not self.invoice_origin:
            return []
        SaleOrder = self.env['sale.order']
        sale_order = SaleOrder.search([('name', '=', self.invoice_origin)], limit=1)
        return sale_order.order_line if sale_order else []
