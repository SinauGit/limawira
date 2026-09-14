from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    x_analytic_needed = fields.Boolean(
        string='Analytic Distribution Required',
        compute='_compute_x_analytic_needed',
    )

    @api.depends(
        'account_id',
        'account_id.x_analytic_required',
        'move_id.move_type',
        'display_type',
    )
    def _compute_x_analytic_needed(self):
        for line in self:
            line.x_analytic_needed = bool(
                line.account_id
                and line.account_id.x_analytic_required
                and line.move_id.move_type in ('in_invoice', 'in_refund', 'entry')
                and line.display_type not in ('line_section', 'line_note')
            )
