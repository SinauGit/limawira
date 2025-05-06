from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.depends('order_line.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = amount_discount = 0.0
            for line in order.order_line:
                line_price_subtotal = line.price_subtotal
                amount_untaxed += line_price_subtotal
                amount_tax += line.price_tax
                amount_discount += (line.product_qty * line.price_unit * line.discount) / 100
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_discount': amount_discount,
                'amount_total': amount_untaxed + amount_tax,
            })

    state = fields.Selection(selection_add=[
        ('waiting', 'Waiting Approval'),
    ], string='Status', readonly=True, copy=False, index=True, 
       help="Status of purchase order.")
    
    discount_type = fields.Selection(
        [('percent', 'All Percentage'), ('amount', 'Amount'), ('line_discount', 'Per Line')],
        string='Discount type',
        default='line_discount')
    
    discount_rate = fields.Float('Discount Rate', digits=(16, 2))
    
    amount_discount = fields.Monetary(string='Discount', store=True,
                                     compute='_amount_all', readonly=True)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True,
                                   readonly=True, compute='_amount_all')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True,
                               compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True,
                                 compute='_amount_all')

    @api.onchange('discount_type', 'discount_rate', 'order_line')
    def supply_rate(self):
        for order in self:
            if order.discount_type == 'percent':
                for line in order.order_line:
                    line.discount = order.discount_rate
            elif order.discount_type == 'amount':
                total = 0.0
                for line in order.order_line:
                    total += round((line.product_qty * line.price_unit))
                if order.discount_rate != 0 and total > 0:
                    discount = (order.discount_rate / total) * 100
                else:
                    discount = order.discount_rate
                for line in order.order_line:
                    line.discount = discount
            elif order.discount_type == 'line_discount':
                pass

    def button_confirm(self):
        discount = 0.0
        no_line = 0.0
        if self.company_id.po_double_validation == 'two_step':
            for line in self.order_line:
                no_line += 1
                discount += line.discount
            discount = (discount / no_line) if no_line > 0 else 0
            if (self.company_id.po_double_validation_limit and 
                    discount > self.company_id.po_double_validation_limit):
                self.state = 'waiting'
                return True
        return super(PurchaseOrder, self).button_confirm()

    def action_approve(self):
        """Fungsi untuk menyetujui pesanan dengan diskon"""
        return super(PurchaseOrder, self).button_confirm()

    def button_dummy(self):
        """Fungsi untuk memperbarui diskon"""
        self.supply_rate()
        return True
