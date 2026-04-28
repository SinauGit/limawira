from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
                                              
    custom_description = fields.Text(
        string='Description',
        store=True,
        readonly=False
    )

    @api.onchange('product_template_id', 'custom_description')
    def _onchange_custom_description(self):
                                                                     
        if self.product_template_id and not self.custom_description:
            self.custom_description = self.product_template_id.name

    @api.model_create_multi
    def create(self, vals_list):
                                                                                
        for vals in vals_list:
            if vals.get('product_template_id') and not vals.get('custom_description'):
                product = self.env['product.template'].browse(vals['product_template_id'])
                vals['custom_description'] = product.name
        return super().create(vals_list)

    def write(self, vals):
                                                                        
        res = super().write(vals)
        for record in self:
            if record.product_template_id and not record.custom_description:
                record.custom_description = record.product_template_id.name
        return res
    
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
                                              
    custom_description = fields.Text(
        string='Description',
        compute='_compute_custom_description',
        inverse='_inverse_custom_description',
        store=True,
        readonly=False,
    )

    @api.depends('sale_line_ids.custom_description', 'move_id.move_type')
    def _compute_custom_description(self):
        for line in self:
            if line.move_id.move_type in ('out_invoice', 'out_refund') and line.sale_line_ids:
                line.custom_description = line.sale_line_ids[:1].custom_description
            # vendor bill: tidak di-overwrite, biarkan nilai yang sudah ada

    def _inverse_custom_description(self):
        pass  # store=True sudah handle penyimpanan

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    order_line_descriptions = fields.Char(
        string='Descriptions',
        compute='_compute_order_line_descriptions',
        store=True,
    )

    @api.depends('order_line.custom_description')
    def _compute_order_line_descriptions(self):
        for order in self:
            descriptions = order.order_line.filtered(
                lambda l: l.custom_description
            ).mapped('custom_description')
            order.order_line_descriptions = ', '.join(descriptions)                                                    