                        
from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    @api.model_create_multi
    def create(self, vals_list):
                                                                  
        moves = super().create(vals_list)
        
        for move in moves:
                                                             
            section_lines = move.line_ids.filtered(
                lambda l: l.display_type == 'line_section' and 'Down Payment' in (l.name or '')
            )
            for section in section_lines:
                section.name = _('Down Payment / Termin')
        
        return moves

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    payment_type = fields.Selection([
        ('down_payment', 'Down Payment'),
        ('installment', 'Termin'),
    ], string='Payment Type', default='down_payment')
    
    payment_sequence = fields.Integer(string='Payment Sequence', default=1)
    
    @api.model_create_multi
    def create(self, vals_list):
                                                                               
        lines = super().create(vals_list)
        
        for line in lines:
                                  
            if line.display_type == 'line_section' and line.is_downpayment:
                line.name = _('Down Payment / Termin')
            
                                       
            elif line.is_downpayment and line.sale_line_ids:
                                                             
                so_line = line.sale_line_ids[0]
                if hasattr(so_line, 'payment_type'):
                    line.payment_type = so_line.payment_type
                if hasattr(so_line, 'payment_sequence'):
                    line.payment_sequence = so_line.payment_sequence
                
                                                      
                line._update_downpayment_name()
        
        return lines
    
    def _update_downpayment_name(self):
                                                                               
        self.ensure_one()
        if not self.is_downpayment:
            return
            
        if self.payment_type == 'installment':
            if self.payment_sequence > 1:
                self.name = _("Termin %s", self.payment_sequence)
                self.custom_description = _("Termin %s", self.payment_sequence)
            else:
                self.name = _("Termin")
                self.custom_description = _("Termin")
        else:
            if self.payment_sequence > 1:
                self.name = _("Down Payment %s", self.payment_sequence)
                self.custom_description = _("Down Payment %s", self.payment_sequence)
            else:
                self.name = _("Down Payment")
                self.custom_description = _("Down Payment")
    
    def write(self, vals):
                                                                
        result = super().write(vals)
        
        if 'payment_type' in vals or 'payment_sequence' in vals:
            for line in self:
                if line.is_downpayment:
                    line._update_downpayment_name()
        
        return result

    def _prepare_analytic_distribution_line(self, distribution, account_ids, distribution_on_each_plan):
        res = super()._prepare_analytic_distribution_line(distribution, account_ids, distribution_on_each_plan)
        if self.custom_description:
            res['name'] = self.custom_description
        return res