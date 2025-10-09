from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    # Field baru untuk description manual user
    custom_description = fields.Text(
        string='Description',
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