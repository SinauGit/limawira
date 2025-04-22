from odoo import api, fields, models


class AccountMove(models.Model):
    """Kelas ini mewarisi "account.move" model dan menambahkan discount_type,
    discount_rate, amount_discount
     """
    _inherit = "account.move"

    discount_type = fields.Selection(
        [('percent', 'Persentase'), ('amount', 'Jumlah')],
        string='Discount Type',
        default='amount')
    discount_rate = fields.Float('Discount', digits=(16, 2),)
    amount_discount = fields.Monetary(string='Diskon', store=True,
                                      compute='_compute_amount', readonly=True,)

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
        """Fungsi untuk menghitung total berdasarkan diskon dan pajak"""
        for move in self:
            total_untaxed, total_untaxed_currency = 0.0, 0.0
            total_tax, total_tax_currency = 0.0, 0.0
            total_residual, total_residual_currency = 0.0, 0.0
            total, total_currency = 0.0, 0.0
            total_to_pay = move.amount_total
            currencies = set()
            amount_discount = 0.0
            
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
            
            # Menghitung jumlah diskon
            if move.move_type in ('in_invoice', 'in_refund'):
                for line in move.invoice_line_ids:
                    price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    amount_discount += (line.price_unit - price_unit) * line.quantity
            
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
            move.amount_discount = amount_discount
            
            # Logika status pembayaran
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
                # We only set 'reversed' state in case of 1 to 1 full
                # reconciliation with a reverse entry; otherwise, we use the
                # regular 'paid' state
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
        """Fungsi ini menghitung nilai diskon berdasarkan perubahan pada
        discount_type, discount_rate dan invoice_line_ids"""
        for inv in self:
            if inv.move_type in ('in_invoice', 'in_refund'):
                if inv.discount_type == 'percent':
                    discount_totals = 0
                    for line in inv.invoice_line_ids:
                        line.discount = inv.discount_rate
                        total_price = line.price_unit * line.quantity
                        discount_total = total_price - line.price_subtotal
                        discount_totals = discount_totals + discount_total
                        inv.amount_discount = discount_totals
                        line._compute_totals()
                else:
                    total = 0.0
                    for line in inv.invoice_line_ids:
                        total += (line.quantity * line.price_unit)
                    if inv.discount_rate != 0 and total > 0:
                        discount = (inv.discount_rate / total) * 100
                    else:
                        discount = inv.discount_rate
                    for line in inv.invoice_line_ids:
                        line.discount = discount
                        inv.amount_discount = inv.discount_rate
                        line._compute_totals()
                inv._compute_tax_totals()

    def supply_rate(self):
        """Alias untuk _supply_rate"""
        self._supply_rate()

    def button_dummy(self):
        """Metode button_dummy untuk memperbarui perhitungan diskon"""
        self.supply_rate()
        return True


class AccountMoveLine(models.Model):
    """Kelas ini mewarisi "account.move.line" model dan menambahkan field diskon"""
    _inherit = "account.move.line"

    discount = fields.Float(string='Diskon (%)', digits=(16, 20), default=0.0,)
    
    def _compute_totals(self):
        """Menghitung ulang jumlah berdasarkan diskon dan harga"""
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_ids._origin.compute_all(
                price, line.move_id.currency_id, line.quantity, 
                product=line.product_id, partner=line.move_id.partner_id
            )
            line.price_subtotal = taxes['total_excluded']
            line.price_total = taxes['total_included'] 