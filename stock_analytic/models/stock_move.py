                                         
                           
                                      
                               
                            
                                 
                                                                    

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "analytic.mixin"]

    analytic_distribution = fields.Json(
        inverse="_inverse_analytic_distribution",
    )

                
    def _inverse_analytic_distribution(self):
        for move in self:
            move.move_line_ids.with_context(_skip_move_sync=True).write(
                {"analytic_distribution": move.analytic_distribution}
            )

    def _prepare_account_move_line(
        self, qty, cost, credit_account_id, debit_account_id, svl_id, description
    ):
        self.ensure_one()
        res = super()._prepare_account_move_line(
            qty, cost, credit_account_id, debit_account_id, svl_id, description
        )
        if not self.analytic_distribution:
            return res
        for line in res:
            if (
                line[2]["account_id"]
                != self.product_id.categ_id.property_stock_valuation_account_id.id
            ):
                                                    
                line[2].update({"analytic_distribution": self.analytic_distribution})
        return res

    def _prepare_procurement_values(self):



           
        res = super()._prepare_procurement_values()
        if self.analytic_distribution:
            res.update(
                {
                    "analytic_distribution": self.analytic_distribution,
                }
            )
        return res

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):



           
        res = super()._prepare_move_line_vals(
            quantity=quantity, reserved_quant=reserved_quant
        )
        if self.analytic_distribution:
            res.update({"analytic_distribution": self.analytic_distribution})
        return res

    def _need_validate_distribution(self):



           
        self.ensure_one()
        if self._is_in() and self._is_returned(valued_type="in"):
            return False
        elif self._is_out() and self._is_returned(valued_type="out"):
            return False
        elif self.company_id.anglo_saxon_accounting and self._is_dropshipped_returned():
            return False
        return True

                                                                            
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
                                                               
            if not vals.get('location_id') and vals.get('picking_id'):
                picking = self.env['stock.picking'].browse(vals['picking_id'])
                if picking and picking.location_id:
                    vals['location_id'] = picking.location_id.id
            
            if not vals.get('location_dest_id') and vals.get('picking_id'):
                picking = self.env['stock.picking'].browse(vals['picking_id'])
                if picking and picking.location_dest_id:
                    vals['location_dest_id'] = picking.location_dest_id.id
                    
        return super().create(vals_list)

    def _action_done(self, cancel_backorder=False):
        for move in self:
                                                              
            if not move.location_id:
                raise ValidationError(
                    f"Source location is mandatory for move {move.name}. "
                    f"Please set the location_id before validating."
                )
            if not move.location_dest_id:
                raise ValidationError(
                    f"Destination location is mandatory for move {move.name}. "
                    f"Please set the location_dest_id before validating."
                )
                
            move.move_line_ids.analytic_distribution = move.analytic_distribution
            if not move._need_validate_distribution():
                continue
            move._validate_distribution(
                **{
                    "product": move.product_id.id,
                    "picking_type": move.picking_type_id.id,
                    "business_domain": "stock_move",
                    "company_id": move.company_id.id,
                }
            )
        return super()._action_done(cancel_backorder=cancel_backorder)


class StockMoveLine(models.Model):
    _name = "stock.move.line"
    _inherit = ["stock.move.line", "analytic.mixin"]

    @api.model
    def _prepare_stock_move_vals(self):



           
        res = super()._prepare_stock_move_vals()
        if self.analytic_distribution:
            res.update({"analytic_distribution": self.analytic_distribution})
        
                                                                                     
        if not res.get('location_id') and self.location_id:
            res['location_id'] = self.location_id.id
        if not res.get('location_dest_id') and self.location_dest_id:
            res['location_dest_id'] = self.location_dest_id.id
            
        return res

                     
    def write(self, vals):
        if "analytic_distribution" in vals and not self.env.context.get("_skip_move_sync"):
            new_dist = vals["analytic_distribution"]
            for ml in self:
                if ml.move_id and ml.move_id.analytic_distribution != new_dist:
                    ml.move_id.write({"analytic_distribution": new_dist})
        return super().write(vals)