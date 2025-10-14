from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    # Field baru untuk description manual user
    custom_description = fields.Text(
        string='Description',
        store=True,
        readonly=False
    )

    @api.onchange('product_template_id', 'custom_description')
    def _onchange_custom_description(self):
        """Auto-fill custom_description with product name if empty"""
        if self.product_template_id and not self.custom_description:
            self.custom_description = self.product_template_id.name

    @api.model_create_multi
    def create(self, vals_list):
        """Set custom_description from product name on create if not provided"""
        for vals in vals_list:
            if vals.get('product_template_id') and not vals.get('custom_description'):
                product = self.env['product.template'].browse(vals['product_template_id'])
                vals['custom_description'] = product.name
        return super().create(vals_list)

    def write(self, vals):
        """Set custom_description from product name on write if empty"""
        res = super().write(vals)
        for record in self:
            if record.product_template_id and not record.custom_description:
                record.custom_description = record.product_template_id.name
        return res
    
    # @api.depends('custom_description')
    # def _compute_name(self):
    #     """
    #     Override: Gunakan custom_description sebagai name
    #     """
    #     for line in self:
    #         if line.custom_description:
    #             line.name = line.custom_description
    #         else:
    #             # Fallback ke logic standard jika custom_description kosong
    #             if not line.product_id and not line.is_downpayment:
    #                 continue

    #             lang = line.order_id._get_lang()
    #             if lang != self.env.lang:
    #                 line = line.with_context(lang=lang)

    #             if line.product_id:
    #                 line.name = line._get_sale_order_line_multiline_description_sale()
    #                 continue

    #             if line.is_downpayment:
    #                 line.name = line._get_downpayment_description()
    


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    # Related field - auto terisi dari SO line
    custom_description = fields.Text(
        string='Description',
        related='sale_line_ids.custom_description',
        store=True,
        readonly=False
    )
    
    # @api.depends('custom_description')
    # def _compute_name(self):
    #     """
    #     Override: Gunakan custom_description sebagai name
    #     """
    #     for line in self:
    #         if line.custom_description:
    #             line.name = line.custom_description
    #         else:
    #             # Fallback ke logic standard jika custom_description kosong
    #             super()._compute_name()