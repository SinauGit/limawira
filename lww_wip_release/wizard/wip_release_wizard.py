from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WipReleaseWizard(models.TransientModel):
    _name = 'wip.release.wizard'
    _description = 'WIP Release Wizard'

    master_project_ids = fields.Many2many(
        'project.project',
        string='Global Projects',
        required=True,
        domain="[('x_is_master_project', '=', True)]",
    )
    accounting_date = fields.Date(
        string='Accounting Date',
        required=True,
        default=fields.Date.context_today,
    )
    remarks = fields.Text(string='Remarks')
    is_manual_override = fields.Boolean(string='Manual Override')
    override_reason = fields.Text(string='Release Reason')
    line_ids = fields.One2many(
        'wip.release.wizard.line',
        'wizard_id',
        string='Preview',
        readonly=True,
    )
    total_amount = fields.Monetary(
        string='Total To Release',
        currency_field='currency_id',
        compute='_compute_total_amount',
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )

    @api.depends('line_ids.wip_amount')
    def _compute_total_amount(self):
        for wizard in self:
            wizard.total_amount = sum(wizard.line_ids.mapped('wip_amount'))

    @api.model
    def _build_preview_values(self, masters):
        values = []
        for master in masters:
            for project in master._get_group_projects():
                amount = sum(project._get_unreleased_wip_lines().mapped('balance'))
                values.append((0, 0, {
                    'master_project_id': master.id,
                    'x_global_project_number': master.x_global_project_number,
                    'company_id': project.company_id.id,
                    'project_id': project.id,
                    'wip_amount': amount,
                }))
        return values

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        master_ids = self.env.context.get('default_master_project_ids') or []
        if master_ids and 'line_ids' in fields_list:
            masters = self.env['project.project'].sudo().browse(master_ids).exists()
            result['line_ids'] = self._build_preview_values(masters)
        return result

    @api.onchange('master_project_ids')
    def _onchange_master_project_ids(self):
        self.line_ids = [(5, 0, 0)]
        self.line_ids = self._build_preview_values(self.master_project_ids)

    def _check_company_access(self, projects):
        allowed = self.env.user.company_ids
        blocked = projects.mapped('company_id').filtered(lambda c: c not in allowed)
        if blocked:
            raise UserError(_(
                'You do not have access to the following companies involved in this '
                'release:\n\n%s\n\nAsk an administrator to grant access before running '
                'the release.'
            ) % '\n'.join(blocked.mapped('name')))
        return True

    def _check_lock_dates(self, projects):
        blocked = []
        for company in projects.mapped('company_id'):
            for attr, label in (
                ('fiscalyear_lock_date', _('Journal Entries Lock Date')),
                ('hard_lock_date', _('Hard Lock Date')),
                ('tax_lock_date', _('Tax Lock Date')),
            ):
                lock_date = getattr(company, attr, False)
                if lock_date and self.accounting_date <= lock_date:
                    blocked.append('%s: %s (%s)' % (company.name, lock_date, label))
        if blocked:
            raise UserError(_(
                'Accounting date %(date)s falls inside a locked period for:\n\n%(list)s\n\n'
                'Choose a later accounting date. The whole batch is cancelled so that no '
                'company is released partially.'
            ) % {
                'date': self.accounting_date,
                'list': '\n'.join(blocked),
            })
        return True

    def _check_contract_revisions(self, master):
        order = master.x_sale_order_id
        if not order:
            return True
        pending = order.sudo().x_revision_ids.filtered(
            lambda r: not (r.reason or '').strip()
        )
        if pending:
            raise UserError(_(
                'Sales order %(order)s has %(count)s contract revision(s) without a '
                'reason. Fill in the reason on every revision before releasing WIP for '
                'global project %(gp)s.'
            ) % {
                'order': order.name,
                'count': len(pending),
                'gp': master.x_global_project_number or '',
            })
        return True

    def _check_threshold(self, master):
        if self.is_manual_override:
            return True
        if master.x_invoice_progress < master.x_release_threshold:
            raise UserError(_(
                'Global project %(gp)s has an invoice progress of %(progress).2f%% which '
                'is below the release threshold of %(threshold).2f%%. Tick Manual '
                'Override and provide a reason to release it anyway.'
            ) % {
                'gp': master.x_global_project_number or master.name,
                'progress': master.x_invoice_progress,
                'threshold': master.x_release_threshold,
            })
        return True

    def action_release(self):
        self.ensure_one()
        if not self.master_project_ids:
            raise UserError(_('Select at least one global project to release.'))
        if self.is_manual_override and not (self.override_reason or '').strip():
            raise UserError(_(
                'Manual Override requires a Release Reason.'
            ))

        batches = self.env['wip.release.batch']
        for master in self.master_project_ids:
            if not master.x_global_project_number:
                raise UserError(_(
                    'Project %s has no Global Project Number.'
                ) % master.name)

            projects = master._get_group_projects()
            projects._check_wip_configuration()
            self._check_company_access(projects)
            self._check_lock_dates(projects)
            self._check_contract_revisions(master)
            self._check_threshold(master)

            released_before = self.env['wip.release.batch'].sudo().search_count([
                ('x_global_project_number', '=', master.x_global_project_number),
                ('state', '=', 'done'),
            ])
            batch = self.env['wip.release.batch'].sudo().create({
                'x_global_project_number': master.x_global_project_number,
                'master_project_id': master.id,
                'accounting_date': self.accounting_date,
                'release_type': 'additional' if released_before else 'initial',
                'is_manual_override': self.is_manual_override,
                'override_reason': self.override_reason,
                'remarks': self.remarks,
                'currency_id': (
                    master.company_id.currency_id.id or self.env.company.currency_id.id
                ),
            })
            batch.action_execute()
            batches |= batch

        return {
            'type': 'ir.actions.act_window',
            'name': _('WIP Release Batch'),
            'res_model': 'wip.release.batch',
            'view_mode': 'list,form',
            'domain': [('id', 'in', batches.ids)],
        }


class WipReleaseWizardLine(models.TransientModel):
    _name = 'wip.release.wizard.line'
    _description = 'WIP Release Wizard Line'

    wizard_id = fields.Many2one('wip.release.wizard', required=True, ondelete='cascade')
    master_project_id = fields.Many2one('project.project', string='Global Project')
    x_global_project_number = fields.Char(string='Global Project Number')
    company_id = fields.Many2one('res.company', string='Company')
    project_id = fields.Many2one('project.project', string='Project')
    currency_id = fields.Many2one(related='company_id.currency_id')
    wip_amount = fields.Monetary(string='Unreleased WIP', currency_field='currency_id')
