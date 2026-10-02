from odoo import fields, models

ENTRY_TYPES = [
    ('reclass', 'Reclassification'),
    ('backdated', 'Backdated'),
    ('reversal_reclass', 'Reversal Reclassification'),
    ('reversal_backdated', 'Reversal Backdated'),
]


class AccountMove(models.Model):
    _inherit = 'account.move'

    lww_project_id = fields.Many2one(
        'project.project', string='Recognition Project', copy=False, readonly=True,
        index='btree_not_null')
    lww_picking_id = fields.Many2one(
        'stock.picking', string='Delivery / Return Order', copy=False, readonly=True,
        index='btree_not_null')
    lww_origin_move_id = fields.Many2one(
        'account.move', string='Origin Journal', copy=False, readonly=True,
        index='btree_not_null')
    lww_entry_type = fields.Selection(
        ENTRY_TYPES, string='Recognition Entry Type', copy=False, readonly=True,
        index='btree_not_null')
    lww_recognition_year = fields.Integer(
        string='Recognition Year', copy=False, readonly=True)

    _sql_constraints = [
        ('lww_picking_entry_type_uniq',
         'unique(lww_picking_id, lww_entry_type)',
         'A recognition journal of this type already exists for this transfer.'),
    ]

    def _post(self, soft=True):
        res = super()._post(soft=soft)
        self._lww_refresh_projects()
        return res

    def button_draft(self):
        res = super().button_draft()
        self._lww_refresh_projects()
        return res

    def button_cancel(self):
        res = super().button_cancel()
        self._lww_refresh_projects()
        return res

    def _lww_refresh_projects(self):
        invoices = self.filtered(lambda m: m.move_type in ('out_invoice', 'out_refund'))
        if not invoices:
            return
        orders = invoices.sudo().line_ids.sale_line_ids.order_id
        if not orders:
            return
        projects = self.env['project.project'].sudo()._lww_projects_from_orders(orders)
        projects._lww_refresh_billing()
