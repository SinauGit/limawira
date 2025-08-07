from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.constrains('lot_id', 'product_id')
    def _check_serial_number_uniqueness(self):
        for line in self:
            if line.lot_id and line.product_id.tracking == 'serial':
                # Skip validasi berdasarkan picking type
                picking = line.picking_id
                if picking:
                    # Skip untuk outgoing, return, dan internal transfers
                    if picking.picking_type_id.code in ['outgoing', 'internal']:
                        continue
                    
                    # Khusus untuk return operations
                    if 'return' in picking.origin.lower() if picking.origin else False:
                        continue
                
                # Fallback ke location-based validation
                if line.location_dest_id.usage in ['customer', 'supplier', 'inventory', 'production', 'transit']:
                    continue
                
                if line.location_id.usage == 'internal' and line.location_dest_id.usage == 'internal':
                    continue
                
                # Return operations
                if line.location_id.usage in ['customer', 'supplier'] and line.location_dest_id.usage == 'internal':
                    continue
                
                existing_moves = self.env['stock.move.line'].search([
                    ('lot_id', '=', line.lot_id.id),
                    ('product_id', '=', line.product_id.id),
                    ('id', '!=', line.id),
                    ('state', '=', 'done')
                ])
                
                if existing_moves:
                    raise ValidationError(_(
                        'Serial Number "%s" for product "%s" already exists in the system. '
                        'Each serial number can only be received once.'
                    ) % (line.lot_id.name, line.product_id.name))