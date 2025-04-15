from odoo import fields, models

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    ship_via = fields.Selection([
        ('1', 'Lokal: Diantar'),
        ('2', 'Lokal: Diambil'),
        ('3', 'Lokal: Air'),
        ('4', 'Lokal: Sea'),
    ], string='Ship Via')


