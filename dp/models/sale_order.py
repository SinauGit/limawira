from odoo import models
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _check_down_payment(self):
        """
        Check if the order contains products requiring down payment
        and ensure invoice status is 'Paid'.
        """
        for order in self:
            if any(line.product_id.requires_down_payment for line in order.order_line):
                if order.invoice_status != 'invoiced':
                    raise ValidationError(
                        "This order contains products requiring down payment. "
                        "Please ensure the invoice is fully paid before proceeding."
                    )
