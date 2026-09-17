from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    edit_confirmed_allowed = fields.Boolean(
        related='order_id.edit_confirmed_allowed',
    )

    @api.onchange('product_uom')
    def _onchange_product_uom_edit_confirmed_warning(self):
        if self.order_id.state == 'sale' and self.qty_invoiced > 0:
            return {
                'warning': {
                    'title': "Baris Sudah Diinvoice",
                    'message': (
                        "Baris ini sudah memiliki qty yang diinvoice. "
                        "Perubahan UoM TIDAK akan otomatis mengubah invoice "
                        "yang sudah dibuat sebelumnya."
                    ),
                }
            }
