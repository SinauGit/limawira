from odoo import api, fields, models

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'
    
    partner_id = fields.Many2one(
        'res.partner', 
        string='Partner',
        related='stock_move_id.picking_id.partner_id', 
        store=True,
        readonly=True
    )
    
    credit = fields.Monetary(
        string='Credit',
        compute='_compute_credit_debit',
        store=True,
        currency_field='currency_id'
    )
    
    debit = fields.Monetary(
        string='Debit',
        compute='_compute_credit_debit',
        store=True,
        currency_field='currency_id'
    )

    quantity_credit = fields.Float(
        string='Quantity Credit',
        compute='_compute_quantity_credit_debit',
        store=True,
        digits='Product Unit of Measure'
    )

    quantity_debit = fields.Float(
        string='Quantity Debit',
        compute='_compute_quantity_credit_debit',
        store=True,
        digits='Product Unit of Measure'
    )
    
    @api.depends('value')
    def _compute_credit_debit(self):
        for record in self:
            if record.value > 0:
                record.debit = record.value
                record.credit = 0.0
            else:
                record.debit = 0.0
                record.credit = abs(record.value)

    @api.depends('quantity')
    def _compute_quantity_credit_debit(self):
        for record in self:
            if record.quantity > 0:
                record.quantity_debit = record.quantity
                record.quantity_credit = 0.0
            else:
                record.quantity_debit = 0.0
                record.quantity_credit = abs(record.quantity) 