from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """This class inherits 'res.config.settings' model and adds fields
    to the settings"""
    _inherit = 'res.config.settings'

    so_order_approval = fields.Boolean(
        string="Sale Discount Approval",
        default=lambda self: self.env.user.company_id.so_double_validation ==
                             'two_step', help="Activate/disable "
                                              "sale order approval.")
    so_double_validation = fields.Selection(
        related='company_id.so_double_validation',
        string="Levels of Approvals *", readonly=False,
        help="Provide a double validation mechanism for sales discount.")
    so_double_validation_limit = fields.Float(
        string="Discount limit requires approval in %",
        related='company_id.so_double_validation_limit', readonly=False,
        help="Minimum discount percentage for which a double validation is "
             "required."
    )

    po_order_approval = fields.Boolean(
        string="Persetujuan Diskon Pembelian",
        default=lambda self: self.env.user.company_id.po_double_validation == 'two_step',
        help="Aktifkan/nonaktifkan persetujuan untuk diskon pembelian.")
    
    po_double_validation = fields.Selection(
        related='company_id.po_double_validation',
        string="Tingkat Persetujuan", readonly=False,
        help="Menyediakan mekanisme validasi ganda untuk diskon pembelian.")
    
    po_double_validation_limit = fields.Float(
        string="Batas diskon yang memerlukan persetujuan dalam %",
        related='company_id.po_double_validation_limit', readonly=False,
        help="Persentase diskon minimum yang memerlukan validasi ganda."
    )

    def set_values(self):
        """Function to set values"""
        super(ResConfigSettings, self).set_values()
        self.so_double_validation = 'two_step' if self.so_order_approval \
            else 'one_step'
        self.po_double_validation = 'two_step' if self.po_order_approval else 'one_step'
