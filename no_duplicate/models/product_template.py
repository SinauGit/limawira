from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.constrains('name')
    def _check_unique_product_name(self):
        for product in self:
            duplicate = self.search([
                ('id', '!=', product.id),
                ('name', 'ilike', product.name),
                ('active', '=', True)
            ]).filtered(lambda p: p.name.lower() == product.name.lower())
            
            if duplicate:
                raise ValidationError(_(
                    "Product with name '%s' already exists (case insensitive). "
                    "Product names must be unique regardless of letter case.",
                    product.name
                ))