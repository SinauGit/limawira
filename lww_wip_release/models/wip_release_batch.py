from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WipReleaseBatch(models.Model):
    _name = 'wip.release.batch'
    _description = 'WIP Release Batch'
    _order = 'release_date desc, id desc'

    name = fields.Char(
        string='Batch Number',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _('New'),
        index=True,
    )
    x_global_project_number = fields.Char(
        string='Global Project Number',
        required=True,
        readonly=True,
        index=True,
    )
    master_project_id = fields.Many2one(
        'project.project',
        string='Master Project',
        required=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        related='master_project_id.partner_id',
        string='Customer',
        store=True,
    )
    sale_order_id = fields.Many2one(
        related='master_project_id.x_sale_order_id',
        string='Sales Order',
        store=True,
    )
    release_date = fields.Date(string='Release Date', readonly=True)
    accounting_date = fields.Date(string='Accounting Date', required=True, readonly=True)
    release_type = fields.Selection(
        [('initial', 'Initial Release'), ('additional', 'Additional Release')],
        string='Release Type',
        required=True,
        readonly=True,
        default='initial',
    )
    is_manual_override = fields.Boolean(string='Manual Override', readonly=True)
    override_reason = fields.Text(string='Release Reason', readonly=True)
    remarks = fields.Text(string='Remarks', readonly=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('done', 'Released')],
        string='Status',
        default='draft',
        required=True,
        readonly=True,
    )
    approved_by_id = fields.Many2one(
        'res.users',
        related='create_uid',
        string='Approved By',
        store=True,
    )
    line_ids = fields.One2many('wip.release.line', 'batch_id', string='Release Lines')
    line_count = fields.Integer(string='Companies', compute='_compute_totals')
    total_wip_amount = fields.Monetary(
        string='Total WIP Amount',
        currency_field='currency_id',
        compute='_compute_totals',
    )
    total_released_amount = fields.Monetary(
        string='Total Released',
        currency_field='currency_id',
        compute='_compute_totals',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Batch Number must be unique.'),
    ]

    @api.depends('line_ids', 'line_ids.wip_amount', 'line_ids.released_amount')
    def _compute_totals(self):
        for batch in self:
            batch.line_count = len(batch.line_ids)
            batch.total_wip_amount = sum(batch.line_ids.mapped('wip_amount'))
            batch.total_released_amount = sum(batch.line_ids.mapped('released_amount'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code(
                    'wip.release.batch'
                ) or _('New')
        return super().create(vals_list)

    def unlink(self):
        for batch in self:
            if batch.state == 'done':
                raise UserError(_(
                    'Batch %s has been released and cannot be deleted.'
                ) % batch.name)
        return super().unlink()

    def action_execute(self):
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_('Batch %s has already been released.') % self.name)

        projects = self.master_project_id._get_group_projects()
        line_model = self.env['wip.release.line'].sudo()
        created_lines = self.env['wip.release.line'].sudo()

        for project in projects:
            move_lines = project._get_unreleased_wip_lines()
            amount = sum(move_lines.mapped('balance'))
            currency = project.company_id.currency_id or self.env.company.currency_id
            if currency.compare_amounts(amount, 0.0) <= 0:
                continue

            release_line = line_model.create({
                'batch_id': self.id,
                'company_id': project.company_id.id,
                'project_id': project.id,
                'analytic_account_id': project.account_id.id,
                'wip_amount': amount,
                'released_amount': amount,
            })
            move = release_line._create_release_move(project, move_lines, amount)
            release_line.move_id = move.id
            release_line._stamp_and_reconcile(move, move_lines)
            created_lines |= release_line

        if not created_lines:
            raise UserError(_(
                'No unreleased WIP balance found for global project %s.'
            ) % self.x_global_project_number)

        self.write({
            'state': 'done',
            'release_date': fields.Date.context_today(self),
        })
        projects._refresh_wip_fields()
        return True

    def action_view_moves(self):
        self.ensure_one()
        moves = self.line_ids.mapped('move_id')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Release Journal Entries'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', moves.ids)],
        }
