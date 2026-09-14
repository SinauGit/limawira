from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


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

    @api.constrains('analytic_distribution', 'account_id', 'display_type')
    def _check_x_analytic_required(self):
        for line in self:
            if (
                line.account_id
                and line.account_id.x_analytic_required
                and line.move_id.move_type in ('in_invoice', 'in_refund', 'entry')
                and line.display_type not in ('line_section', 'line_note')
                and not line.analytic_distribution
            ):
                raise ValidationError(_(
                    'The Analytic Distribution field is Required for rows with the account "%(account)s" '
                    'in the Draft Bill document. %(move)s.',
                    account=line.account_id.display_name,
                    move=line.move_id.display_name or _('baru'),
                ))
