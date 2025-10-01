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

    @api.depends('create_uid')
    def _compute_department_id(self):
        """Compute department based on create_uid"""
        for record in self:
            if record.create_uid and record.create_uid.employee_id and record.create_uid.employee_id.department_id:
                record.department_id = record.create_uid.employee_id.department_id
            else:
                record.department_id = False

    @api.model
    def create(self, vals):
        """Auto-assign department when creating vendor bill"""
        move = super().create(vals)
        
        # Force compute department for vendor bills
        if move.move_type == 'in_invoice':
            move._compute_department_id()
            
        return move

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