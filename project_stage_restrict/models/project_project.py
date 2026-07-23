from odoo import models, _
from odoo.exceptions import UserError


class ProjectProject(models.Model):
    _inherit = 'project.project'

    def write(self, vals):
        if 'stage_id' in vals and not self.env.su:
            user = self.env.user
            if user.has_group('project_stage_restrict.group_project_user_no_stage') and not user.has_group('project.group_project_manager'):
                for project in self:
                    if project.stage_id.id != vals['stage_id']:
                        raise UserError(_('You are not allowed to change the project stage.'))
        return super().write(vals)
