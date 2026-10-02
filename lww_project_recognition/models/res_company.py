from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    lww_rec_journal_id = fields.Many2one(
        'account.journal', string='Recognition Journal',
        domain="[('type', '=', 'general'), ('company_id', '=', id)]")
    lww_rec_payable_account_id = fields.Many2one(
        'account.account', string='Project Cost Payable Account',
        domain="[('deprecated', '=', False)]")
    lww_billing_threshold = fields.Float(
        string='Billing Progress Threshold (%)', default=90.0)
