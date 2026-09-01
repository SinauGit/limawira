from odoo import api, fields, models


class SaleContractRevision(models.Model):
    _name = 'sale.contract.revision'
    _description = 'Sale Contract Revision'
    _order = 'revision_date desc, id desc'

    order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='order_id.company_id',
        store=True,
        index=True,
    )
    currency_id = fields.Many2one(related='order_id.currency_id')
    old_value = fields.Monetary(string='Old Value', currency_field='currency_id')
    new_value = fields.Monetary(string='New Value', currency_field='currency_id')
    difference = fields.Monetary(
        string='Difference',
        currency_field='currency_id',
        compute='_compute_difference',
        store=True,
    )
    revision_date = fields.Datetime(string='Update Date', default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='Updated By', default=lambda self: self.env.user)
    reason = fields.Text(string='Reason')

    @api.depends('old_value', 'new_value')
    def _compute_difference(self):
        for rec in self:
            rec.difference = rec.new_value - rec.old_value
