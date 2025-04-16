from odoo import fields, models

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    ship_via = fields.Selection([
        ('1', 'Diantar'),
        ('2', 'Diambil'),
        ('3', 'Air'),
        ('4', 'Sea'),
    ], string='Ship Via')


