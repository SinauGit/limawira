from odoo import api, fields, models


class WipReleaseConfig(models.Model):
    _name = 'wip.release.config'
    _description = 'WIP Release Company Defaults'
    _rec_name = 'company_id'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        index=True,
    )
    wip_account_id = fields.Many2one(
        'account.account',
        string='Default WIP Account',
        domain="[('company_ids', 'in', company_id), ('deprecated', '=', False)]",
    )
    cogs_account_id = fields.Many2one(
        'account.account',
        string='Default COGS Account',
        domain="[('company_ids', 'in', company_id), ('deprecated', '=', False)]",
    )
    wip_journal_id = fields.Many2one(
        'account.journal',
        string='Default WIP Release Journal',
        domain="[('company_id', '=', company_id)]",
    )
    release_threshold = fields.Float(
        string='Default WIP Release Threshold (%)',
        default=90.0,
    )

    _sql_constraints = [
        ('company_uniq', 'unique(company_id)',
         'There is already a WIP Release default configuration for this company.'),
    ]

    @api.model
    def _get_for_company(self, company):
        if not company:
            return self.browse()
        return self.sudo().search([('company_id', '=', company.id)], limit=1)
