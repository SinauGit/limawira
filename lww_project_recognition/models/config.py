from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LwwRecognitionConfig(models.Model):
    _name = 'lww.recognition.config'
    _description = 'Project Recognition Configuration'

    company_id = fields.Many2one('res.company', required=True, default=lambda s: s.env.company, index=True)
    name = fields.Char(compute='_compute_name')
    journal_id = fields.Many2one('account.journal', string='Recognition Journal', required=True,
                                 domain="[('company_id', '=', company_id)]")
    payable_account_id = fields.Many2one('account.account', string='Hutang Biaya Proyek Account', required=True,
                                         domain="[('company_ids', 'in', company_id)]")
    threshold = fields.Float(string='Billing Threshold (%)', default=90.0, required=True)
    go_live_date = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)

    _sql_constraints = [('company_uniq', 'unique(company_id)', 'Only one configuration per company.')]

    @api.depends('company_id')
    def _compute_name(self):
        for rec in self:
            rec.name = rec.company_id.name

    @api.constrains('threshold')
    def _check_threshold(self):
        for rec in self:
            if not 0 < rec.threshold <= 100:
                raise ValidationError(_('Threshold must be between 0 and 100.'))

    @api.model
    def _get(self, company):
        return self.sudo().search([('company_id', '=', company.id)], limit=1)
