from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WipReleaseLine(models.Model):
    _name = 'wip.release.line'
    _description = 'WIP Release Line'
    _order = 'batch_id desc, id asc'

    batch_id = fields.Many2one(
        'wip.release.batch',
        string='Batch',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        index=True,
    )
    project_id = fields.Many2one('project.project', string='Project', required=True)
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
    )
    currency_id = fields.Many2one(related='company_id.currency_id')
    wip_amount = fields.Monetary(string='WIP Amount', currency_field='currency_id')
    released_amount = fields.Monetary(string='Released Amount', currency_field='currency_id')
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)
    move_state = fields.Selection(related='move_id.state', string='Entry Status')
    x_global_project_number = fields.Char(
        related='batch_id.x_global_project_number',
        store=True,
        index=True,
    )
    accounting_date = fields.Date(related='batch_id.accounting_date', store=True)
    source_line_ids = fields.One2many(
        'account.move.line',
        'x_wip_release_line_id',
        string='Released Journal Items',
    )

    def _create_release_move(self, project, move_lines, amount):
        self.ensure_one()
        label = _('WIP Release - %s') % project.name
        distribution = {}
        if project.account_id:
            distribution = {str(project.account_id.id): 100.0}

        move_vals = {
            'move_type': 'entry',
            'company_id': project.company_id.id,
            'journal_id': project.x_wip_journal_id.id,
            'date': self.batch_id.accounting_date,
            'ref': _('%(batch)s - %(project)s') % {
                'batch': self.batch_id.name,
                'project': project.name,
            },
            'line_ids': [
                (0, 0, {
                    'name': label,
                    'account_id': project.x_cogs_account_id.id,
                    'debit': amount,
                    'credit': 0.0,
                    'currency_id': project.company_id.currency_id.id,
                    'amount_currency': amount,
                    'analytic_distribution': distribution,
                }),
                (0, 0, {
                    'name': label,
                    'account_id': project.x_wip_account_id.id,
                    'debit': 0.0,
                    'credit': amount,
                    'currency_id': project.company_id.currency_id.id,
                    'amount_currency': -amount,
                    'analytic_distribution': distribution,
                }),
            ],
        }
        move = self.env['account.move'].sudo().with_company(project.company_id).create(move_vals)
        move.action_post()
        return move

    def _stamp_and_reconcile(self, move, move_lines):
        self.ensure_one()
        wip_account = self.project_id.x_wip_account_id
        credit_line = move.line_ids.filtered(lambda l: l.account_id == wip_account)
        if wip_account.reconcile:
            to_reconcile = (move_lines | credit_line).sudo().filtered(
                lambda l: not l.reconciled
            )
            if to_reconcile:
                company = self.company_id
                to_reconcile.with_company(company).with_context(
                    allowed_company_ids=[company.id],
                    no_exchange_difference=True,
                ).reconcile()

    def action_view_move(self):
        self.ensure_one()
        if not self.move_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Release Journal Entry'),
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
        }
