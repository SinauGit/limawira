from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    lww_rec_journal_id = fields.Many2one(
        related='company_id.lww_rec_journal_id', readonly=False)
    lww_rec_payable_account_id = fields.Many2one(
        related='company_id.lww_rec_payable_account_id', readonly=False)
    lww_billing_threshold = fields.Float(
        related='company_id.lww_billing_threshold', readonly=False)
