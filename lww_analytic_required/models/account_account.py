from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    x_analytic_required = fields.Boolean(
        string='Required Analytical Distribution',
        help=(
            'Jika dicentang, baris Vendor Bill dan Journal Entry yang '
            'menggunakan akun ini wajib mengisi Analytic Distribution '
            'sebelum disimpan.'
        ),
    )
