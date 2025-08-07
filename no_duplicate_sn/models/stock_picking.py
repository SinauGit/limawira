from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        self._validate_serial_numbers()
        return super()._action_done()

    def _validate_serial_numbers(self):
        for picking in self:
            # Skip validation untuk non-incoming operations
            if picking.picking_type_id.code != 'incoming':
                continue
            
            # CRITICAL FIX: Skip validation untuk return operations
            if self._is_return_operation(picking):
                continue
                
            for move_line in picking.move_line_ids:
                if move_line.lot_id and move_line.product_id.tracking == 'serial':
                    
                    existing_serial = self.env['stock.lot'].search([
                        ('name', '=', move_line.lot_id.name),
                        ('product_id', '=', move_line.product_id.id),
                        ('id', '!=', move_line.lot_id.id)
                    ])
                    
                    if existing_serial:
                        raise ValidationError(_(
                            'Cannot validate receipt. Serial Number "%s" for product "%s" '
                            'already exists in the system. Each serial number can only be received once.'
                        ) % (move_line.lot_id.name, move_line.product_id.name))

                    # Check existing moves (only for ACTUAL receipts, not returns)
                    existing_moves = self.env['stock.move.line'].search([
                        ('lot_id.name', '=', move_line.lot_id.name),
                        ('product_id', '=', move_line.product_id.id),
                        ('state', '=', 'done'),
                        ('id', '!=', move_line.id),
                        # IMPORTANT: Only check actual receipts, exclude returns
                        ('picking_id.picking_type_id.code', '=', 'incoming'),
                        ('location_id.usage', 'in', ['supplier', 'production']),  # Actual incoming sources
                    ])
                    
                    if existing_moves:
                        raise ValidationError(_(
                            'Cannot validate receipt. Serial Number "%s" for product "%s" '
                            'has been previously received. Each serial number can only be received once.'
                        ) % (move_line.lot_id.name, move_line.product_id.name))

    def _is_return_operation(self, picking):
        """Detect if this is a return operation"""
        
        # Method 1: Check origin field for 'Return'
        if picking.origin and 'return' in picking.origin.lower():
            return True
        
        # Method 2: Check if source location is customer/supplier
        for move_line in picking.move_line_ids:
            if move_line.location_id.usage in ['customer', 'supplier']:
                return True
        
        # Method 3: Check picking name pattern (Return usually has specific naming)
        if picking.name and ('ret' in picking.name.lower() or 'return' in picking.name.lower()):
            return True
        
        # Method 4: Check if linked to a return wizard/process
        # You can add more specific checks based on your return process
        
        return False

    def button_validate(self):
        self._validate_serial_numbers()
        return super().button_validate()