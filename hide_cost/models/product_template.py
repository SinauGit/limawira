from odoo import api, fields, models

class ProductTemplate(models.Model):
  _inherit = "product.template"

  free_qty = fields.Float(
      'Free to Use',
       compute='_compute_free_qty',
       digits='Product Unit of Measure',
   )

  @api.depends('product_variant_ids.free_qty')
  def _compute_free_qty(self):
     for tmpl in self:
          tmpl.free_qty = sum(tmpl.product_variant_ids.mapped('free_qty'))