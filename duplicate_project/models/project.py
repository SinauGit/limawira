from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

class Project(models.Model):
    _inherit = 'project.project'

    @api.constrains('name')
    def _check_unique_name(self):
        for project in self:
            # Cek duplikasi nama hanya untuk proyek yang aktif (case insensitive)
            duplicate = self.search([
                ('id', '!=', project.id),
                ('name', 'ilike', project.name),
                ('active', '=', True)
            ]).filtered(lambda p: p.name.lower() == project.name.lower())
            
            if duplicate:
                raise ValidationError(_(
                    "Project with name '%s' already exists (case insensitive). "
                    "Project names must be unique regardless of letter case.", 
                    project.name
                ))
