from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrderDiscount(models.TransientModel):
    _name = 'purchase.order.discount'
    _description = 'Purchase Order Discount'

    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', 
                                     required=True, readonly=True)
    company_id = fields.Many2one('res.company', related='purchase_order_id.company_id', 
                              string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', related='purchase_order_id.currency_id', 
                               string='Currency', readonly=True)
    discount_amount = fields.Monetary(string='Jumlah Diskon', required=True,
                                    currency_field='currency_id')
    discount_type = fields.Selection([
        ('percent', 'Persentase'),
        ('amount', 'Jumlah Tetap')
    ], string='Tipe Diskon', default='amount')
    discount_percentage = fields.Float(string='Persentase Diskon (%)',
                                     digits=(16, 2))
    tax_ids = fields.Many2many('account.tax', string='Pajak', 
                            domain="[('type_tax_use', '=', 'purchase'), ('company_id', '=', company_id)]")

    @api.model
    def default_get(self, fields_list):
        """Set default values saat wizard diinisiasi"""
        result = super(PurchaseOrderDiscount, self).default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            purchase_order = self.env['purchase.order'].browse(active_id)
            result['purchase_order_id'] = purchase_order.id
            
            # Inisialisasi tax_ids dari produk diskon jika tersedia
            if purchase_order.company_id.purchase_discount_product_id:
                result['tax_ids'] = purchase_order.company_id.purchase_discount_product_id.supplier_taxes_id.ids
        return result
    
    @api.onchange('discount_type', 'discount_amount', 'discount_percentage', 'purchase_order_id')
    def _onchange_discount(self):
        """Menghitung nilai diskon berdasarkan tipe yang dipilih"""
        if not self.purchase_order_id:
            return
            
        total_amount = sum(line.price_subtotal for line in self.purchase_order_id.order_line)
        
        if self.discount_type == 'percent' and self.discount_percentage:
            self.discount_amount = (self.discount_percentage / 100.0) * total_amount
        elif self.discount_type == 'amount' and total_amount and self.discount_amount:
            self.discount_percentage = (self.discount_amount / total_amount) * 100.0

    def _get_discount_product(self):
        """Mendapatkan atau membuat produk diskon"""
        self.ensure_one()
        discount_product = self.company_id.purchase_discount_product_id
        if not discount_product:
            # Membuat produk diskon default jika belum ada
            product_vals = {
                'name': _('Diskon'),
                'type': 'service',
                'purchase_method': 'purchase',
                'standard_price': 0.0,
                'company_id': self.company_id.id,
                'supplier_taxes_id': [(6, 0, self.tax_ids.ids)],
            }
            discount_product = self.env['product.product'].sudo().create(product_vals)
            self.company_id.sudo().write({
                'purchase_discount_product_id': discount_product.id
            })
        return discount_product

    def action_apply_discount(self):
        """Menerapkan diskon ke pesanan pembelian"""
        self.ensure_one()
        if self.discount_amount <= 0:
            raise UserError(_('Jumlah diskon harus lebih besar dari nol.'))
            
        purchase_order = self.purchase_order_id
        total_amount = sum(line.price_subtotal for line in purchase_order.order_line)
        
        if not total_amount:
            raise UserError(_('Tidak ada baris pesanan atau jumlah total nol.'))
            
        # Mengatur diskon pada pesanan pembelian
        if self.discount_type == 'percent':
            purchase_order.write({
                'discount_type': 'percent',
                'discount_rate': self.discount_percentage,
            })
        else:
            purchase_order.write({
                'discount_type': 'amount',
                'discount_rate': self.discount_amount,
            })
        
        # Mengupdate diskon di baris pesanan
        purchase_order.supply_rate()
        
        # Jika menggunakan pendekatan baris diskon terpisah
        if self.env.context.get('add_discount_line', False):
            discount_product = self._get_discount_product()
            vals = {
                'order_id': purchase_order.id,
                'product_id': discount_product.id,
                'price_unit': -self.discount_amount,
                'product_qty': 1.0,
                'taxes_id': [(6, 0, self.tax_ids.ids)],
                'sequence': 999,
            }
            self.env['purchase.order.line'].create(vals)
        
        return {'type': 'ir.actions.act_window_close'} 