from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LwwRecognitionWizard(models.TransientModel):
    _name = 'lww.recognition.wizard'
    _description = 'Project Recognition Wizard'

    project_id = fields.Many2one('project.project', required=True, readonly=True)
    mode = fields.Selection([('override', 'Override'), ('pending', 'Process Pending')], required=True, readonly=True)
    current_year = fields.Integer(related='project_id.lww_rec_year', string='Current Recognition Year')
    manual = fields.Boolean(string='Use Manual Year', default=True)
    new_year = fields.Integer(string='Recognition Year', default=lambda s: fields.Date.today().year)
    impacted_count = fields.Integer(compute='_compute_impacted', string='Affected Delivery Orders')
    confirm = fields.Boolean(string='I confirm these delivery orders will be processed')

    def _target_year(self):
        self.ensure_one()
        if self.mode == 'pending':
            return self.project_id.lww_rec_year
        if self.manual:
            return self.new_year
        return self.project_id.lww_auto_year

    def _pickings(self):
        self.ensure_one()
        pickings = self.project_id._lww_tracked_pickings()
        if self.mode == 'pending':
            return pickings.filtered(lambda p: p.x_accounting_status == 'pending')
        return pickings

    def _impacted(self):
        self.ensure_one()
        year = self._target_year()
        res = self.env['stock.picking']
        for picking in self._pickings():
            plan = picking._lww_plan(year)
            target = 'awaiting' if not year else ('returned' if picking.x_accounting_status == 'returned' else 'recognized')
            if plan in ('create', 'rebuild', 'reverse') or (
                    plan == 'status' and (picking.x_accounting_status != target
                                          or picking.x_recognition_year != (year or 0))):
                res |= picking
        return res

    @api.depends('project_id', 'mode', 'manual', 'new_year')
    def _compute_impacted(self):
        for wiz in self:
            wiz.impacted_count = len(wiz._impacted()) if wiz.project_id else 0

    def action_apply(self):
        self.ensure_one()
        project = self.project_id.sudo()
        if self.mode == 'override':
            if project.lww_auto_year:
                raise UserError(_('The billing threshold has been reached. The recognition year can no longer be overridden.'))
            if self.manual and self.new_year < 1900:
                raise UserError(_('Enter a valid recognition year.'))
        elif not project.lww_rec_year:
            raise UserError(_('This project has no recognition year yet.'))
        year = self._target_year()
        impacted = self._impacted()
        if impacted and not self.confirm:
            raise UserError(_('Tick the confirmation box to process %s delivery order(s).', len(impacted)))
        if impacted:
            config = impacted[:1]._lww_config()
            if not config:
                raise UserError(_('Project Recognition settings are missing for this company.'))
            impacted[:1]._lww_require_config(config)
            dates = []
            for picking in impacted:
                dates += picking._lww_required_dates(year)
            self.env['stock.picking']._lww_check_dates(project.company_id, dates)
        old_year = project.lww_rec_year
        if self.mode == 'override':
            project.write({'lww_manual_override': self.manual,
                           'lww_override_year': self.new_year if self.manual else 0})
            self.env['lww.recognition.log'].sudo().create({
                'company_id': project.company_id.id, 'project_id': project.id, 'action': 'year_override',
                'old_year': old_year, 'new_year': project.lww_rec_year,
                'note': _('Manual override') if self.manual else _('Override removed')})
        mode = project.lww_rec_mode
        for picking in self._pickings():
            if picking in impacted:
                picking._lww_sync(project.lww_rec_year, mode, action='recognized')
        return {'type': 'ir.actions.act_window_close'}
