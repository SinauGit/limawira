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
                record.department_id = record.create_uid.employee_id.department_id.id
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

    def write(self, vals):
        """Ensure user can only modify vendor bills according to their access level"""
        for record in self:
            if record.move_type == 'in_invoice':
                # Check user access level
                is_admin = self.env.user.has_group('department_vendor_bill_management.group_department_bill_admin')
                is_manager = self.env.user.has_group('department_vendor_bill_management.group_department_bill_manager')
                
                if is_admin:
                    # Admin can modify all bills
                    continue
                elif is_manager:
                    # Manager can modify bills from their department only
                    user_dept = self.env.user.employee_id.department_id if self.env.user.employee_id else False
                    if user_dept and record.department_id and record.department_id != user_dept:
                        raise AccessError(_('You can only modify vendor bills from your department.'))
                else:
                    # Regular user can only modify their own bills
                    if record.create_uid != self.env.user:
                        raise AccessError(_('You can only modify your own vendor bills.'))
        
        return super().write(vals)

    def unlink(self):
        """Ensure proper deletion permissions"""
        for record in self:
            if record.move_type == 'in_invoice':
                # Check user access level
                is_admin = self.env.user.has_group('department_vendor_bill_management.group_department_bill_admin')
                is_manager = self.env.user.has_group('department_vendor_bill_management.group_department_bill_manager')
                
                if is_admin:
                    # Admin can delete all bills
                    continue
                elif is_manager:
                    # Manager can delete bills from their department only
                    user_dept = self.env.user.employee_id.department_id if self.env.user.employee_id else False
                    if user_dept and record.department_id and record.department_id != user_dept:
                        raise AccessError(_('You can only delete vendor bills from your department.'))
                else:
                    # Regular user cannot delete bills
                    raise AccessError(_('You are not allowed to delete vendor bills.'))
        
        return super().unlink()

    @api.model 
    def _get_user_bills_domain(self):
        """Helper method untuk mendapatkan domain user bills"""
        is_admin = self.env.user.has_group('department_vendor_bill_management.group_department_bill_admin')
        is_manager = self.env.user.has_group('department_vendor_bill_management.group_department_bill_manager')
        
        if is_admin:
            # Admin: semua bill dari semua department
            return []
        elif is_manager:
            # Manager: semua bill dari departemen
            user_dept = self.env.user.employee_id.department_id if self.env.user.employee_id else False
            if user_dept:
                return [('department_id', '=', user_dept.id)]
        else:
            # User biasa: hanya bill sendiri
            return [('create_uid', '=', self.env.user.id)]
        
        return []