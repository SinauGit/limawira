from odoo import api, fields, models


class SaleOrder(models.Model):
    """Inherit 'sale.order' model and add fields needed"""
    _inherit = "sale.order"

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """Compute the total amounts of the SO."""
        for order in self:
            amount_untaxed = amount_tax = amount_discount = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                amount_discount += (
                                           line.product_uom_qty * line.price_unit * line.discount) / 100
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_discount': amount_discount,
                'amount_total': amount_untaxed + amount_tax,
            })

    state = fields.Selection(selection_add=[
        ('waiting', 'Waiting Approval'),
    ], string='Status', readonly=True, copy=False, index=True,
        default='draft', help="Status of quotation.")
    discount_type = fields.Selection([
    ('percent', 'Percentage'), 
    ('amount', 'Amount'),
    ('line_discount', 'Per Line')
], string='Discount type', default='line_discount')
    discount_rate = fields.Float('Discount Rate', digits=(16, 2))
    amount_discount = fields.Monetary(string='Discount', store=True,
                                      compute='_amount_all', readonly=True,)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True,
                                     readonly=True, compute='_amount_all')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True,
                                 compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True,
                                   compute='_amount_all')
    margin_test = fields.Float(string="Margin", compute='_compute_margin_test',)

    @api.depends('amount_untaxed','amount_tax','amount_total')
    def _compute_margin_test(self):
        # Compute logic for margin if sale_margin is installed
        if self.env['ir.module.module'].sudo().search(
                [('name', '=', 'sale_margin'), ('state', '=', 'installed')]):
            # If sale_margin is installed, calculate margin
            for record in self:
                print(record.margin, 'll')
                record.margin_test = record.margin
        else:
            for record in self:
                record.margin_test = False

    def action_confirm(self):
        discount = 0.0
        no_line = 0.0
        if self.company_id.so_double_validation == 'two_step':
            for line in self.order_line:
                no_line += 1
                discount += line.discount
            if no_line > 0:
                discount = (discount / no_line)
            if (self.company_id.so_double_validation_limit and discount >
                    self.company_id.so_double_validation_limit):
                self.state = 'waiting'
                return True
        super(SaleOrder, self).action_confirm()

    def action_approve(self):
        """This super the class and calls the action_confirm method on clicking
         approve button"""
        super(SaleOrder, self).action_confirm()
        return

    def _can_be_confirmed(self):
        """This function _can_be_confirmed adds waiting state """
        self.ensure_one()
        return self.state in {'draft', 'sent', 'waiting'}

    @api.onchange('discount_type', 'discount_rate', 'order_line')
    def supply_rate(self):
        for order in self:
            if order.discount_type == 'percent':
                for line in order.order_line:
                    line.discount = order.discount_rate
            elif order.discount_type == 'amount':
                total = 0.0
                for line in order.order_line:
                    total += round((line.product_uom_qty * line.price_unit))
                if order.discount_rate != 0:
                    discount = (order.discount_rate / total) * 100 if total > 0 else 0
                else:
                    discount = order.discount_rate
                for line in order.order_line:
                    line.discount = discount
                    new_sub_price = (line.price_unit * (discount / 100))
                    line.total_discount = line.price_unit - new_sub_price
            elif order.discount_type == 'line_discount':
                # Untuk tipe 'line_discount', kita biarkan diskon per line
                # tidak melakukan perubahan pada baris order, tetapi tetap menghitung amount_discount
                amount_discount = 0.0
                for line in order.order_line:
                    discount_value = (line.product_uom_qty * line.price_unit * line.discount) / 100
                    amount_discount += discount_value
                    line.total_discount = discount_value
                order.amount_discount = amount_discount

    def _prepare_invoice(self, ):
        """Super sale order class and update with fields"""
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.update({
            'discount_type': self.discount_type,
            'discount_rate': self.discount_rate,
            'amount_discount': self.amount_discount,
        })
        return invoice_vals

    def button_dummy(self):
        """The button_dummy method is intended to perform some action related
          to the supply rate and always return True"""
        self.supply_rate()
        return True
