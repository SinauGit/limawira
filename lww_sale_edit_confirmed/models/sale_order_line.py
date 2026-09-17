from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('state', 'order_id.locked')
    def _compute_product_uom_readonly(self):
        # Jalankan logic asli Odoo dulu, lalu buka lagi kalau order-nya
        # confirmed tapi belum (atau sudah tidak) di-Lock.
        super()._compute_product_uom_readonly()
        for line in self:
            if line.state == 'sale' and not line.order_id.locked:
                line.product_uom_readonly = False

    @api.onchange('product_uom')
    def _onchange_product_uom_edit_confirmed_warning(self):
        if (
            self.order_id.state == 'sale'
            and not self.order_id.locked
            and self.qty_invoiced > 0
        ):
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
