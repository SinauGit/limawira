from odoo import models, api, fields
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _check_down_payment(self):
        """
        Check if the order contains products requiring down payment
        and ensure down payment invoice is paid.
        """
        for order in self:
            dp_products = order.order_line.filtered(
                lambda l: l.product_id.requires_down_payment
            )
            if dp_products:
                dp_invoices = order.invoice_ids.filtered(
                    lambda i: i.move_type == 'out_invoice' 
                    and i.payment_state in ['paid', 'in_payment']
                    and i.is_down_payment
                )
                if not dp_invoices:
                    raise ValidationError(
                        "Down payment is required for some products in this order. "
                        "Please create and pay the down payment invoice before proceeding."
                    )
