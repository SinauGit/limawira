from collections import defaultdict

from odoo import api, fields, models, _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    lww_manual_override = fields.Boolean(
        string='Manual Override', copy=False, readonly=True, tracking=True)
    lww_override_year = fields.Integer(
        string='Override Year', copy=False, readonly=True, tracking=True)
    lww_billing_date = fields.Date(
        string='Billing Threshold Date', copy=False, readonly=True,
        help='Date on which cumulative progress billing reached the threshold (default 90%).')
    lww_rec_year = fields.Integer(
        string='Recognition Year', compute='_compute_lww_rec_year', store=True)
    lww_rec_mode = fields.Selection(
        [('automatic', 'Automatic (90% Rule)'), ('manual', 'Manual Override')],
        string='Recognition Mode', compute='_compute_lww_rec_mode')
    lww_rec_status = fields.Selection(
        [('not_ready', 'Not Ready'),
         ('pending', 'Pending Recognition'),
         ('recognized', 'Recognized')],
        string='Recognition Status', compute='_compute_lww_rec_status', store=True)
    lww_has_return = fields.Boolean(
        string='Has Return Delivery', compute='_compute_lww_has_return', store=True)
    lww_picking_ids = fields.One2many('stock.picking', 'x_project_id', string='Transfers')

    lww_do_count = fields.Integer(compute='_compute_lww_counts', string='Delivery Orders')
    lww_reclass_count = fields.Integer(compute='_compute_lww_counts', string='Reclassification Journals')
    lww_backdated_count = fields.Integer(compute='_compute_lww_counts', string='Backdated Journals')
    lww_return_count = fields.Integer(compute='_compute_lww_counts', string='Return Deliveries')
    lww_reversal_count = fields.Integer(compute='_compute_lww_counts', string='Reversal Journals')

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('lww_manual_override', 'lww_override_year', 'lww_billing_date')
    def _compute_lww_rec_year(self):
        for project in self:
            if project.lww_manual_override:
                project.lww_rec_year = project.lww_override_year or 0
            elif project.lww_billing_date:
                project.lww_rec_year = project.lww_billing_date.year
            else:
                project.lww_rec_year = 0

    def _compute_lww_rec_mode(self):
        for project in self:
            project.lww_rec_mode = 'manual' if project.lww_manual_override else 'automatic'

    @api.depends('lww_rec_year', 'lww_picking_ids.x_accounting_status', 'lww_picking_ids.state')
    def _compute_lww_rec_status(self):
        for project in self:
            if not project.lww_rec_year:
                project.lww_rec_status = 'not_ready'
                continue
            delivered = project.lww_picking_ids.filtered(
                lambda p: not p.x_is_return and p.picking_type_code == 'outgoing' and p.state == 'done')
            if delivered and all(p.x_accounting_status == 'recognized' for p in delivered):
                project.lww_rec_status = 'recognized'
            else:
                project.lww_rec_status = 'pending'

    @api.depends('lww_picking_ids.x_is_return', 'lww_picking_ids.state')
    def _compute_lww_has_return(self):
        for project in self:
            project.lww_has_return = any(
                p.x_is_return and p.state == 'done' for p in project.lww_picking_ids)

    def _compute_lww_counts(self):
        counts = defaultdict(lambda: defaultdict(int))
        if self.ids:
            Picking = self.env['stock.picking'].sudo()
            Move = self.env['account.move'].sudo()
            base = [('x_project_id', 'in', self.ids), ('state', '!=', 'cancel')]
            for project, count in Picking._read_group(
                    base + [('x_is_return', '=', False), ('picking_type_code', '=', 'outgoing')],
                    ['x_project_id'], ['__count']):
                counts[project.id]['do'] = count
            for project, count in Picking._read_group(
                    base + [('x_is_return', '=', True)], ['x_project_id'], ['__count']):
                counts[project.id]['return'] = count
            for project, entry_type, count in Move._read_group(
                    [('lww_project_id', 'in', self.ids), ('lww_entry_type', '!=', False)],
                    ['lww_project_id', 'lww_entry_type'], ['__count']):
                counts[project.id][entry_type] = count
        for project in self:
            data = counts[project.id]
            project.lww_do_count = data['do']
            project.lww_return_count = data['return']
            project.lww_reclass_count = data['reclass']
            project.lww_backdated_count = data['backdated']
            project.lww_reversal_count = data['reversal_reclass'] + data['reversal_backdated']

    # ------------------------------------------------------------------
    # Order / project linkage
    # ------------------------------------------------------------------
    @api.model
    def _lww_projects_from_orders(self, orders):
        orders = orders.sudo()
        projects = orders.project_id
        projects |= self.sudo().search([
            '|',
            ('sale_line_id.order_id', 'in', orders.ids),
            ('reinvoiced_sale_order_id', 'in', orders.ids),
        ])
        return projects.sorted('id')

    def _lww_orders(self):
        self.ensure_one()
        project = self.sudo()
        orders = project.sale_order_id | project.reinvoiced_sale_order_id
        orders |= self.env['sale.order'].sudo().search([('project_id', '=', project.id)])
        return orders.filtered(lambda so: so.state == 'sale')

    def _lww_relink_pickings(self):
        """Recompute the project reference of the transfers of the project orders."""
        Picking = self.env['stock.picking'].sudo()
        for project in self:
            orders = (project.sudo().sale_order_id | project.sudo().reinvoiced_sale_order_id
                      | self.env['sale.order'].sudo().search([('project_id', '=', project.id)]))
            pickings = Picking.search([('sale_id', 'in', orders.ids)])
            if pickings:
                self.env.add_to_compute(Picking._fields['x_project_id'], pickings)

    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)
        projects._lww_relink_pickings()
        projects._lww_refresh_billing()
        return projects

    def write(self, vals):
        res = super().write(vals)
        if 'sale_line_id' in vals or 'reinvoiced_sale_order_id' in vals:
            self._lww_relink_pickings()
            self._lww_refresh_billing()
        return res

    # ------------------------------------------------------------------
    # Billing milestone (FR-01)
    # ------------------------------------------------------------------
    def _lww_refresh_billing(self):
        for project in self.sudo():
            billing_date = project._lww_compute_billing_date()
            if project.lww_billing_date != billing_date:
                project.lww_billing_date = billing_date

    def _lww_compute_billing_date(self):
        """Date on which cumulative posted billing (invoices minus credit notes)
        of the project sale order(s) reached the company threshold of the order
        total (untaxed). Returns False if the threshold is not reached (anymore)."""
        self.ensure_one()
        orders = self._lww_orders()
        if not orders:
            return False
        total = sum(orders.mapped('amount_untaxed'))
        if total <= 0:
            return False
        currency = orders[:1].currency_id
        target = total * (self.company_id.lww_billing_threshold or 90.0) / 100.0

        lines = self.env['account.move.line'].sudo().search([
            ('sale_line_ids.order_id', 'in', orders.ids),
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type', 'in', ('out_invoice', 'out_refund')),
            ('display_type', '=', 'product'),
        ])
        per_move = defaultdict(float)
        for line in lines:
            sign = 1.0 if line.move_id.move_type == 'out_invoice' else -1.0
            per_move[line.move_id] += sign * line.price_subtotal
        entries = sorted(
            ((move.invoice_date or move.date, move.id, amount) for move, amount in per_move.items()))

        cumulative = 0.0
        reached = False
        for entry_date, _move_id, amount in entries:
            cumulative += amount
            if currency.compare_amounts(cumulative, target) >= 0:
                reached = reached or entry_date
            else:
                reached = False
        return reached

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_open_recognition_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generate Recognition'),
            'res_model': 'lww.recognition.override.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_project_id': self.id},
        }

    def _lww_picking_action(self, is_return):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('stock.action_picking_tree_all')
        domain = [('x_project_id', '=', self.id), ('x_is_return', '=', is_return)]
        if not is_return:
            domain.append(('picking_type_code', '=', 'outgoing'))
        action.update({
            'name': _('Return Deliveries') if is_return else _('Delivery Orders'),
            'domain': domain,
            'context': {},
        })
        return action

    def action_view_lww_pickings(self):
        return self._lww_picking_action(False)

    def action_view_lww_returns(self):
        return self._lww_picking_action(True)

    def _lww_journal_action(self, entry_types, name):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'account.move',
            'views': [
                (self.env.ref('lww_project_recognition.view_move_recognition_list').id, 'list'),
                (False, 'form'),
            ],
            'domain': [('lww_project_id', '=', self.id), ('lww_entry_type', 'in', entry_types)],
            'context': {'create': False},
        }

    def action_view_lww_reclass(self):
        return self._lww_journal_action(['reclass'], _('Reclassification Journals'))

    def action_view_lww_backdated(self):
        return self._lww_journal_action(['backdated'], _('Backdated Journals'))

    def action_view_lww_reversals(self):
        return self._lww_journal_action(
            ['reversal_reclass', 'reversal_backdated'], _('Reversal Journals'))

    def action_view_lww_all_journals(self):
        return self._lww_journal_action(
            ['reclass', 'backdated', 'reversal_reclass', 'reversal_backdated'],
            _('Recognition Journals'))
