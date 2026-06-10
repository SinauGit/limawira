from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    restrict_modules = fields.Boolean(
        string='Restrict Module Visibility',
        default=False,
    )
    allowed_modules = fields.Char(
        string='Allowed Modules',
        help=(
            'Comma-separated technical module names that are visible for this company. '
            'Example: stock,stock_account,uom,product\n'
            'Leave empty to allow all modules (restriction disabled).\n'
            'Core modules (base, web, mail, bus) are always allowed.'
        ),
    )
