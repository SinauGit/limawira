from odoo import fields, models, _
from odoo.exceptions import AccessError, UserError


class RecognitionOverrideWizard(models.TransientModel):
    _name = 'lww.recognition.override.wizard'
    _description = 'Project Recognition Override'

    project_id = fields.Many2one('project.project', required=True, readonly=True)
    manual_override = fields.Boolean(string='Manual Override')
    year = fields.Integer(string='Recognition Year')

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        project = self.env['project.project'].browse(
            res.get('project_id') or self.env.context.get('default_project_id')).sudo()
        if project:
            res.setdefault('manual_override', project.lww_manual_override)
            res.setdefault('year', project.lww_override_year or project.lww_rec_year or fields.Date.today().year)
        return res

    def action_apply(self):
        self.ensure_one()
        if not self.env.user.has_group('lww_project_recognition.group_recognition_manager'):
            raise AccessError(_('Only Project Recognition Managers can override the recognition year.'))
        if self.manual_override and not (1990 <= self.year <= 2100):
            raise UserError(_('Please enter a valid recognition year.'))
        project = self.project_id.sudo()
        project.write({
            'lww_manual_override': self.manual_override,
            'lww_override_year': self.year if self.manual_override else 0,
        })
        if self.manual_override:
            body = _('Recognition year manually overridden to %s.', self.year)
        else:
            body = _('Manual override removed: recognition follows the billing milestone.')
        project.message_post(body=body)
        return {'type': 'ir.actions.act_window_close'}
