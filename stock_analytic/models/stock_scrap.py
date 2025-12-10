                                            
                                                                    
from odoo import models


class StockScrap(models.Model):
    _name = "stock.scrap"
    _inherit = ["stock.scrap", "analytic.mixin"]

    def _prepare_move_values(self):
        res = super()._prepare_move_values()
        res.update({
            "analytic_distribution": self.analytic_distribution,
        })
        
                                                                   
        if not res.get('location_id') and self.location_id:
            res['location_id'] = self.location_id.id
        if not res.get('location_dest_id') and self.scrap_location_id:
            res['location_dest_id'] = self.scrap_location_id.id
            
        return res

    def action_validate(self):
                                              
        for scrap in self:
            if not scrap.location_id:
                raise models.ValidationError(
                    f"Source location is required for scrap {scrap.name}"
                )
            if not scrap.scrap_location_id:
                raise models.ValidationError(
                    f"Scrap location is required for scrap {scrap.name}"
                )
        
        self = self.with_context(validate_analytic=True)
        return super().action_validate()
