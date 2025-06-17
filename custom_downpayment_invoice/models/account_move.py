from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    sale_order_line_ids = fields.One2many(
        comodel_name='sale.order.line',
        inverse_name='order_id',
        string='Sale Order Lines',
        compute='_compute_sale_order_lines',
        store=True,
    )

    @api.depends('invoice_origin')
    def _compute_sale_order_lines(self):
        for record in self:
            sale_order_lines = self.env['sale.order.line']
            if record.invoice_origin:
                sale_orders = self.env['sale.order'].search([('name', '=', record.invoice_origin)])
                sale_order_lines = sale_orders.mapped('order_line')
            record.sale_order_line_ids = sale_order_lines
