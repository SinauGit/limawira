# -*- coding: utf-8 -*-
from odoo import models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def create_invoices(self):
        """Extend the standard down payment invoice creation.

        Standard behavior: creates a down payment invoice (percentage,
        fixed, or delivered) and returns the action to view it.

        Extension: when the down payment method is 'percentage', check
        whether the cumulative amount already invoiced through down
        payment lines on the order has reached (or exceeded) the order's
        untaxed total. If so, automatically trigger the creation of the
        final (regular) invoice, which deducts the existing down
        payments. This ensures the order's invoice_status correctly
        reflects 'Fully Invoiced' once the customer has been billed for
        the full amount via down payment(s), instead of staying stuck on
        'To Invoice'.
        """
        action = super().create_invoices()

        if self.advance_payment_method == 'percentage':
            order = self.sale_order_ids

            downpayment_lines = order.order_line.filtered(
                lambda line: line.is_downpayment and not line.display_type
            )
            invoiced_amount = sum(
                downpayment_lines.invoice_lines.filtered(
                    lambda line: line.move_id.state != 'cancel'
                ).mapped('price_subtotal')
            )

            if order.currency_id.compare_amounts(invoiced_amount, order.amount_untaxed) >= 0:
                order._create_invoices(final=True)

        return action
