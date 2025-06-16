from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    director = fields.Char(string='Director')
