from odoo import fields, models


class ResCompany(models.Model):
    """Kelas ini mewarisi 'res.company' dan menambahkan po_double_validation,
    po_double_validation_limit untuk menambahkan batas validasi"""
    _inherit = 'res.company'

    po_double_validation = fields.Selection([
        ('one_step', 'Konfirmasi pesanan pembelian dalam satu langkah'),
        ('two_step', 'Memerlukan 2 level persetujuan untuk mengkonfirmasi pesanan pembelian')
    ], string="Level Persetujuan", default='one_step',
        help="Menyediakan mekanisme validasi ganda untuk diskon pembelian.")
    po_double_validation_limit = fields.Float(
        string="Persentase Discount yang memerlukan validasi ganda",
        help="Persentase diskon minimum yang memerlukan validasi ganda.")
    # purchase_discount_product_id = fields.Many2one(
    #     'product.product', string="Produk Discount", 
    #     domain=[('type', '=', 'service')],
    #     help="Produk yang digunakan untuk baris diskon dalam pesanan pembelian.") 