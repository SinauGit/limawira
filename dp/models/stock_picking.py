from odoo import models, api, _
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.constrains('state')
    def _check_down_payment_before_delivery(self):
        """
        Prevent delivery validation if the customer requires down payment
        and the payment is not completed.
        """
        for picking in self:
            if picking.state == 'done' and picking.sale_id:
                sale_order = picking.sale_id
                if sale_order.partner_id.requires_down_payment:
                    if sale_order.invoice_status != 'invoiced':
                        raise ValidationError(
                            _("You cannot validate this delivery. Down payment has not been received "
                              "for this customer who requires advance payment.")
                        )
