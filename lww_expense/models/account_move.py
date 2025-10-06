# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    employee_id = fields.Many2one('hr.employee', string='Employee')

    is_expense_bill = fields.Boolean(
        string='Is Expense Bill',
        default=False,
        store=True,
        readonly=True,
        copy=False,
        help='Indicates if this vendor bill is an expense bill'
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        compute='_compute_department_id',
        store=True,
        readonly=True,
        copy=False,
        index=True,
        help='Department of the user who created this expense bill'
    )
    
    @api.depends('create_uid', 'is_expense_bill')
    def _compute_department_id(self):
        """
        Compute department based on creator's employee record.
        Only applies to expense bills.
        Department is locked at creation time.
        """
        for record in self:
            if record.is_expense_bill and record.move_type == 'in_invoice':
                if record.create_uid and hasattr(record.create_uid, 'employee_id'):
                    employee = record.create_uid.employee_id
                    if employee and employee.department_id:
                        record.department_id = employee.department_id.id
                        continue
                # Fallback: no department found
                record.department_id = False
            else:
                record.department_id = False

    @api.model
    def create(self, vals):
        """
        Auto-handle expense bill creation:
        1. Detect journal with code 'EXP'
        2. Set is_expense_bill flag
        3. Validate user has employee record with department
        """
        
        # Check if journal EXP is being used
        journal_id = vals.get('journal_id')
        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
            if journal.code == 'EXP':
                vals['is_expense_bill'] = True
        
        # Handle expense bill from context
        if self._context.get('default_is_expense_bill'):
            vals['is_expense_bill'] = True
            
            # Auto-set journal EXP if not provided
            if not vals.get('journal_id'):
                exp_journal = self.env['account.journal'].search(
                    [('code', '=', 'EXP'), ('type', '=', 'purchase')], 
                    limit=1
                )
                if exp_journal:
                    vals['journal_id'] = exp_journal.id
                else:
                    raise UserError(_(
                        'Expense Journal (EXP) not found. '
                        'Please create a Purchase Journal with code "EXP".'
                    ))
        
        # Validate expense bill requirements
        # if vals.get('is_expense_bill') and vals.get('move_type') == 'in_invoice':
        #     self._validate_expense_bill_creation()
        
        move = super(AccountMove, self).create(vals)
        
        # Force recompute department for new expense bills
        if move.is_expense_bill and move.move_type == 'in_invoice':
            move._compute_department_id()
            
            # Validate department was assigned
            if not move.department_id:
                raise UserError(_(
                    'Cannot create expense bill: You must be assigned to a department. '
                    'Please contact your HR administrator.'
                ))
            
        return move
    
    def write(self, vals):
        """
        Handle updates:
        1. Prevent changing journal away from EXP for expense bills
        2. Recompute department if needed
        3. Validate permissions
        """
        
        # Prevent clearing is_expense_bill flag
        if 'is_expense_bill' in vals and not vals['is_expense_bill']:
            if any(rec.is_expense_bill for rec in self):
                raise UserError(_(
                    'Cannot change expense bill to regular bill. '
                    'This is not allowed for data integrity.'
                ))
        
        # Check if journal is being changed to EXP
        if 'journal_id' in vals:
            journal = self.env['account.journal'].browse(vals['journal_id'])
            if journal.code == 'EXP':
                vals['is_expense_bill'] = True
            
            # Prevent changing journal from EXP to non-EXP
            if any(rec.is_expense_bill and rec.journal_id.code == 'EXP' for rec in self):
                if journal.code != 'EXP':
                    raise UserError(_(
                        'Cannot change journal for expense bills. '
                        'Expense bills must use the EXP journal.'
                    ))
        
        # Check write permissions for posted bills
        # if any(rec.state == 'posted' and rec.is_expense_bill for rec in self):
        #     if not self._check_expense_bill_edit_rights():
        #         raise AccessError(_(
        #             'You cannot modify posted expense bills. '
        #             'Only managers and admins can edit posted expense bills.'
        #         ))
        
        res = super(AccountMove, self).write(vals)
        
        # Recompute if necessary
        if 'journal_id' in vals or 'is_expense_bill' in vals:
            self._compute_department_id()
            
        return res

    def unlink(self):
        """Prevent deletion of posted expense bills by regular users"""
        for move in self:
            if move.is_expense_bill and move.state == 'posted':
                if not self.env.user.has_group('department_vendor_bill_management.group_department_bill_admin'):
                    raise UserError(_(
                        'You cannot delete posted expense bills. '
                        'Please contact your manager or administrator.'
                    ))
        return super(AccountMove, self).unlink()

    # def button_draft(self):
    #     """Override reset to draft with permission check"""
    #     for move in self:
    #         if move.is_expense_bill and move.state == 'posted':
    #             if not self._check_expense_bill_edit_rights():
    #                 raise AccessError(_(
    #                     'You cannot reset posted expense bills to draft. '
    #                     'Only managers and admins have this permission.'
    #                 ))
    #     return super(AccountMove, self).button_draft()

    # def _check_expense_bill_edit_rights(self):
    #     """
    #     Check if current user can edit expense bills.
    #     Returns True if user is Manager or Admin.
    #     """
    #     return (
    #         self.env.user.has_group('department_vendor_bill_management.group_department_bill_manager') or
    #         self.env.user.has_group('department_vendor_bill_management.group_department_bill_admin')
    #     )

    # def _validate_expense_bill_creation(self):
    #     """
    #     Validate that user can create expense bills.
    #     Raises UserError if validation fails.
    #     """
    #     user = self.env.user
        
    #     # Check if user has required groups
    #     if not (user.has_group('department_vendor_bill_management.group_department_bill_user') or
    #             user.has_group('department_vendor_bill_management.group_department_bill_manager') or
    #             user.has_group('department_vendor_bill_management.group_department_bill_admin')):
    #         raise AccessError(_(
    #             'You do not have permission to create expense bills. '
    #             'Please contact your administrator.'
    #         ))
        
    #     # Check if user has employee record
    #     if not user.employee_id:
    #         raise UserError(_(
    #             'Cannot create expense bill: You are not registered as an employee. '
    #             'Please contact your HR administrator.'
    #         ))
        
    #     # Check if employee has department
    #     if not user.employee_id.department_id:
    #         raise UserError(_(
    #             'Cannot create expense bill: You are not assigned to any department. '
    #             'Please contact your HR administrator.'
    #         ))

    @api.model 
    def _get_user_bills_domain(self):
        """
        Helper method to get appropriate domain based on user role.
        Returns domain list for filtering expense bills.
        """
        user = self.env.user
        base_domain = [('move_type', '=', 'in_invoice'), ('is_expense_bill', '=', True)]

        if user.has_group('department_vendor_bill_management.group_department_bill_admin'):
            # Admin: all expense bills
            return base_domain
            
        elif user.has_group('department_vendor_bill_management.group_department_bill_manager'):
            # Manager: department bills only
            if user.employee_id and user.employee_id.department_id:
                return base_domain + [('department_id', '=', user.employee_id.department_id.id)]
            # Fallback: manager without department sees only own bills
            return base_domain + [('create_uid', '=', user.id)]
            
        else:
            # Regular user: own bills only
            return base_domain + [('create_uid', '=', user.id)]

    @api.constrains('is_expense_bill', 'move_type', 'journal_id')
    def _check_expense_bill_consistency(self):
        """Ensure expense bills use correct journal and move type"""
        for move in self:
            if move.is_expense_bill:
                if move.move_type != 'in_invoice':
                    raise ValidationError(_(
                        'Expense bills must be vendor bills (in_invoice). '
                        'Current type: %s'
                    ) % move.move_type)
                
                if move.journal_id.code != 'EXP':
                    raise ValidationError(_(
                        'Expense bills must use the EXP journal. '
                        'Current journal: %s'
                    ) % move.journal_id.name)