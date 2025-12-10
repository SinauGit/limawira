from odoo import models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _get_custom_move_fields(self):
                                                       
        return super()._get_custom_move_fields() + [
            "analytic_distribution", 
            "location_id", 
            "location_dest_id"
        ]

    def _prepare_move_vals(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values):
                                                                      
        res = super()._prepare_move_vals(
            product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values
        )
        
                                                                       
        if not res.get('location_id'):
            if self.location_src_id:
                res['location_id'] = self.location_src_id.id
            elif values.get('location_id'):
                res['location_id'] = values['location_id']
        
                                                 
        if values.get('analytic_distribution'):
            res['analytic_distribution'] = values['analytic_distribution']
            
        return res