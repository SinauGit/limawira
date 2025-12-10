                       
                                                                             
 
                                    
 
                                                                                
                                                          
 
                                                        
                                                 
 
                                                                    
                                                                   
                                                                  
                                                                  
 
                                                                             
                                       
                                                
 
                                                                             
from odoo import api, fields, models


class InvoiceApproval(models.Model):
\
                      
    _name = 'invoice.approval'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Invoice Approval'

    name = fields.Char(
        default='Approval Configuration',
        string="Name",
        help="Approval configuration."
    )

                      
    approve_customer_invoice = fields.Boolean(
        string="Approval on Customer Invoice",
        help='Enable this field for adding the approvals for the customer invoice.'
    )
    invoice_approver_ids = fields.Many2many(
        'res.users', 'invoice_id', string='Invoice Approver',
        domain=lambda self: [
            ('groups_id', 'in', self.env.ref('invoice_multi_approval.group_approver').id)
        ],
        help='In this field you can add the approvers for the customer invoice.'
    )

                 
    approve_vendor_bill = fields.Boolean(
        string="Approval on Vendor Bill",
        help='Enable this field for adding the approvals for the Vendor bill.'
    )
    bill_approver_ids = fields.Many2many(
        'res.users', 'bill_id', string='Bill Approver',
        domain=lambda self: [
            ('groups_id', 'in', self.env.ref('invoice_multi_approval.group_approver').id)
        ],
        help='In this field you can add the approvers for the Vendor bill.'
    )

                          
    approve_customer_credit = fields.Boolean(
        string='Approval on Customer Refund',
        help='Enable this field for adding the approvals for the customer credit note.'
    )
    cust_credit_approver_ids = fields.Many2many(
        'res.users', 'cust_credit_id', string='Customer Credit Note Approver',
        domain=lambda self: [
            ('groups_id', 'in', self.env.ref('invoice_multi_approval.group_approver').id)
        ],
        help='In this field you can add the approvers for the Customer credit note.'
    )

                        
    approve_vendor_credit = fields.Boolean(
        string='Approval on Vendor Refund',
        help='Enable this field for adding the approvals for the Vendor credit note.'
    )
    vend_credit_approver_ids = fields.Many2many(
        'res.users', 'vend_credit_id', string='Vendor Credit Note Approver',
        domain=lambda self: [
            ('groups_id', 'in', self.env.ref('invoice_multi_approval.group_approver').id)
        ],
        help='In this field you can add the approvers for the Vendor credit note.'
    )

                                                             
    approval_enabled = fields.Boolean(
        string='Approval Enabled',
        compute="_compute_approval_enabled",
        help='True if at least one document type requires approval.'
    )

    @api.depends('approve_customer_invoice', 'approve_vendor_bill',
                 'approve_customer_credit', 'approve_vendor_credit')
    def _compute_approval_enabled(self):
                                                                                             
        for rec in self:
            rec.approval_enabled = any((
                rec.approve_customer_invoice,
                rec.approve_vendor_bill,
                rec.approve_customer_credit,
                rec.approve_vendor_credit,
            ))
