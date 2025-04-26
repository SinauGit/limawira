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

    def set_values(self):
        """Function to set values"""
        super(ResConfigSettings, self).set_values()
        self.so_double_validation = 'two_step' if self.so_order_approval \
            else 'one_step'
