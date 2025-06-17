from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    sale_order_line_ids = fields.Many2many(
        comodel_name='sale.order.line',
        compute='_compute_sale_order_lines',
        string='Sale Order Lines',
    )

    @api.depends('invoice_origin')
    def _compute_sale_order_lines(self):
        for record in self:
            lines = self.env['sale.order.line']
            if record.invoice_origin:
                sale_orders = self.env['sale.order'].search([('name', '=', record.invoice_origin)])
                lines = sale_orders.mapped('order_line')
            record.sale_order_line_ids = lines

