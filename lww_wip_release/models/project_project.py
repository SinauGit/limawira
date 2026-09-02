from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

WIP_COMPUTED_FIELDS = [
    'x_contract_value',
    'x_invoice_progress',
    'x_unreleased_wip',
    'x_released_wip',
    'x_group_unreleased_wip',
    'x_wip_release_state',
]


class ProjectProject(models.Model):
    _inherit = 'project.project'

    x_is_master_project = fields.Boolean(
        string='Master Project',
        default=False,
        copy=False,
        help='Project of the parent company that owns the sales order.',
    )
    x_parent_global_project_id = fields.Many2one(
        'project.project',
        string='Parent Global Project',
        domain="[('x_is_master_project', '=', True)]",
        copy=False,
        index=True,
    )
    x_master_project_id = fields.Many2one(
        'project.project',
        string='Master Project Reference',
        compute='_compute_x_master_project_id',
        store=True,
        compute_sudo=True,
        index=True,
    )
    x_child_project_ids = fields.One2many(
        'project.project',
        'x_parent_global_project_id',
        string='Child Projects',
    )
    x_global_project_number = fields.Char(
        string='Global Project Number',
        compute='_compute_x_global_project_number',
        store=True,
        compute_sudo=True,
        index=True,
    )
    x_company_role = fields.Selection(
        [('parent', 'Parent Company'), ('child', 'Child Company')],
        string='Company Role',
        compute='_compute_x_company_role',
        store=True,
        compute_sudo=True,
    )
    x_project_group_name = fields.Char(
        string='Project Group Name',
        compute='_compute_x_project_group_name',
        store=True,
        readonly=False,
        compute_sudo=True,
    )
    x_sale_order_id = fields.Many2one(
        'sale.order',
        string='Contract Sales Order',
        copy=False,
        domain="[('state', '=', 'sale'), ('company_id', '=', company_id)]",
    )
    x_release_threshold = fields.Float(
        string='WIP Release Threshold (%)',
        default=90.0,
    )
    x_wip_account_id = fields.Many2one(
        'account.account',
        string='WIP Account',
        domain="[('company_ids', 'in', company_id), ('deprecated', '=', False)]",
    )
    x_cogs_account_id = fields.Many2one(
        'account.account',
        string='COGS Account',
        domain="[('company_ids', 'in', company_id), ('deprecated', '=', False)]",
    )
    x_wip_journal_id = fields.Many2one(
        'account.journal',
        string='WIP Release Journal',
        domain="[('company_id', '=', company_id)]",
    )
    x_contract_value = fields.Monetary(
        string='Contract Value',
        currency_field='currency_id',
        compute='_compute_x_contract_value',
        store=True,
        compute_sudo=True,
    )
    x_invoice_progress = fields.Float(
        string='Invoice Progress (%)',
        digits=(16, 2),
        compute='_compute_x_invoice_progress',
        store=True,
        compute_sudo=True,
    )
    x_invoiced_amount = fields.Monetary(
        string='Invoiced Amount',
        currency_field='currency_id',
        compute='_compute_x_invoice_progress',
        store=True,
        compute_sudo=True,
    )
    x_unreleased_wip = fields.Monetary(
        string='Unreleased WIP',
        currency_field='currency_id',
        compute='_compute_x_wip_amounts',
        store=True,
        compute_sudo=True,
    )
    x_released_wip = fields.Monetary(
        string='Released WIP',
        currency_field='currency_id',
        compute='_compute_x_wip_amounts',
        store=True,
        compute_sudo=True,
    )
    x_group_unreleased_wip = fields.Monetary(
        string='Group Unreleased WIP',
        currency_field='currency_id',
        compute='_compute_x_group_unreleased_wip',
        store=True,
        compute_sudo=True,
    )
    x_wip_release_state = fields.Selection(
        [
            ('not_released', 'Not Released'),
            ('eligible', 'Eligible'),
            ('released', 'Released'),
            ('released_additional', 'Released + Additional'),
        ],
        string='WIP Release Status',
        default='not_released',
        compute='_compute_x_wip_release_state',
        store=True,
        compute_sudo=True,
    )
    x_release_line_ids = fields.One2many(
        'wip.release.line',
        'project_id',
        string='WIP Release History',
    )
    x_last_release_date = fields.Date(
        string='Last Release',
        compute='_compute_x_last_release_date',
        store=True,
        compute_sudo=True,
    )

    @api.depends('x_is_master_project', 'x_parent_global_project_id')
    def _compute_x_master_project_id(self):
        for project in self:
            if project.x_is_master_project:
                project.x_master_project_id = project
            else:
                project.x_master_project_id = project.x_parent_global_project_id

    @api.depends(
        'x_is_master_project',
        'name',
        'x_parent_global_project_id.x_global_project_number',
    )
    def _compute_x_global_project_number(self):
        for project in self:
            if project.x_is_master_project:
                project.x_global_project_number = project.name
            elif project.x_parent_global_project_id:
                project.x_global_project_number = (
                    project.x_parent_global_project_id.x_global_project_number
                )
            else:
                project.x_global_project_number = False

    @api.depends('x_is_master_project', 'x_parent_global_project_id')
    def _compute_x_company_role(self):
        for project in self:
            if project.x_is_master_project:
                project.x_company_role = 'parent'
            elif project.x_parent_global_project_id:
                project.x_company_role = 'child'
            else:
                project.x_company_role = False

    @api.depends(
        'x_is_master_project',
        'x_parent_global_project_id.x_project_group_name',
    )
    def _compute_x_project_group_name(self):
        for project in self:
            if not project.x_is_master_project and project.x_parent_global_project_id:
                project.x_project_group_name = (
                    project.x_parent_global_project_id.x_project_group_name
                )
            else:
                project.x_project_group_name = project.x_project_group_name

    @api.depends(
        'x_master_project_id',
        'x_master_project_id.x_sale_order_id',
        'x_master_project_id.x_sale_order_id.amount_total',
    )
    def _compute_x_contract_value(self):
        for project in self:
            order = project.x_master_project_id.x_sale_order_id
            project.x_contract_value = order.amount_total if order else 0.0

    @api.depends(
        'x_master_project_id',
        'x_master_project_id.account_id',
        'x_master_project_id.x_sale_order_id',
        'x_master_project_id.x_sale_order_id.amount_total',
        'x_master_project_id.x_sale_order_id.invoice_ids',
        'x_master_project_id.x_sale_order_id.invoice_ids.state',
        'x_master_project_id.x_sale_order_id.invoice_ids.amount_total',
    )
    def _compute_x_invoice_progress(self):
        for project in self:
            master = project.x_master_project_id
            order = master.x_sale_order_id
            contract = order.amount_total if order else 0.0
            invoiced = master._get_invoiced_amount() if order else 0.0
            project.x_invoiced_amount = invoiced
            if not contract:
                project.x_invoice_progress = 0.0
            else:
                project.x_invoice_progress = (invoiced / contract) * 100.0

    def _get_invoiced_amount(self):
        self.ensure_one()
        order = self.x_sale_order_id
        if not order or not self.account_id:
            return 0.0
        key = str(self.account_id.id)
        total = 0.0
        for invoice in order.invoice_ids:
            if invoice.state != 'posted' or invoice.move_type != 'out_invoice':
                continue
            touches = any(
                key in (line.analytic_distribution or {})
                for line in invoice.invoice_line_ids
            )
            if touches:
                total += invoice.amount_total
        return total

    def _get_unreleased_wip_lines(self):
        self.ensure_one()
        if not self.x_wip_account_id or not self.account_id:
            return self.env['account.move.line']
        lines = self.env['account.move.line'].sudo().search([
            ('account_id', '=', self.x_wip_account_id.id),
            ('parent_state', '=', 'posted'),
            ('x_wip_release_line_id', '=', False),
        ])
        key = str(self.account_id.id)
        return lines.filtered(lambda l: key in (l.analytic_distribution or {}))

    @api.depends(
        'x_wip_account_id',
        'account_id',
        'x_release_line_ids',
        'x_release_line_ids.released_amount',
    )
    def _compute_x_wip_amounts(self):
        account_ids = self.mapped('x_wip_account_id').ids
        balances = {}
        if account_ids:
            lines = self.env['account.move.line'].sudo().search([
                ('account_id', 'in', account_ids),
                ('parent_state', '=', 'posted'),
                ('x_wip_release_line_id', '=', False),
            ])
            for line in lines:
                for key in (line.analytic_distribution or {}):
                    bucket = (line.account_id.id, key)
                    balances[bucket] = balances.get(bucket, 0.0) + line.balance

        for project in self:
            if project.x_wip_account_id and project.account_id:
                bucket = (
                    project.x_wip_account_id.id,
                    str(project.account_id.id),
                )
                project.x_unreleased_wip = balances.get(bucket, 0.0)
            else:
                project.x_unreleased_wip = 0.0
            project.x_released_wip = sum(
                project.x_release_line_ids.sudo().mapped('released_amount')
            )

    @api.depends('x_unreleased_wip', 'x_child_project_ids.x_unreleased_wip')
    def _compute_x_group_unreleased_wip(self):
        for project in self:
            total = project.x_unreleased_wip
            if project.x_is_master_project:
                total += sum(project.x_child_project_ids.mapped('x_unreleased_wip'))
            project.x_group_unreleased_wip = total

    @api.depends(
        'x_invoice_progress',
        'x_release_threshold',
        'x_unreleased_wip',
        'x_group_unreleased_wip',
        'x_release_line_ids',
        'x_release_line_ids.batch_id.state',
    )
    def _compute_x_wip_release_state(self):
        for project in self:
            batches = project.x_release_line_ids.sudo().mapped('batch_id').filtered(
                lambda b: b.state == 'done'
            )
            if len(batches) > 1:
                project.x_wip_release_state = 'released_additional'
            elif batches:
                project.x_wip_release_state = 'released'
            else:
                pending = (
                    project.x_group_unreleased_wip
                    if project.x_is_master_project
                    else project.x_unreleased_wip
                )
                if (
                    project.x_global_project_number
                    and project.x_invoice_progress >= project.x_release_threshold
                    and pending > 0
                ):
                    project.x_wip_release_state = 'eligible'
                else:
                    project.x_wip_release_state = 'not_released'

    @api.depends('x_release_line_ids.batch_id.release_date')
    def _compute_x_last_release_date(self):
        for project in self:
            dates = project.x_release_line_ids.sudo().mapped('batch_id.release_date')
            project.x_last_release_date = max([d for d in dates if d], default=False)

    @api.constrains('x_is_master_project', 'x_parent_global_project_id')
    def _check_global_project_mapping(self):
        for project in self:
            if project.x_is_master_project and project.x_parent_global_project_id:
                raise ValidationError(_(
                    'Project %s is a master project and cannot reference a parent '
                    'global project.'
                ) % project.name)
            if project.x_parent_global_project_id == project:
                raise ValidationError(_(
                    'Project %s cannot be its own parent global project.'
                ) % project.name)
            if (
                project.x_parent_global_project_id
                and not project.x_parent_global_project_id.x_is_master_project
            ):
                raise ValidationError(_(
                    'Parent global project of %s must be a master project.'
                ) % project.name)

    @api.constrains('x_is_master_project', 'x_sale_order_id')
    def _check_master_sale_order(self):
        for project in self:
            if project.x_sale_order_id and not project.x_is_master_project:
                raise ValidationError(_(
                    'Only a master project can hold the contract sales order. '
                    'Project %s is a child project.'
                ) % project.name)

    def _get_group_projects(self):
        self.ensure_one()
        if not self.x_global_project_number:
            return self
        return self.env['project.project'].sudo().search([
            ('x_global_project_number', '=', self.x_global_project_number),
        ])

    def _check_wip_configuration(self):
        missing = []
        for project in self:
            gaps = []
            if not project.account_id:
                gaps.append(_('Analytic Account'))
            if not project.company_id:
                gaps.append(_('Company'))
            if not project.x_wip_account_id:
                gaps.append(_('WIP Account'))
            if not project.x_cogs_account_id:
                gaps.append(_('COGS Account'))
            if not project.x_wip_journal_id:
                gaps.append(_('WIP Release Journal'))
            if gaps:
                missing.append('%s (%s): %s' % (
                    project.name,
                    project.company_id.name or _('No Company'),
                    ', '.join(gaps),
                ))
        if missing:
            raise UserError(_(
                'WIP release configuration is incomplete:\n\n%s'
            ) % '\n'.join(missing))
        return True

    def _refresh_wip_fields(self):
        if not self:
            return
        for field_name in WIP_COMPUTED_FIELDS:
            self.env.add_to_compute(self._fields[field_name], self)
        self.flush_recordset()
        return True

    @api.model
    def _cron_update_wip_release_status(self):
        projects = self.sudo().with_context(active_test=False).search([
            ('x_global_project_number', '!=', False),
        ])
        children = projects.filtered(lambda p: not p.x_is_master_project)
        masters = projects.filtered(lambda p: p.x_is_master_project)
        children._refresh_wip_fields()
        masters._refresh_wip_fields()
        return True

    def action_open_wip_release_wizard(self):
        masters = self.filtered(lambda p: p.x_is_master_project)
        if not masters:
            raise UserError(_(
                'WIP release must be executed from a master project.'
            ))
        return {
            'type': 'ir.actions.act_window',
            'name': _('WIP Release'),
            'res_model': 'wip.release.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_master_project_ids': masters.ids,
            },
        }

    def action_view_group_projects(self):
        self.ensure_one()
        projects = self._get_group_projects()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Global Project %s') % (self.x_global_project_number or ''),
            'res_model': 'project.project',
            'view_mode': 'list,form',
            'domain': [('id', 'in', projects.ids)],
            'context': {'search_default_group_company': 1},
        }
