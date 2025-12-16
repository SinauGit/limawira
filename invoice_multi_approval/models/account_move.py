from odoo import api, fields, models


class AccountMove(models.Model):
                                                                         
    _inherit = 'account.move'

    approval_ids = fields.One2many('approval.line', 'move_id', string="Lines", help="Approval lines")
    document_fully_approved = fields.Boolean(
        string="Document Fully Approved",
        compute='_compute_document_fully_approved',
        help="Enable/disable to approve document."
    )
    check_approve_ability = fields.Boolean(
        string="Check Approve Ability",
        compute='_compute_check_approve_ability',
        help="Enable/disable to check approve ability."
    )
    is_approved = fields.Boolean(
        string="Is Approved",
        compute='_compute_is_approved',
        help="Enable/disable to compute approved or not."
    )
    page_visibility = fields.Boolean(
        string="Page visibility",
        compute='_compute_page_visibility',
        help=" To compute page visibility."
    )
    users_approved = fields.Boolean(string="Users Approved", help="All the users approved the invoice")

    @api.depends('approval_ids')
    def _compute_page_visibility(self):
                                                                             
        for rec in self:
            rec.page_visibility = True if rec.approval_ids else False

    @api.onchange('partner_id')
    def _onchange_partner_id(self):

                                                                             
        res = super(AccountMove, self)._onchange_partner_id()
        invoice_approval_id = self.env['invoice.approval'].browse(
            self.env.ref('invoice_multi_approval.default_invoice_multi_approval_config').id
        )
        self.approval_ids = None
        approval_managers = self.env['res.users'].search([
            ('groups_id', 'in', self.env.ref('invoice_multi_approval.group_approve_manager').id)
        ])
                                                 
        if invoice_approval_id.approval_enabled:
                                                
            if approval_managers:
                for manager in approval_managers:
                    if manager.id not in self.approval_ids.approver_id.ids:
                        vals = {'approver_id': manager.id}
                        self.approval_ids |= self.approval_ids.new(vals)

                                                            
            if (invoice_approval_id.approve_customer_invoice and self.move_type == 'out_invoice'):
                for user in invoice_approval_id.invoice_approver_ids:
                    if user.id not in self.approval_ids.approver_id.ids:
                        vals = {'approver_id': user.id}
                        self.approval_ids |= self.approval_ids.new(vals)
            elif (invoice_approval_id.approve_vendor_bill and self.move_type == 'in_invoice'):
                for user in invoice_approval_id.bill_approver_ids:
                    if user.id not in self.approval_ids.approver_id.ids:
                        vals = {'approver_id': user.id}
                        self.approval_ids |= self.approval_ids.new(vals)
            elif (invoice_approval_id.approve_customer_credit and self.move_type == 'out_refund'):
                for user in invoice_approval_id.cust_credit_approver_ids:
                    if user.id not in self.approval_ids.approver_id.ids:
                        vals = {'approver_id': user.id}
                        self.approval_ids |= self.approval_ids.new(vals)
            elif (invoice_approval_id.approve_vendor_credit and self.move_type == 'in_refund'):
                for user in invoice_approval_id.vend_credit_approver_ids:
                    if user.id not in self.approval_ids.approver_id.ids:
                        vals = {'approver_id': user.id}
                        self.approval_ids |= self.approval_ids.new(vals)
        return res

                                                              
    @api.depends('move_type', 'approval_ids.approver_id')
    def _compute_check_approve_ability(self):
                                                                                       
        config = self.env.ref('invoice_multi_approval.default_invoice_multi_approval_config', raise_if_not_found=False)
        current_user = self.env.user
        for rec in self:
            can = False
            if config:
                require_map = {
                    'out_invoice': bool(config.approve_customer_invoice),
                    'in_invoice': bool(config.approve_vendor_bill),                                
                    'out_refund': bool(config.approve_customer_credit),
                    'in_refund': bool(config.approve_vendor_credit),
                }
                require = require_map.get(rec.move_type, False)
                if require:
                                                         
                    can = any(line.approver_id.id == current_user.id for line in rec.approval_ids)
            rec.check_approve_ability = can

    def action_invoice_approve(self):
                                                                                           
        self.ensure_one()
        current_user = self.env.uid
        for approval_id in self.approval_ids:
            if current_user == approval_id.approver_id.id:
                approval_id.update({'approval_status': True})

        config = self.env.ref('invoice_multi_approval.default_invoice_multi_approval_config', raise_if_not_found=False)
        approved_users = set(self.approval_ids.filtered(lambda item: item.approval_status).approver_id.ids)

        if config:
            if self.move_type == 'out_invoice':
                required_users = set(config.invoice_approver_ids.ids)
            elif self.move_type == 'in_invoice':                       
                required_users = set(config.bill_approver_ids.ids)
            elif self.move_type == 'out_refund':
                required_users = set(config.cust_credit_approver_ids.ids)
            elif self.move_type == 'in_refund':
                required_users = set(config.vend_credit_approver_ids.ids)
            else:
                required_users = set()

                                                    
            self.users_approved = (approved_users == required_users)

        return True

    def _compute_is_approved(self):

                                                                 
        for rec in self:
            current_user = rec.env.uid
            if rec.invoice_line_ids and rec.approval_ids:
                for approval_id in rec.approval_ids:
                    if current_user == approval_id.approver_id.id:
                        if approval_id.approval_status:
                            rec.is_approved = True
                            break
                        else:
                            rec.is_approved = False
                    else:
                        rec.is_approved = False
            else:
                rec.is_approved = False

    @api.depends('approval_ids')
    def _compute_document_fully_approved(self):

                                                     
        for rec in self:
            length_approval_ids = len(rec.approval_ids)
            approval_ids = rec.approval_ids
            approve_lines = approval_ids.filtered(lambda item: item.approval_status)
            length_approve_lines = len(approve_lines)
            rec.document_fully_approved = True if length_approval_ids == length_approve_lines else False
            approval_managers = self.env['res.users'].search([
                ('groups_id', 'in', self.env.ref('invoice_multi_approval.group_approve_manager').id)
            ]).ids
            for approval in approve_lines:
                if approval.approver_id.id in approval_managers:
                    rec.document_fully_approved = True
            if rec.users_approved:
                rec.document_fully_approved = True

    @api.model_create_multi
    def create(self, vals_list):



                          
        res = super(AccountMove, self).create(vals_list)
        res._onchange_partner_id()
        return res
