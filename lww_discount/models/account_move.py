from odoo import api, fields, models


class AccountInvoice(models.Model):
    
    _inherit = "account.move"

    discount_type = fields.Selection(
        [('percent', 'All Percentage'), ('amount', 'Amount'), ('line_discount', 'Per Line')],
        string='Discount type',
        default='line_discount')
    discount_rate = fields.Float('Discount Rate', digits=(16, 2))
    amount_discount = fields.Monetary(string='Discount', store=True,
                                      compute='_compute_amount', readonly=True)

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_ids.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_ids.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id')
    def _compute_amount(self):
        """This function computes amount based on taxed,untaxed"""
        for move in self:
            total_untaxed, total_untaxed_currency = 0.0, 0.0
            total_tax, total_tax_currency = 0.0, 0.0
            total_residual, total_residual_currency = 0.0, 0.0
            total, total_currency = 0.0, 0.0
            total_to_pay = move.amount_total
            currencies = set()
            for line in move.line_ids:
                if move.is_invoice(True):
                    # === Invoices ===
                    if line.display_type == 'tax' or (
                            line.display_type == 'rounding' and
                            line.tax_repartition_line_id):
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type in ('product', 'rounding'):
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type == 'payment_term':
                        # Residual amount.
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency
            sign = move.direction_sign
            move.amount_untaxed = sign * (total_untaxed_currency if len(
                currencies) == 1 else total_untaxed)
            move.amount_tax = sign * (
                total_tax_currency if len(currencies) == 1 else total_tax)
            move.amount_total = sign * total_currency
            move.amount_residual = -sign * total_residual_currency
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(
                total) if move.move_type == 'entry' else -total
            move.amount_residual_signed = total_residual
            move.amount_total_in_currency_signed = abs(
                move.amount_total) if move.move_type == 'entry' else -(
                    sign * move.amount_total)
            currency = (len(
                currencies) == 1 and currencies.pop() or
                        move.company_id.currency_id)
            new_pmt_state = 'not_paid' if move.move_type != 'entry' else False
            if move.is_invoice(
                    include_receipts=True) and move.state == 'posted':
                if currency.is_zero(move.amount_residual):
                    if all(payment.is_matched for payment in
                           move._get_reconciled_payments()):
                        new_pmt_state = 'paid'
                    else:
                        new_pmt_state = move._get_invoice_in_payment_state()
                elif currency.compare_amounts(total_to_pay,
                                              abs(total_residual)) != 0:
                    new_pmt_state = 'partial'
            if new_pmt_state == 'paid' and move.move_type in (
                    'in_invoice', 'out_invoice', 'entry'):
                reverse_type = (move.move_type == 'in_invoice' and 'in_refund'
                                or move.move_type == 'out_invoice' and
                                'out_refund' or 'entry')
                reverse_moves = self.env['account.move'].search(
                    [('reversed_entry_id', '=', move.id),
                     ('state', '=', 'posted'),
                     ('move_type', '=', reverse_type)])
                reverse_moves_full_recs = reverse_moves.mapped(
                    'line_ids.full_reconcile_id')
                if reverse_moves_full_recs.mapped(
                        'reconciled_line_ids.move_id').filtered(
                    lambda x: x not in (
                            reverse_moves + reverse_moves_full_recs.mapped(
                        'exchange_move_id'))) == move:
                    new_pmt_state = 'reversed'
            move.payment_state = new_pmt_state

    @api.onchange('discount_type', 'discount_rate', 'invoice_line_ids')
    def _supply_rate(self):

        for inv in self:
            if inv.discount_type == 'percent':
                discount_totals = 0
                for line in inv.invoice_line_ids:
                    line.discount = inv.discount_rate
                    total_price = line.price_unit * line.quantity
                    discount_total = total_price - line.price_subtotal
                    discount_totals = discount_totals + discount_total
                    inv.amount_discount = discount_totals
                    line._compute_totals()
            elif inv.discount_type == 'amount':
                total = 0.0
                for line in inv.invoice_line_ids:
                    total += (line.quantity * line.price_unit)
                if inv.discount_rate != 0:
                    discount = (inv.discount_rate / total) * 100
                else:
                    discount = inv.discount_rate
                for line in inv.invoice_line_ids:
                    line.discount = discount
                    inv.amount_discount = inv.discount_rate
                    line._compute_totals()
            elif inv.discount_type == 'line_discount':
                discount_totals = 0
                for line in inv.invoice_line_ids:
                    total_price = line.price_unit * line.quantity
                    discount_total = total_price * (line.discount / 100)
                    discount_totals += discount_total
                inv.amount_discount = discount_totals
            inv._compute_tax_totals()

    def button_dummy(self):
        """The button_dummy method is intended to perform some action related
        to the supply rate and always return True"""
        self.supply_rate()
        return True


class AccountInvoiceLine(models.Model):
    """This class inherits "account.move.line" model and adds discount field"""
    _inherit = "account.move.line"
    discount = fields.Float(string='Discount (%)', digits=(16, 20), default=0.0)


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange('invoice_line_ids')
    def _onchange_invoice_line_ids(self):
        """Fungsi untuk mengupdate amount_discount saat invoice line berubah"""
        if self.move_type in ['in_invoice', 'in_refund']:
            discount_totals = 0
            for line in self.invoice_line_ids:
                total_price = line.price_unit * line.quantity
                discount_total = total_price * (line.discount / 100)
                discount_totals += discount_total
            self.amount_discount = discount_totals
