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
        # MULTI-COMPANY: Department bisa shared atau per-company
        check_company=False,  # Allow shared departments
        help='Department of the user who created this expense bill'
    )
    
    @api.depends('create_uid', 'is_expense_bill')
    def _compute_department_id(self):
        """
        Compute department based on creator's employee record.
        Only applies to expense bills.
        Department is locked at creation time.
        
        MULTI-COMPANY NOTE:
        - Department validation terhadap company dilakukan di constraint
        - Compute hanya assign department, tidak validate company
        - Ini memungkinkan shared department (department tanpa company_id)
        """
        for record in self:
            if record.is_expense_bill and record.move_type == 'in_invoice':
                if record.create_uid:
                    # Get employee dari create_uid
                    # PENTING: Gunakan sudo() untuk akses employee cross-company
                    employee = record.create_uid.sudo().employee_id
                    
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
        
        MULTI-COMPANY NOTE:
        - company_id sudah di-handle oleh Odoo standard (required field)
        - Kita hanya perlu validate journal EXP untuk company yang benar
        - Odoo standard akan auto-set company_id jika tidak ada di vals
        """
        
        # Check if journal EXP is being used
        journal_id = vals.get('journal_id')
        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
            # TIDAK PERLU validasi company di sini, Odoo standard sudah handle
            # via _check_company_id constraint
            
            if journal.code == 'EXP':
                vals['is_expense_bill'] = True
        
        # Handle expense bill from context
        if self._context.get('default_is_expense_bill'):
            vals['is_expense_bill'] = True
            
            # Auto-set journal EXP if not provided
            if not vals.get('journal_id'):
                # Get company_id - biarkan Odoo standard handle default company
                # Gunakan self.env.company (current company in context)
                company = self.env.company
                
                # Search journal EXP untuk current company
                exp_journal = self.env['account.journal'].search([
                    ('code', '=', 'EXP'),
                    ('type', '=', 'purchase'),
                    ('company_id', '=', company.id)
                ], limit=1)
                
                if exp_journal:
                    vals['journal_id'] = exp_journal.id
                else:
                    raise UserError(_(
                        'Expense Journal (EXP) not found for company "%s". '
                        'Please create a Purchase Journal with code "EXP" for this company.'
                    ) % company.name)
        
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
        
        MULTI-COMPANY NOTE:
        - company_id change sudah di-block oleh Odoo standard untuk posted entries
        - Journal change validation akan di-handle oleh constraint
        """
        
        # Prevent clearing is_expense_bill flag
        if 'is_expense_bill' in vals and not vals['is_expense_bill']:
            if any(rec.is_expense_bill for rec in self):
                raise UserError(_(
                    'Cannot change expense bill to regular bill. '
                    'This is not allowed for data integrity.'
                ))
        
        # Check if journal is being changed
        if 'journal_id' in vals:
            journal = self.env['account.journal'].browse(vals['journal_id'])
            
            # TIDAK perlu manual check company, constraint akan handle
            
            if journal.code == 'EXP':
                vals['is_expense_bill'] = True
            
            # Prevent changing journal from EXP to non-EXP
            if any(rec.is_expense_bill and rec.journal_id.code == 'EXP' for rec in self):
                if journal.code != 'EXP':
                    raise UserError(_(
                        'Cannot change journal for expense bills. '
                        'Expense bills must use the EXP journal.'
                    ))
        
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

    @api.model 
    def _get_user_bills_domain(self):
        """
        Helper method to get appropriate domain based on user role.
        Returns domain list for filtering expense bills.
        
        MULTI-COMPANY NOTE:
        - TIDAK perlu manual add company_id ke domain
        - Odoo standard akan auto-inject company filter based on allowed_company_ids
        - Kita hanya define business logic filter (role-based)
        """
        user = self.env.user
        
        # Base domain - TANPA company filter (Odoo handle otomatis)
        base_domain = [
            ('move_type', '=', 'in_invoice'),
            ('is_expense_bill', '=', True)
        ]

        if user.has_group('department_vendor_bill_management.group_department_bill_admin'):
            # Admin: all expense bills (Odoo auto-filter by allowed companies)
            return base_domain
            
        elif user.has_group('department_vendor_bill_management.group_department_bill_manager'):
            # Manager: department bills only
            if user.employee_id and user.employee_id.department_id:
                department = user.employee_id.department_id
                return base_domain + [('department_id', '=', department.id)]
                
            # Fallback: manager without department sees only own bills
            return base_domain + [('create_uid', '=', user.id)]
            
        else:
            # Regular user: own bills only
            return base_domain + [('create_uid', '=', user.id)]

    @api.constrains('is_expense_bill', 'move_type', 'journal_id', 'company_id', 'department_id')
    def _check_expense_bill_consistency(self):
        """
        Ensure expense bills use correct journal and move type.
        
        MULTI-COMPANY NOTE:
        - Constraint ini validate business rules SETELAH Odoo standard validate
        - Odoo standard sudah validate journal.company_id == move.company_id
        - Kita hanya perlu validate department consistency
        """
        for move in self:
            if move.is_expense_bill:
                # Check move type
                if move.move_type != 'in_invoice':
                    raise ValidationError(_(
                        'Expense bills must be vendor bills (in_invoice). '
                        'Current type: %s'
                    ) % move.move_type)
                
                # Check journal code
                if move.journal_id.code != 'EXP':
                    raise ValidationError(_(
                        'Expense bills must use the EXP journal. '
                        'Current journal: %s'
                    ) % move.journal_id.name)
                
                # MULTI-COMPANY: Journal-Company validation sudah di-handle Odoo standard
                # via _check_company_id, TIDAK perlu duplicate check
                
                # MULTI-COMPANY: Check department consistency
                # Department bisa:
                # 1. Tanpa company (shared) -> OK
                # 2. Dengan company -> harus sama dengan move.company_id
                if move.department_id and move.department_id.company_id:
                    if move.department_id.company_id != move.company_id:
                        raise ValidationError(_(
                            'Department "%(dept)s" belongs to company "%(dept_co)s" '
                            'but this expense bill is for company "%(bill_co)s".\n\n'
                            'Please ensure your employee is assigned to a department '
                            'in the correct company.'
                        ) % {
                            'dept': move.department_id.name,
                            'dept_co': move.department_id.company_id.name,
                            'bill_co': move.company_id.name
                        })
    
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        """
        Override name_search untuk respect multi-company context.
        
        MULTI-COMPANY NOTE:
        - Odoo standard sudah inject company filter via allowed_company_ids
        - Override ini hanya untuk custom business logic jika diperlukan
        """
        # Biarkan Odoo standard handle multi-company filtering
        return super()._name_search(
            name=name, args=args, operator=operator, 
            limit=limit, name_get_uid=name_get_uid
        )