from odoo import models, api, fields
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _check_down_payment(self):
        """
        Check if the customer requires down payment
        and ensure down payment invoice is paid.
        """
        for order in self:
            if order.partner_id.requires_down_payment:
                dp_invoices = order.invoice_ids.filtered(
                    lambda i: i.move_type == 'out_invoice' 
                    and i.payment_state in ['paid', 'in_payment']
                    and i.is_down_payment
                )
                if not dp_invoices:
                    raise ValidationError(
                        "Down payment is required for this customer. "
                        "Please create and pay the down payment invoice before proceeding."
                    )
