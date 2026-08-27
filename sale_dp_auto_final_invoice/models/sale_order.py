from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends(
        'order_line.invoice_lines.price_total',
        'order_line.invoice_lines.move_id.state',
    )
    def _compute_invoice_status(self):
        super()._compute_invoice_status()
        for order in self:
            if order.invoice_status != 'to invoice':
                continue
            downpayment_lines = order.order_line.filtered(
                lambda line: line.is_downpayment and not line.display_type
            )
            if not downpayment_lines:
                continue
            invoiced_amount = sum(
                downpayment_lines.invoice_lines.filtered(
                    lambda line: line.move_id.state != 'cancel'
                ).mapped('price_total')
            )
            if order.currency_id.compare_amounts(invoiced_amount, order.amount_total) >= 0:
                order.invoice_status = 'invoiced'
