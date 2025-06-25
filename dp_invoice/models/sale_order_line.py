# models/sale_order_line.py
from odoo import models, fields, api, _
from odoo.tools import format_date

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    payment_type = fields.Selection([
        ('down_payment', 'Down Payment'),
        ('installment', 'Termin'),
    ], string='Payment Type', default='down_payment')
    
    payment_sequence = fields.Integer(string='Payment Sequence', default=1)
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create untuk auto-set sequence"""
        lines = super().create(vals_list)
        
        for line in lines:
            if line.is_downpayment and not line.display_type:
                # Auto-set sequence berdasarkan existing down payment lines
                line.payment_sequence = line._get_next_payment_sequence()
        
        return lines
    
    def _get_next_payment_sequence(self):
        """Get next sequence number untuk payment type ini"""
        if not self.order_id:
            return 1
        
        # Cari semua down payment lines di SO ini dengan payment_type yang sama
        existing_lines = self.order_id.order_line.filtered(
            lambda l: l.is_downpayment 
            and not l.display_type 
            and l.payment_type == self.payment_type
            and l.id != self.id
        )
        
        if not existing_lines:
            return 1
        
        # Ambil sequence tertinggi dan tambah 1
        max_sequence = max(existing_lines.mapped('payment_sequence') or [0])
        return max_sequence + 1
    
    def _get_downpayment_description(self):
        """Override description untuk include payment_type dan sequence"""
        self.ensure_one()
        
        if self.display_type:
            # Untuk section, tampilkan berdasarkan payment_type yang dominan di SO
            installment_lines = self.order_id.order_line.filtered(
                lambda l: l.is_downpayment and not l.display_type and l.payment_type == 'installment'
            )
            if installment_lines:
                return _("Termin")
            else:
                return _("Down Payment")

        dp_state = self._get_downpayment_state()
        
        # Base name berdasarkan payment_type dan sequence
        if self.payment_type == 'installment':
            if self.payment_sequence > 1:
                base_name = _("Termin %s", self.payment_sequence)
            else:
                base_name = _("Termin")
        else:
            if self.payment_sequence > 1:
                base_name = _("Down Payment %s", self.payment_sequence)
            else:
                base_name = _("Down Payment")
        
        if dp_state == 'draft':
            name = _(
                "%(base_name)s: %(date)s (Draft)",
                base_name=base_name,
                date=format_date(self.env, self.create_date.date()),
            )
        elif dp_state == 'cancel':
            name = _("%(base_name)s (Cancelled)", base_name=base_name)
        else:
            invoice = self._get_invoice_lines().filtered(
                lambda aml: aml.quantity >= 0
            ).move_id.filtered(lambda move: move.move_type == 'out_invoice')
            if len(invoice) == 1 and invoice.payment_reference and invoice.invoice_date:
                name = _(
                    "%(base_name)s (ref: %(reference)s on %(date)s)",
                    base_name=base_name,
                    reference=invoice.payment_reference,
                    date=format_date(self.env, invoice.invoice_date),
                )
            else:
                name = base_name

        return name