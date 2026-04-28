                                        
from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

                                                                  
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        compute="_compute_project_id",
        store=True,
        readonly=True,
        index=True,
        help="Automatically set from the originating Sales Order's Project."
    )

    @api.depends("invoice_line_ids.sale_line_ids.order_id.project_id", "move_type")
    def _compute_project_id(self):
        for move in self:
            proj = False
            if move.move_type in ("out_invoice", "out_refund"):
                orders = move.invoice_line_ids.mapped("sale_line_ids").mapped("order_id")
                if orders:
                    projs = orders.mapped("project_id")
                    proj = projs[0] if projs else False
            move.project_id = proj


        invoice_line_descriptions = fields.Char(
        string='Descriptions',
        compute='_compute_invoice_line_descriptions',
        store=True,
    )

    @api.depends('invoice_line_ids.custom_description', 'invoice_line_ids.sale_line_ids.is_downpayment')
    def _compute_invoice_line_descriptions(self):
        for move in self:
            descriptions = move.invoice_line_ids.filtered(
                lambda l: l.custom_description
                and not any(sl.is_downpayment for sl in l.sale_line_ids)
            ).mapped('custom_description')
            move.invoice_line_descriptions = ', '.join(descriptions)



                                   
                         
                                     
            
                                         
       

                               
                                           
                                                                     
                                              
                           
                                             
                                                    

                                     
                                                                       
                                         
                                                         
                                            
                                                         
                         
                                               
