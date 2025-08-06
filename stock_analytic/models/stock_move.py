# Copyright 2013 Julius Network Solutions
# Copyright 2015 Clear Corp
# Copyright 2016 OpenSynergy Indonesia
# Copyright 2017 ForgeFlow S.L.
# Copyright 2018 Hibou Corp.
# Copyright 2023 Quartile Limited
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "analytic.mixin"]

    analytic_distribution = fields.Json(inverse="_inverse_analytic_distribution")

    def _inverse_analytic_distribution(self):
        """
        If analytic distribution is set on move, write it on all move lines
        FIXED: Prevent circular calls and validate move line integrity
        """
        for move in self:
            # Prevent infinite recursion from picking inverse
            if self.env.context.get('skip_move_line_inverse'):
                continue
                
            if move.analytic_distribution and move.move_line_ids:
                # Filter valid move lines
                valid_lines = move.move_line_ids.filtered(lambda ml: ml.id)
                
                if valid_lines:
                    # Use context to prevent circular calls
                    ctx = dict(self.env.context, skip_move_inverse=True)
                    
                    try:
                        valid_lines.with_context(ctx).write({
                            "analytic_distribution": move.analytic_distribution
                        })
                    except Exception as e:
                        _logger.warning(f"Failed to update analytic distribution for move lines of move {move.id}: {e}")

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
                # Add analytic account in debit line
                line[2].update({"analytic_distribution": self.analytic_distribution})
        return res

    def _prepare_procurement_values(self):
        """
        Allows to transmit analytic account from moves to new
        moves through procurement.
        """
        res = super()._prepare_procurement_values()
        if self.analytic_distribution:
            res.update({"analytic_distribution": self.analytic_distribution})
        return res

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        """
        We fill in the analytic account when creating the move line from
        the move
        """
        res = super()._prepare_move_line_vals(
            quantity=quantity, reserved_quant=reserved_quant
        )
        if self.analytic_distribution:
            res.update({"analytic_distribution": self.analytic_distribution})
        return res

    def _need_validate_distribution(self):
        """Return moves are made outside the scope of the validation for now, since
        there could be cases where the necessity cannot be judged solely by the
        operation type.
        """
        self.ensure_one()
        if self._is_in() and self._is_returned(valued_type="in"):
            return False
        elif self._is_out() and self._is_returned(valued_type="out"):
            return False
        elif self.company_id.anglo_saxon_accounting and self._is_dropshipped_returned():
            return False
        return True

    def _action_done(self, cancel_backorder=False):
        for move in self:
            # Safely update move line analytic distribution
            if move.move_line_ids and move.analytic_distribution:
                try:
                    move.move_line_ids.with_context(skip_move_inverse=True).write({
                        'analytic_distribution': move.analytic_distribution
                    })
                except Exception as e:
                    _logger.warning(f"Failed to sync analytic distribution in _action_done for move {move.id}: {e}")
                    
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


# ===== STOCK MOVE LINE FIX =====
class StockMoveLine(models.Model):
    _name = "stock.move.line"
    _inherit = ["stock.move.line", "analytic.mixin"]

    @api.model
    def _prepare_stock_move_vals(self):
        """
        In the case move lines are created manually, we should fill in the
        new move created here with the analytic account if filled in.
        """
        res = super()._prepare_stock_move_vals()
        if self.analytic_distribution:
            res.update({"analytic_distribution": self.analytic_distribution})
        return res

    def write(self, vals):
        """
        FIXED: Prevent circular inverse calls when updating analytic distribution
        """
        result = super().write(vals)
        
        # Only update move if not in circular prevention context
        if ("analytic_distribution" in vals and 
            not self.env.context.get('skip_move_inverse')):
            
            # Update related moves with context to prevent circular calls
            moves_to_update = self.mapped('move_id').filtered(lambda m: m.id)
            if moves_to_update:
                ctx = dict(self.env.context, skip_move_line_inverse=True)
                try:
                    for move in moves_to_update:
                        move.with_context(ctx).analytic_distribution = vals["analytic_distribution"]
                except Exception as e:
                    _logger.warning(f"Failed to update move analytic distribution from move line: {e}")
                    
        return result