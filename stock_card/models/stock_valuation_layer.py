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