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

class ProductCategory(models.Model):
    _inherit = 'product.category'

    @api.constrains('name', 'parent_id')
    def _check_unique_category_name(self):
        for category in self:
            domain = [
                ('id', '!=', category.id),
                ('name', 'ilike', category.name),
                ('parent_id', '=', category.parent_id.id),
            ]
            duplicate = self.search(domain).filtered(
                lambda c: c.name.lower() == category.name.lower()
            )
            
            if duplicate:
                raise ValidationError(_(
                    "Product Category with name '%s' already exists under the same parent category "
                    "(case insensitive). Category names must be unique within the same level.",
                    category.name
                ))