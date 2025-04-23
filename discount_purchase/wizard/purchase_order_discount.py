from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class PurchaseOrderDiscount(models.TransientModel):
    _name = 'purchase.order.discount'
    _description = "Purchase Discount Wizard"

    purchase_order_id = fields.Many2one(
        'purchase.order', default=lambda self: self.env.context.get('active_id'), required=True)
    company_id = fields.Many2one(related='purchase_order_id.company_id')
    currency_id = fields.Many2one(related='purchase_order_id.currency_id')
    discount_amount = fields.Monetary(string="Amount")
    tax_ids = fields.Many2many(
        string="Taxes",
        help="Taxes to add on the discount line.",
        comodel_name='account.tax',
        domain="[('type_tax_use', '=', 'purchase'), ('company_id', '=', company_id)]",
    )

    @api.onchange('purchase_order_id')
    def _onchange_purchase_order(self):
        if self.purchase_order_id and self.purchase_order_id.company_id.purchase_discount_product_id:
            self.tax_ids = self.purchase_order_id.company_id.purchase_discount_product_id.supplier_taxes_id

    def _prepare_discount_product_values(self):
        self.ensure_one()
        return {
            'name': _('Discount'),
            'type': 'service',
            'purchase_method': 'purchase',
            'standard_price': 0.0,
            'company_id': self.company_id.id,
            'taxes_id': None,
        }

    def _get_discount_product(self):
        self.ensure_one()
        discount_product = self.company_id.purchase_discount_product_id
        if not discount_product:
            # Create default discount product if not exists
            product_vals = self._prepare_discount_product_values()
            discount_product = self.env['product.product'].sudo().create(product_vals)
            self.company_id.sudo().write({
                'purchase_discount_product_id': discount_product.id
            })
        return discount_product

    def _prepare_discount_line_values(self, product, amount, taxes):
        self.ensure_one()
        return {
            'order_id': self.purchase_order_id.id,
            'product_id': product.id,
            'price_unit': -amount,
            'product_qty': 1.0,
            'taxes_id': [fields.Command.set(taxes.ids)],
            'sequence': 999,
        }

    def action_apply_discount(self):
        self.ensure_one()
        self = self.with_company(self.company_id)
        discount_product = self._get_discount_product()
        
        vals = self._prepare_discount_line_values(
            product=discount_product,
            amount=self.discount_amount,
            taxes=self.tax_ids,
        )
        self.env['purchase.order.line'].create(vals) 