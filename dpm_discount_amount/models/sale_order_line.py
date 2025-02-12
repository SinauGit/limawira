from odoo import api, fields, models
from odoo.tools.float_utils import float_is_zero


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    discount_fixed = fields.Monetary(
        string="Discount (Amount)",
        default=0.0,
        currency_field="currency_id",
        help="Terapkan diskon dengan nominal tetap pada baris ini.",
    )
    original_discount_fixed = fields.Monetary(
        string="Original Discount Amount",
        currency_field="currency_id",
        copy=False,
    )
    original_discount = fields.Float(
        string="Original Discount %",
        copy=False,
    )
    primary_discount_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage')
    ], string='Primary Discount Type', copy=False)

    # Override field discount bawaan Odoo
    discount = fields.Float(
        string='Discount (%)', 
        digits=(16, 15),  # 16 digit total, 15 digit desimal
        default=0.0
    )

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'discount_fixed', 'primary_discount_type')
    def _compute_amount(self):
        """Menyesuaikan perhitungan subtotal dengan mempertimbangkan diskon tetap."""
        done_lines = self.env['sale.order.line']
        for line in self:
            if line.primary_discount_type == 'fixed' and not float_is_zero(
                line.original_discount_fixed, precision_rounding=line.currency_id.rounding
            ):
                # Gunakan original_discount_fixed untuk perhitungan
                price = line.price_unit - line.original_discount_fixed
                
                if line.tax_id:
                    taxes = line.tax_id._compute_all(
                        price,
                        line.order_id.currency_id,
                        line.product_uom_qty,
                        product=line.product_id,
                        partner=line.order_id.partner_shipping_id,
                    )
                    line.update({
                        'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                        'price_total': taxes['total_included'],
                        'price_subtotal': taxes['total_excluded'],
                    })
                else:
                    subtotal = line.product_uom_qty * price
                    line.update({
                        'price_tax': 0.0,
                        'price_total': subtotal,
                        'price_subtotal': subtotal,
                    })
                done_lines |= line

        return super(SaleOrderLine, self - done_lines)._compute_amount()

    @api.onchange('discount_fixed')
    def _onchange_discount_fixed(self):
        """Menghitung persentase diskon berdasarkan nominal diskon tetap."""
        if self.env.context.get('ignore_discount_onchange'):
            return
        self = self.with_context(ignore_discount_onchange=True)
        
        # Simpan nilai asli
        self.original_discount_fixed = self.discount_fixed
        self.primary_discount_type = 'fixed'
        
        # Hitung discount % hanya untuk display
        if self.price_unit:
            self.discount = (self.discount_fixed / self.price_unit) * 100

    @api.onchange('discount')
    def _onchange_discount(self):
        """Menghitung nominal diskon tetap berdasarkan persentase diskon."""
        if self.env.context.get('ignore_discount_onchange'):
            return
        self = self.with_context(ignore_discount_onchange=True)
        
        # Simpan nilai asli
        self.original_discount = self.discount
        self.primary_discount_type = 'percentage'
        
        # Hitung discount_fixed hanya untuk display
        if self.price_unit > 0:
            self.discount_fixed = (self.discount / 100.0) * self.price_unit

    def _prepare_invoice_line(self, **optional_values):
        """Meneruskan nilai discount ke invoice line."""
        res = super()._prepare_invoice_line(**optional_values)
        res.update({
            'discount_fixed': self.original_discount_fixed if self.primary_discount_type == 'fixed' else self.discount_fixed,
            'original_discount_fixed': self.original_discount_fixed,
            'original_discount': self.original_discount,
            'primary_discount_type': self.primary_discount_type,
        })
        return res

    def _get_discount_from_fixed_discount(self):
        """Menghitung persentase diskon dari nominal diskon tetap."""
        self.ensure_one()
        if float_is_zero(self.price_unit, precision_rounding=self.currency_id.rounding):
            return 0.0
        # Gunakan original_discount_fixed jika tipe diskon adalah fixed
        discount_amount = self.original_discount_fixed if self.primary_discount_type == 'fixed' else self.discount_fixed
        return (discount_amount / self.price_unit) * 100