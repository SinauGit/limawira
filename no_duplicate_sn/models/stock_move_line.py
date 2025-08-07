from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.constrains('lot_id', 'product_id')
    def _check_serial_number_uniqueness(self):
        for line in self:
            if line.lot_id and line.product_id.tracking == 'serial':
                
                # Skip validasi untuk outgoing movements
                if line.location_dest_id.usage in ['customer', 'supplier', 'inventory', 'production', 'transit']:
                    continue
                
                # Skip validasi untuk internal transfers
                if line.location_id.usage == 'internal' and line.location_dest_id.usage == 'internal':
                    continue
                
                # CRITICAL: Skip validasi untuk return operations
                if line.location_id.usage in ['customer', 'supplier'] and line.location_dest_id.usage == 'internal':
                    continue
                
                # Additional check: Skip if this is part of a return picking
                if line.picking_id and self._is_return_picking(line.picking_id):
                    continue
                
                existing_moves = self.env['stock.move.line'].search([
                    ('lot_id', '=', line.lot_id.id),
                    ('product_id', '=', line.product_id.id),
                    ('id', '!=', line.id),
                    ('state', '=', 'done'),
                    # Exclude return operations from search
                    ('location_id.usage', 'in', ['supplier', 'production', 'internal']),
                ])
                
                if existing_moves:
                    raise ValidationError(_(
                        'Serial Number "%s" for product "%s" already exists in the system. '
                        'Each serial number can only be received once.'
                    ) % (line.lot_id.name, line.product_id.name))

    def _is_return_picking(self, picking):
        """Check if picking is a return"""
        if not picking:
            return False
            
        # Check origin
        if picking.origin and 'return' in picking.origin.lower():
            return True
            
        # Check source locations
        for move_line in picking.move_line_ids:
            if move_line.location_id.usage in ['customer', 'supplier']:
                return True
                
        return False

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._check_serial_number_uniqueness()
        return lines

    def write(self, vals):
        result = super().write(vals)
        if 'lot_id' in vals or 'product_id' in vals:
            self._check_serial_number_uniqueness()
        return result