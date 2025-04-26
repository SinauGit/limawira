from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Kelas ini mewarisi 'res.config.settings' model dan menambahkan field
    ke pengaturan"""
    _inherit = 'res.config.settings'

    po_order_approval = fields.Boolean(
        string="Persetujuan Discount Pembelian",
        default=lambda self: self.env.user.company_id.po_double_validation ==
                             'two_step', help="Aktifkan/nonaktifkan "
                                              "persetujuan pesanan pembelian.")
    po_double_validation = fields.Selection(
        related='company_id.po_double_validation',
        string="Level Persetujuan *", readonly=False,
        help="Menyediakan mekanisme validasi ganda untuk diskon pembelian.")
    po_double_validation_limit = fields.Float(
        string="Batas diskon memerlukan persetujuan dalam %",
        related='company_id.po_double_validation_limit', readonly=False,
        help="Persentase diskon minimum yang memerlukan validasi ganda."
    )
    # purchase_discount_product_id = fields.Many2one(
    #     related='company_id.purchase_discount_product_id',
    #     string="Produk Discount", readonly=False,
    #     domain=[('type', '=', 'service')],
    #     help="Produk yang digunakan untuk baris diskon dalam pesanan pembelian."
    # )

    def set_values(self):
        """Fungsi untuk mengatur nilai"""
        super(ResConfigSettings, self).set_values()
        self.po_double_validation = 'two_step' if self.po_order_approval \
            else 'one_step' 