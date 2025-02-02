from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.constrains('name')
    def _check_unique_vendor_name(self):
        for partner in self:
            if partner.supplier_rank > 0:  # Hanya cek untuk vendor
                duplicate = self.search([
                    ('id', '!=', partner.id),
                    ('name', 'ilike', partner.name),
                    ('supplier_rank', '>', 0),
                    ('active', '=', True)
                ]).filtered(lambda p: p.name.lower() == partner.name.lower())
                
                if duplicate:
                    raise ValidationError(_(
                        "Vendor with name '%s' already exists (case insensitive). "
                        "Vendor names must be unique regardless of letter case.",
                        partner.name
                    ))