# Copyright 2023 Quartile Limited
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _
from odoo import models
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        # Validasi: pastikan setiap move punya source & destination
        for picking in self:
            for move in picking.move_ids_without_package.filtered(lambda m: m.state != 'cancel'):
                if not move.location_id:
                    raise ValidationError(
                        _("Source location is missing for move %(move)s in picking %(picking)s. "
                          "Please set the source location."),
                        params={"move": move.name or move.id, "picking": picking.name},
                    )
                if not move.location_dest_id:
                    raise ValidationError(
                        _("Destination location is missing for move %(move)s in picking %(picking)s. "
                          "Please set the destination location."),
                        params={"move": move.name or move.id, "picking": picking.name},
                    )
                    
        self = self.with_context(validate_analytic=True)
        return super().button_validate()
