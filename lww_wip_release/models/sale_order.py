from odoo import api, fields, models

SKIP_CTX = 'lww_skip_contract_revision'


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_original_contract_value = fields.Monetary(
        string='Original Contract Value',
        currency_field='currency_id',
        readonly=True,
        copy=False,
    )
    x_last_contract_value = fields.Monetary(
        string='Last Captured Value',
        currency_field='currency_id',
        readonly=True,
        copy=False,
    )
    x_current_contract_value = fields.Monetary(
        string='Current Contract Value',
        related='amount_total',
        currency_field='currency_id',
    )
    x_revision_ids = fields.One2many(
        'sale.contract.revision',
        'order_id',
        string='Contract Revisions',
    )
    x_contract_revision_count = fields.Integer(
        string='Revision Count',
        compute='_compute_x_contract_revision_count',
        store=True,
    )
    x_pending_revision_count = fields.Integer(
        string='Revisions Without Reason',
        compute='_compute_x_contract_revision_count',
        store=True,
    )
    x_project_ids = fields.One2many(
        'project.project',
        'x_sale_order_id',
        string='WIP Projects',
    )

    @api.depends('x_revision_ids', 'x_revision_ids.reason')
    def _compute_x_contract_revision_count(self):
        for order in self:
            revisions = order.x_revision_ids
            order.x_contract_revision_count = len(revisions)
            order.x_pending_revision_count = len(
                revisions.filtered(lambda r: not (r.reason or '').strip())
            )

    def _capture_contract_revision(self):
        if self.env.context.get(SKIP_CTX):
            return
        revision_model = self.env['sale.contract.revision'].sudo()
        for order in self:
            if order.state not in ('sale',):
                continue
            old_value = order.x_last_contract_value
            new_value = order.amount_total
            if (
                not order.x_original_contract_value
                and not order.x_revision_ids
            ):
                order.with_context(**{SKIP_CTX: True}).sudo().write({
                    'x_original_contract_value': new_value,
                    'x_last_contract_value': new_value,
                })
                continue
            if order.currency_id.is_zero(new_value - old_value):
                continue
            revision_model.create({
                'order_id': order.id,
                'old_value': old_value,
                'new_value': new_value,
                'revision_date': fields.Datetime.now(),
                'user_id': self.env.user.id,
            })
            order.with_context(**{SKIP_CTX: True}).sudo().write({
                'x_last_contract_value': new_value,
            })

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            order.with_context(**{SKIP_CTX: True}).sudo().write({
                'x_original_contract_value': order.amount_total,
                'x_last_contract_value': order.amount_total,
            })
        return res

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get(SKIP_CTX):
            self._capture_contract_revision()
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.order_id._capture_contract_revision()
        return lines

    def write(self, vals):
        res = super().write(vals)
        self.order_id._capture_contract_revision()
        return res

    def unlink(self):
        orders = self.order_id
        res = super().unlink()
        orders.exists()._capture_contract_revision()
        return res
