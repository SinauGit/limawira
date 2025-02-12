from odoo import api, fields, models
from odoo.tools.float_utils import float_is_zero


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    discount_fixed = fields.Monetary(
        string="Discount (Amount)",
        default=0.0,
        currency_field="currency_id",
        help="Apply a fixed amount discount to this line.",
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

    # Override field discount
    discount = fields.Float(
        string='Discount (%)', 
        digits=(16, 15),  # 16 digit total, 15 digit desimal
        default=0.0
    )

    @api.depends("quantity", "discount", "price_unit", "tax_ids", "currency_id", "discount_fixed", "primary_discount_type")
    def _compute_totals(self):
        done_lines = self.env["account.move.line"]
        for line in self:
            if line.primary_discount_type == 'fixed' and not float_is_zero(
                line.original_discount_fixed, precision_rounding=line.currency_id.rounding
            ):
                price = line.price_unit - line.original_discount_fixed
                
                if line.tax_ids:
                    taxes_res = line.tax_ids._compute_all(
                        price,
                        quantity=line.quantity,
                        currency=line.currency_id,
                        product=line.product_id,
                        partner=line.partner_id,
                        is_refund=line.is_refund,
                    )
                    line.price_subtotal = taxes_res["total_excluded"]
                    line.price_total = taxes_res["total_included"]
                else:
                    subtotal = line.quantity * price
                    line.price_total = line.price_subtotal = subtotal

                done_lines |= line

        return super(AccountMoveLine, self - done_lines)._compute_totals()

    @api.onchange("discount_fixed")
    def _onchange_discount_fixed(self):
        if self.env.context.get("ignore_discount_onchange"):
            return
        self = self.with_context(ignore_discount_onchange=True)
        
        # Simpan nilai asli
        self.original_discount_fixed = self.discount_fixed
        self.primary_discount_type = 'fixed'
        
        # Hitung discount % hanya untuk display
        if self.price_unit:
            self.discount = (self.discount_fixed / self.price_unit) * 100

    @api.onchange("discount")
    def _onchange_discount(self):
        if self.env.context.get("ignore_discount_onchange"):
            return
        self = self.with_context(ignore_discount_onchange=True)
        
        # Simpan nilai asli
        self.original_discount = self.discount
        self.primary_discount_type = 'percentage'
        
        # Hitung discount_fixed hanya untuk display
        if self.price_unit > 0:
            self.discount_fixed = (self.discount / 100.0) * self.price_unit

    def _get_discount_from_fixed_discount(self):
        self.ensure_one()
        if float_is_zero(self.price_unit, precision_rounding=self.currency_id.rounding):
            return 0.0
        return (self.discount_fixed / self.price_unit) * 100
