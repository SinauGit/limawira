                       
                                                                             
 
                                    
 
                                                                                
                                                          
 
                                                        
                                                 
 
                                                                    
                                                                   
                                                                  
                                                                  
 
                                                                             
                                       
                                                
 
                                                                             
from odoo import fields, models


class ApprovalLine(models.Model):
                                                                    
    _name = 'approval.line'
    _description = 'Approval Line In Move'

    move_id = fields.Many2one('account.move', string="Approval lines", help="Approval line")
    approver_id = fields.Many2one('res.users', string='Approver', help="Approver of the invoice")
    approval_status = fields.Boolean(string='Status', help="Status of approvals")
