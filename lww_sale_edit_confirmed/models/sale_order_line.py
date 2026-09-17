from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    edit_confirmed_allowed = fields.Boolean(
        related='order_id.edit_confirmed_allowed',
    )

    @api.depends('state')
    def _compute_product_uom_readonly(self):
        # Jalankan logic asli Odoo dulu (readonly saat state in sale/cancel, dst),
        # lalu override jadi False khusus untuk user yang punya izin.
        super()._compute_product_uom_readonly()
        if self.env.user.has_group(
            'lww_sale_edit_confirmed.group_sale_edit_confirmed'
        ):
            for line in self:
                line.product_uom_readonly = False

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
