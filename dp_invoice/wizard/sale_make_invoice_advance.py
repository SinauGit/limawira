# wizard/sale_make_invoice_advance.py
from odoo import models, fields, api, _

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"
    
    payment_type = fields.Selection([
        ('down_payment', 'Down Payment'),
        ('installment', 'Termin'),
    ], string='Payment Type', default='down_payment', required=True)
    
    def _prepare_base_downpayment_line_values(self, order):
        """Override untuk include payment_type dalam SO line values"""
        values = super()._prepare_base_downpayment_line_values(order)
        values.update({
            'payment_type': self.payment_type,
        })
        return values
    
    def _prepare_down_payment_section_values(self, order):
        """Override untuk ubah name section menjadi 'Down Payment / Termin'"""
        values = super()._prepare_down_payment_section_values(order)
        values['name'] = _('Down Payment / Termin')
        return values
    
    def _get_down_payment_description(self, order):
        """Override description berdasarkan payment_type"""
        self.ensure_one()
        context = {'lang': order.partner_id.lang}
        
        if self.payment_type == 'installment':
            if self.advance_payment_method == 'percentage':
                name = _("Termin of %s%%", self.amount)
            else:
                name = _('Termin')
        else:
            # Standard behavior - call parent method
            return super()._get_down_payment_description(order)
        
        del context
        return name