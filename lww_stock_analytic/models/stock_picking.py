# ===== STOCK PICKING FIX =====
from odoo import api, fields, models


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "analytic.mixin"]

    original_analytic_distribution = fields.Json()
    analytic_distribution = fields.Json(inverse="_inverse_analytic_distribution")

    @api.depends(
        "move_ids_without_package.analytic_distribution",
        "original_analytic_distribution",
    )
    def _compute_analytic_distribution(self):
        """
        Get analytic account from first move and put it on picking
        """
        if not self.filtered("id"):
            return
        self.flush_model(["move_ids", "original_analytic_distribution"])
        self.env["stock.move"].flush_model(["analytic_distribution"])
        self.env.cr.execute(
            """
            SELECT
                picking.id,
                CASE
                    WHEN
                        COUNT(move.id) = 0
                        THEN picking.original_analytic_distribution
                    WHEN
                        COUNT(DISTINCT move.analytic_distribution) = 1
                        THEN (
                            ARRAY_AGG(move.analytic_distribution)
                            FILTER (WHERE move.analytic_distribution IS NOT NULL)
                        )[1]
                END AS analytic_distribution
            FROM
                stock_picking AS picking
            LEFT JOIN
                stock_move AS move
                ON picking.id = move.picking_id
            WHERE
                picking.id IN %s
            GROUP BY
                picking.id;
            """,
            [tuple(self.ids)],
        )
        result = dict(self.env.cr.fetchall())
        for picking in self:
            picking.analytic_distribution = result.get(picking.id)

    def _inverse_analytic_distribution(self):
        """
        If analytic distribution is set on picking, write it on all moves
        FIXED: Prevent circular calls and validate move integrity
        """
        for picking in self:
            # Prevent infinite recursion
            if self.env.context.get('skip_picking_inverse'):
                continue
                
            if picking.analytic_distribution:
                # Get valid moves only (with required fields)
                valid_moves = picking.move_ids_without_package.filtered(
                    lambda m: m.id and m.product_id and 
                    getattr(m, 'location_id', False) and 
                    getattr(m, 'location_dest_id', False)
                )
                
                if valid_moves:
                    # Use context to prevent circular inverse calls
                    ctx = dict(self.env.context, 
                              skip_picking_inverse=True,
                              skip_move_line_inverse=True)
                    
                    # Update moves one by one to handle any individual failures
                    for move in valid_moves:
                        try:
                            move.with_context(ctx).write({
                                "analytic_distribution": picking.analytic_distribution
                            })
                        except Exception as e:
                            # Log the error but continue with other moves
                            _logger.warning(f"Failed to update analytic distribution for move {move.id}: {e}")
                            continue
                            
            # Always update original_analytic_distribution
            picking.original_analytic_distribution = picking.analytic_distribution