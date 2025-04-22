from odoo import api, fields, models


class PurchaseOrder(models.Model):
    """Inherit 'purchase.order' model dan menambahkan field yang dibutuhkan"""
    _inherit = "purchase.order"

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """Menghitung total pada PO."""
        for order in self:
            amount_untaxed = amount_tax = amount_discount = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                amount_discount += (
                        line.product_qty * line.price_unit * line.discount) / 100
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_discount': amount_discount,
                'amount_total': amount_untaxed + amount_tax,
            })

    state = fields.Selection(selection_add=[
        ('waiting', 'Menunggu Persetujuan'),
    ], ondelete={'waiting': 'set default'})
    discount_type = fields.Selection(
        [('percent', 'Persentase'), ('amount', 'Jumlah')],
        string='Discount Type',
        default='amount', help="Tipe diskon yang digunakan.")
    discount_rate = fields.Float('Discount', digits=(16, 2),)
    amount_discount = fields.Monetary(string='Discount', store=True,
                                  compute='_amount_all', readonly=True,)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True,
                                 readonly=True, compute='_amount_all',
                                 help="Jumlah sebelum pajak.")
    amount_tax = fields.Monetary(string='Tax', store=True, readonly=True,
                             compute='_amount_all',
                             help="Pajak produk.")
    amount_total = fields.Monetary(string='Total', store=True, readonly=True,
                               compute='_amount_all',
                               help="Total jumlah.")

    def button_confirm(self):
        """Fungsi ini memanggil super button_confirm dengan validasi diskon"""
        discount = 0.0
        no_line = 0.0
        if self.company_id.po_double_validation == 'two_step':
            for line in self.order_line:
                no_line += 1
                discount += line.discount
            discount = (discount / no_line) if no_line else 0
            if (self.company_id.po_double_validation_limit and discount >
                    self.company_id.po_double_validation_limit):
                self.state = 'waiting'
                return True
        return super(PurchaseOrder, self).button_confirm()

    def action_approve(self):
        """Fungsi ini memanggil action_confirm saat tombol approve diklik"""
        return super(PurchaseOrder, self).button_confirm()

    @api.onchange('discount_type', 'discount_rate', 'order_line')
    def supply_rate(self):
        """Fungsi ini menghitung diskon berdasarkan perubahan pada
        discount_type, discount_rate dan order_line"""
        for order in self:
            if order.discount_type == 'percent':
                for line in order.order_line:
                    line.discount = order.discount_rate
            else:
                total = 0.0
                for line in order.order_line:
                    total += round((line.product_qty * line.price_unit))
                if order.discount_rate != 0 and total > 0:
                    discount = (order.discount_rate / total) * 100
                else:
                    discount = order.discount_rate
                for line in order.order_line:
                    line.discount = discount
                    new_sub_price = (line.price_unit * (discount / 100))
                    line.total_discount = line.price_unit - new_sub_price

    def _prepare_invoice(self):
        """Override _prepare_invoice untuk menambahkan field diskon"""
        invoice_vals = super(PurchaseOrder, self)._prepare_invoice()
        invoice_vals.update({
            'discount_type': self.discount_type,
            'discount_rate': self.discount_rate,
            'amount_discount': self.amount_discount,
        })
        return invoice_vals

    def button_dummy(self):
        """Method button_dummy untuk memperbarui perhitungan diskon"""
        self.supply_rate()
        return True
        
    # def action_open_discount_wizard(self):
    #     """Fungsi untuk membuka wizard diskon"""
    #     self.ensure_one()
    #     return {
    #         'name': "Diskon",
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'purchase.order.discount',
    #         'view_mode': 'form',
    #         'target': 'new',
    #     } 