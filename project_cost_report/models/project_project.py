# -*- coding: utf-8 -*-
from odoo import models, _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    def action_open_export_cost_report(self):
        """Open the export wizard for project cost report"""
        self.ensure_one()
        return {
            'name': _('Export Project Cost Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.cost.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.id,
            }
        }