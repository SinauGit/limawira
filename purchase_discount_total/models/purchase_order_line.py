from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    """Inherit purchase.order.line model dan menambahkan field total_discount"""
    _inherit = "purchase.order.line"

    discount = fields.Float(string='Diskon (%)', digits=(16, 20), default=0.0,
                         help="Masukkan nilai diskon")
    total_discount = fields.Float(string="Discount Total", default=0.0,
                               store=True)

    @api.depends('discount', 'price_unit', 'product_qty', 'taxes_id')
    def _compute_amount(self):
        """Menghitung total diskon berdasarkan perubahan pada discount, price_unit, atau product_qty"""
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.taxes_id.compute_all(price, line.order_id.currency_id, line.product_qty, product=line.product_id, partner=line.order_id.partner_id)
            
            # Menghitung total diskon
            line.total_discount = line.price_unit * line.product_qty * line.discount / 100.0
            
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            }) 