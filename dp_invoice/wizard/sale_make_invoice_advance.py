                                     
from odoo import models, fields, api, _

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"
    
    payment_type = fields.Selection([
        ('down_payment', 'Down Payment'),
        ('installment', 'Termin'),
    ], string='Payment Type', default='down_payment', required=True)
    
    def _prepare_base_downpayment_line_values(self, order):
                                                                      
        values = super()._prepare_base_downpayment_line_values(order)
        values.update({
            'payment_type': self.payment_type,
        })
        return values
    
    def _prepare_down_payment_section_values(self, order):
                                                                              
        values = super()._prepare_down_payment_section_values(order)
        values['name'] = _('Down Payment / Termin')
        return values
    
    def _get_down_payment_description(self, order):
                                                           
        self.ensure_one()
        context = {'lang': order.partner_id.lang}
        
        if self.payment_type == 'installment':
            if self.advance_payment_method == 'percentage':
                name = _("Termin of %s%%", self.amount)
            else:
                name = _('Termin')
        else:
                                                    
            return super()._get_down_payment_description(order)
        
        del context
        return name