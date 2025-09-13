from odoo import models, fields

class ProjectAnalyticTransferLog(models.Model):
    _name = 'project.analytic.transfer.log'
    _description = 'Project Analytic Transfer Log'
    _order = 'create_date desc'

    source_project_id = fields.Many2one('project.project', string='Source Project')
    source_analytic_account_id = fields.Many2one('account.analytic.account', string='Source Analytic')
    target_project_id = fields.Many2one('project.project', string='Target Project')
    target_analytic_account_id = fields.Many2one('account.analytic.account', string='Target Analytic')
    user_id = fields.Many2one('res.users', string='User')
    create_date = fields.Datetime(string='Date', readonly=True)
    state = fields.Selection([
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('error', 'Error')
    ], string='State', default='in_progress')
    records_updated = fields.Integer(string='Records Updated')
    details = fields.Text(string='Details')