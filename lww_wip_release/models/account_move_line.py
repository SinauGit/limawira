from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    x_wip_release_line_id = fields.Many2one(
        'wip.release.line',
        string='WIP Release',
        readonly=True,
        copy=False,
        index=True,
        check_company=False,
    )
    x_wip_release_batch_id = fields.Many2one(
        related='x_wip_release_line_id.batch_id',
        string='WIP Release Batch',
        store=True,
    )

    @api.model
    def _get_configured_wip_account_ids(self):
        projects = self.env['project.project'].sudo().search(
            [('x_wip_account_id', '!=', False)]
        )
        return set(projects.mapped('x_wip_account_id').ids)

    @api.constrains('account_id', 'analytic_distribution')
    def _check_wip_analytic_distribution(self):
        suspicious = self.filtered(lambda l: l.analytic_distribution and (
            len(l.analytic_distribution) != 1
            or list(l.analytic_distribution.values())[0] != 100.0
        ))
        if not suspicious:
            return
        wip_account_ids = self._get_configured_wip_account_ids()
        if not wip_account_ids:
            return
        for line in suspicious:
            if line.account_id.id not in wip_account_ids:
                continue
            raise ValidationError(_(
                'Journal item "%(label)s" posts to WIP account %(account)s and must be '
                'distributed 100%% to a single analytic account.'
            ) % {
                'label': line.name or line.move_id.name or '',
                'account': line.account_id.display_name,
            })
