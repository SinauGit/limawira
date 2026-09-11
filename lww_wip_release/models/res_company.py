from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    x_default_wip_account_id = fields.Many2one(
        'account.account',
        string='Default WIP Account',
        domain="[('company_ids', 'in', id), ('deprecated', '=', False)]",
    )
    x_default_cogs_account_id = fields.Many2one(
        'account.account',
        string='Default COGS Account',
        domain="[('company_ids', 'in', id), ('deprecated', '=', False)]",
    )
    x_default_wip_journal_id = fields.Many2one(
        'account.journal',
        string='Default WIP Release Journal',
        domain="[('company_id', '=', id)]",
    )
    x_default_release_threshold = fields.Float(
        string='Default WIP Release Threshold (%)',
        default=90.0,
    )
