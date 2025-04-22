from odoo import fields, models

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    ship_via = fields.Selection([
        ('Diantar', 'Diantar'),
        ('Diambil', 'Diambil'),
        ('Air', 'Air'),
        ('Sea', 'Sea'),
    ], string='Ship Via', default = 'Diantar')


