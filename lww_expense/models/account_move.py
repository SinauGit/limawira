# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Add department field as related field
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        compute='_compute_department_id',
        store=True,
        readonly=True,
        help='Department of the user who created this vendor bill'
    )
    
    @api.depends('create_uid', 'journal_id')
    def _compute_department_id(self):
        """Compute department based on create_uid only for journal with code 'EXP'"""
        for record in self:
            # Check if journal code is "EXP"
            if (record.journal_id and 
                record.journal_id.code == 'EXP' and
                record.create_uid and 
                record.create_uid.employee_id and 
                record.create_uid.employee_id.department_id):
                record.department_id = record.create_uid.employee_id.department_id
            else:
                record.department_id = False

    @api.model
    def create(self, vals):
        """Auto-assign department when creating vendor bill with EXP journal"""
        move = super().create(vals)
        
        # Force compute department for vendor bills with EXP journal
        if (move.move_type == 'in_invoice' and 
            move.journal_id and 
            move.journal_id.code == 'EXP'):
            move._compute_department_id()
            
        return move
    
    def write(self, vals):
        """Recompute department if journal changed to/from EXP"""
        res = super().write(vals)
        
        # Recompute if journal_id changed
        if 'journal_id' in vals:
            self._compute_department_id()
            
        return res

    @api.model 
    def _get_user_bills_domain(self):
        """Helper method untuk mendapatkan domain user bills"""
        is_admin = self.env.user.has_group('department_vendor_bill_management.group_department_bill_admin')
        is_manager = self.env.user.has_group('department_vendor_bill_management.group_department_bill_manager')

        base = [('move_type', '=', 'in_invoice')]

        if is_admin:
            # Admin: tidak dibatasi di helper (state dibatasi via action/rule)
            return base
        elif is_manager:
            user_dept = self.env.user.employee_id.department_id if self.env.user.employee_id else False
            if user_dept:
                return base + [('department_id', '=', user_dept.id)]
            # ✔ Fallback aman: Manager tanpa department → hanya bill miliknya
            return base + [('create_uid', '=', self.env.user.id)]
        else:
            # User biasa: hanya bill sendiri
            return base + [('create_uid', '=', self.env.user.id)]
        
        return []