from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        self._validate_serial_numbers()
        return super()._action_done()

    def _validate_serial_numbers(self):

        for picking in self:
            if picking.picking_type_id.code != 'incoming':
                continue
                
            for move_line in picking.move_line_ids:
                if move_line.lot_id and move_line.product_id.tracking == 'serial':
                    existing_serial = self.env['stock.production.lot'].search([
                        ('name', '=', move_line.lot_id.name),
                        ('product_id', '=', move_line.product_id.id),
                        ('id', '!=', move_line.lot_id.id)
                    ])
                    
                    if existing_serial:
                        raise ValidationError(_(
                            'Cannot validate receipt. Serial Number "%s" for product "%s" '
                            'already exists in the system. Each serial number can only be received once.'
                        ) % (move_line.lot_id.name, move_line.product_id.name))

                    existing_moves = self.env['stock.move.line'].search([
                        ('lot_id.name', '=', move_line.lot_id.name),
                        ('product_id', '=', move_line.product_id.id),
                        ('state', '=', 'done'),
                        ('id', '!=', move_line.id)
                    ])
                    
                    if existing_moves:
                        raise ValidationError(_(
                            'Cannot validate receipt. Serial Number "%s" for product "%s" '
                            'has been previously processed in the system. Each serial number can only be received once.'
                        ) % (move_line.lot_id.name, move_line.product_id.name))

    def button_validate(self):

        self._validate_serial_numbers()
        return super().button_validate()