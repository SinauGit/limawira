from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class ProjectProject(models.Model):
    _inherit = 'project.project'

    lww_manual_override = fields.Boolean(string='Manual Recognition Year', copy=False, tracking=False)
    lww_override_year = fields.Integer(string='Override Year', copy=False)
    lww_auto_year = fields.Integer(string='Billing Year', copy=False, readonly=True)
    lww_auto_date = fields.Date(string='Threshold Date', copy=False, readonly=True)
    lww_rec_year = fields.Integer(string='Recognition Year', compute='_compute_lww_rec_year', store=True)
    lww_rec_mode = fields.Selection([('auto', 'Automatic'), ('manual', 'Manual')],
                                    compute='_compute_lww_rec_year', store=True, string='Recognition Mode')
    lww_sale_order_id = fields.Many2one('sale.order', string='Recognition Sales Order', compute='_compute_lww_sale_order_id',
                                        search='_search_lww_sale_order_id')
    lww_progress = fields.Float(string='Billing Progress (%)', compute='_compute_lww_progress')
    lww_awaiting_count = fields.Integer(compute='_compute_lww_counts')
    lww_pending_count = fields.Integer(compute='_compute_lww_counts')
    lww_recognized_count = fields.Integer(compute='_compute_lww_counts')
    lww_move_count = fields.Integer(compute='_compute_lww_counts')

    @api.depends('lww_manual_override', 'lww_override_year', 'lww_auto_year')
    def _compute_lww_rec_year(self):
        for project in self:
            if project.lww_manual_override and project.lww_override_year:
                project.lww_rec_year = project.lww_override_year
                project.lww_rec_mode = 'manual'
            elif project.lww_auto_year:
                project.lww_rec_year = project.lww_auto_year
                project.lww_rec_mode = 'auto'
            else:
                project.lww_rec_year = 0
                project.lww_rec_mode = False

    def _lww_sale_order(self):
        self.ensure_one()
        order = self.env['sale.order'].sudo().search(
            [('project_id', '=', self.id), ('state', '!=', 'cancel')], limit=1, order='id')
        return order or (self.sale_order_id or self.reinvoiced_sale_order_id).sudo()

    @api.depends('sale_line_id', 'reinvoiced_sale_order_id')
    def _compute_lww_sale_order_id(self):
        for project in self:
            project.lww_sale_order_id = project._lww_sale_order()

    def _search_lww_sale_order_id(self, operator, value):
        if operator not in ('=', '!=') or value is not False:
            raise UserError(_('Unsupported search on Recognition Sales Order.'))
        by_so = self.env['sale.order'].sudo().search(
            [('project_id', '!=', False), ('state', '!=', 'cancel')]).project_id.ids
        projects = self.sudo().with_context(active_test=False).search([
            '|', '|', ('id', 'in', by_so), ('sale_line_id', '!=', False), ('reinvoiced_sale_order_id', '!=', False)])
        return [('id', 'in' if operator == '!=' else 'not in', projects.ids)]

    def _lww_invoices(self):
        self.ensure_one()
        if not self.account_id:
            return self.env['account.move']
        lines = self.env['account.move.line'].sudo().search([
            ('analytic_distribution', 'in', self.account_id.ids),
            ('move_id.move_type', '=', 'out_invoice'),
            ('move_id.state', '=', 'posted'),
        ])
        return lines.move_id

    def _lww_progress_data(self):
        self.ensure_one()
        order = self._lww_sale_order()
        config = self.env['lww.recognition.config']._get(self.company_id)
        total = order.amount_total if order else 0.0
        invoices = self._lww_invoices().sorted(lambda m: (m.date, m.id))
        cumulative = 0.0
        reached = False
        for inv in invoices:
            cumulative += inv.amount_total
            if config and total > 0 and not reached and \
                    float_compare(cumulative * 100.0, total * config.threshold, precision_digits=4) >= 0:
                reached = inv.date
        pct = (cumulative / total * 100.0) if total > 0 else 0.0
        return pct, reached

    def _compute_lww_progress(self):
        for project in self:
            project.lww_progress = project._lww_progress_data()[0]

    def _lww_all_move_ids(self):
        self.ensure_one()
        Move = self.env['account.move'].sudo()
        moves = Move.search([('lww_project_id', '=', self.id)])
        pickings = moves.filtered(lambda m: m.lww_active and m.lww_entry_type in ('reclass', 'backdated')).lww_picking_id
        if pickings:
            layers = self.env['stock.valuation.layer'].sudo().search([('stock_move_id.picking_id', 'in', pickings.ids)])
            moves |= layers.account_move_id
        return moves.ids

    def _compute_lww_counts(self):
        Picking = self.env['stock.picking'].sudo()
        for project in self:
            data = Picking._read_group([('x_project_id', '=', project.id)], ['x_accounting_status'], ['__count'])
            counts = {status: count for status, count in data}
            project.lww_awaiting_count = counts.get('awaiting', 0)
            project.lww_pending_count = counts.get('pending', 0)
            project.lww_recognized_count = counts.get('recognized', 0) + counts.get('returned', 0)
            project.lww_move_count = len(project._lww_all_move_ids())

    def _lww_refresh_auto(self):
        for project in self.sudo():
            if not project._lww_sale_order():
                continue
            config = self.env['lww.recognition.config']._get(project.company_id)
            if not config:
                continue
            date = project._lww_progress_data()[1]
            if not date:
                continue
            Log = self.env['lww.recognition.log'].sudo()
            if project.lww_auto_year:
                if date != project.lww_auto_date:
                    old_date = project.lww_auto_date
                    project.write({'lww_auto_date': date})
                    Log.create({
                        'company_id': project.company_id.id, 'project_id': project.id, 'action': 'date_update',
                        'old_year': project.lww_auto_year, 'new_year': project.lww_auto_year,
                        'note': _('Threshold date %(old)s -> %(new)s', old=old_date, new=date)})
                    if date.year != project.lww_auto_year:
                        Log.create({
                            'company_id': project.company_id.id, 'project_id': project.id, 'action': 'year_warning',
                            'old_year': project.lww_auto_year, 'new_year': date.year,
                            'note': _('Recalculated year %(new)s differs from locked year %(old)s. No DO was changed.',
                                      new=date.year, old=project.lww_auto_year)})
                continue
            project.write({'lww_auto_year': date.year, 'lww_auto_date': date})
            Log.create({
                'company_id': project.company_id.id, 'project_id': project.id, 'action': 'year_auto',
                'new_year': date.year, 'note': _('Billing threshold reached on %s', date)})
            if not (project.lww_manual_override and project.lww_override_year):
                project.env['stock.picking'].sudo().search([
                    ('x_project_id', '=', project.id), ('x_accounting_status', '=', 'awaiting')
                ])._lww_year_appeared(project.lww_rec_year)

    def _lww_tracked_pickings(self):
        return self.env['stock.picking'].sudo().search([
            ('x_project_id', '=', self.id), ('x_accounting_status', '!=', False), ('x_is_return', '=', False)])

    def action_lww_override(self):
        self.ensure_one()
        return self._lww_wizard_action('override')

    def action_lww_process_pending(self):
        self.ensure_one()
        return self._lww_wizard_action('pending')

    def _lww_wizard_action(self, mode):
        wizard = self.env['lww.recognition.wizard'].create({'project_id': self.id, 'mode': mode})
        return {
            'type': 'ir.actions.act_window', 'res_model': 'lww.recognition.wizard',
            'res_id': wizard.id, 'view_mode': 'form', 'target': 'new',
            'name': _('Override Recognition Year') if mode == 'override' else _('Process Pending DOs'),
        }

    def _lww_picking_action(self, status):
        self.ensure_one()
        domain = [('x_project_id', '=', self.id)]
        if status == 'recognized':
            domain.append(('x_accounting_status', 'in', ['recognized', 'returned']))
        else:
            domain.append(('x_accounting_status', '=', status))
        return {'type': 'ir.actions.act_window', 'name': _('Delivery Orders'), 'res_model': 'stock.picking',
                'view_mode': 'list,form', 'domain': domain}

    def action_lww_view_awaiting(self):
        return self._lww_picking_action('awaiting')

    def action_lww_view_pending(self):
        return self._lww_picking_action('pending')

    def action_lww_view_recognized(self):
        return self._lww_picking_action('recognized')

    def action_lww_view_moves(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('Recognition Journals'), 'res_model': 'account.move',
                'view_mode': 'list,form', 'domain': [('id', 'in', self._lww_all_move_ids())]}
