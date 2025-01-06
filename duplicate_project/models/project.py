from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

class Project(models.Model):
    _inherit = 'project.project'

    @api.constrains('name')
    def _check_unique_name(self):
        for project in self:
            # Cek duplikasi nama hanya untuk proyek yang aktif
            duplicate = self.search([
                ('id', '!=', project.id),
                ('name', '=', project.name),
                ('active', '=', True)  # Hanya cek proyek yang aktif
            ])
            if duplicate:
                raise ValidationError(_(
                    "Project with name '%s' already exists. Project names must be unique.", 
                    project.name
                ))
