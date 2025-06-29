# models/account_move.py
from odoo import models, fields, api, _

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create untuk update section name di invoice"""
        moves = super().create(vals_list)
        
        for move in moves:
            # Update section name untuk down payment invoices
            section_lines = move.line_ids.filtered(
                lambda l: l.display_type == 'line_section' and 'Down Payment' in (l.name or '')
            )
            for section in section_lines:
                section.name = _('test')
        
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
        """Override create untuk copy payment_type dan sequence dari SO line"""
        lines = super().create(vals_list)
        
        for line in lines:
            # Handle section lines
            if line.display_type == 'line_section' and line.is_downpayment:
                line.name = _('Test')
            
            # Handle down payment lines
            elif line.is_downpayment and line.sale_line_ids:
                # Copy payment_type dan sequence dari SO line
                so_line = line.sale_line_ids[0]
                if hasattr(so_line, 'payment_type'):
                    line.payment_type = so_line.payment_type
                if hasattr(so_line, 'payment_sequence'):
                    line.payment_sequence = so_line.payment_sequence
                
                # Update name berdasarkan payment_type
                line._update_downpayment_name()
        
        return lines
    
    def _update_downpayment_name(self):
        """Update name field untuk down payment lines"""
        self.ensure_one()
        if not self.is_downpayment:
            return
            
        if self.payment_type == 'installment':
            if self.payment_sequence > 1:
                self.name = _("Termin %s", self.payment_sequence)
            else:
                self.name = _("Termin")
        else:
            if self.payment_sequence > 1:
                self.name = _("Down Payment %s", self.payment_sequence)
            else:
                self.name = _("Down Payment")
    
    def write(self, vals):
        """Override write untuk handle perubahan payment_type"""
        result = super().write(vals)
        
        if 'payment_type' in vals or 'payment_sequence' in vals:
            for line in self:
                if line.is_downpayment:
                    line._update_downpayment_name()
        
        return result