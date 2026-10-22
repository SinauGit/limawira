from collections import defaultdict
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    x_project_id = fields.Many2one('project.project', string='Recognition Project', readonly=True, copy=False,
                                   index='btree_not_null')
    x_is_return = fields.Boolean(string='Is Return', readonly=True, copy=False)
    x_do_date = fields.Date(string='DO Date', readonly=True, copy=False)
    x_accounting_status = fields.Selection([
        ('awaiting', 'Awaiting'),
        ('pending', 'Pending'),
        ('recognized', 'Recognized'),
        ('returned', 'Returned'),
    ], string='Recognition Status', readonly=True, copy=False, index='btree_not_null')
    x_recognized = fields.Boolean(string='Recognized', compute='_compute_x_recognized', store=True)
    x_recognition_year = fields.Integer(string='Recognition Year', readonly=True, copy=False)
    x_recognition_mode = fields.Selection([('auto', 'Automatic'), ('manual', 'Manual')],
                                          string='Recognition Mode', readonly=True, copy=False)
    x_has_return = fields.Boolean(string='Has Return', readonly=True, copy=False)
    x_move_ids = fields.One2many('account.move', 'lww_picking_id', string='Recognition Journals')
    x_reclass_move_id = fields.Many2one('account.move', compute='_compute_x_moves', string='Reclass Journal')
    x_backdated_move_id = fields.Many2one('account.move', compute='_compute_x_moves', string='Backdated Journal')
    x_reclass_reversal_move_id = fields.Many2one('account.move', compute='_compute_x_moves',
                                                 string='Reclass Reversal Journal')
    x_backdated_reversal_move_id = fields.Many2one('account.move', compute='_compute_x_moves',
                                                   string='Backdated Reversal Journal')

    @api.depends('x_accounting_status')
    def _compute_x_recognized(self):
        for picking in self:
            picking.x_recognized = picking.x_accounting_status in ('recognized', 'returned')

    @api.depends('x_move_ids.lww_entry_type', 'x_move_ids.state')
    def _compute_x_moves(self):
        for picking in self:
            moves = picking.x_move_ids.sorted('id', reverse=True)
            for fname, etype in (('x_reclass_move_id', 'reclass'), ('x_backdated_move_id', 'backdated'),
                                 ('x_reclass_reversal_move_id', 'reversal_reclass'),
                                 ('x_backdated_reversal_move_id', 'reversal_backdated')):
                picking[fname] = moves.filtered(lambda m: m.lww_entry_type == etype)[:1]

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _lww_config(self):
        return self.env['lww.recognition.config']._get(self.company_id)

    def _lww_is_delivery(self):
        self.ensure_one()
        return self.picking_type_code == 'outgoing' and not self.return_id

    def _lww_is_return(self):
        self.ensure_one()
        return self.picking_type_code == 'incoming' and bool(self.return_id) \
            and self.return_id.picking_type_code == 'outgoing'

    def _lww_find_project(self):
        self.ensure_one()
        if self.return_id:
            return self.return_id.x_project_id or self.return_id._lww_find_project()
        project = self.project_id.sudo()
        if project and not project._lww_sale_order():
            return self.env['project.project']
        return project

    @api.model
    def _lww_end_of_year(self, year):
        return date(year, 12, 31)

    @api.model
    def _lww_check_dates(self, company, dates):
        locks = [company.fiscalyear_lock_date, company.tax_lock_date, company.hard_lock_date]
        lock = max([d for d in locks if d] or [False]) or None
        if not lock:
            return
        bad = sorted({d for d in dates if d and d <= lock})
        if bad:
            raise UserError(_(
                'Recognition journals cannot be created because these dates are in a locked period: %(dates)s '
                '(locked up to %(lock)s). Unlock the period manually first.',
                dates=', '.join(str(d) for d in bad), lock=lock))

    def _lww_active_moves(self, types):
        self.ensure_one()
        return self.x_move_ids.sudo().filtered(
            lambda m: m.lww_active and m.state == 'posted' and m.lww_entry_type in types)

    def _lww_wip_lines(self, svl_moves, sign):
        """Lines (account, analytic) -> wip debit amount from valuation entries."""
        res = defaultdict(float)
        for svl in svl_moves.sudo().stock_valuation_layer_ids:
            move = svl.account_move_id
            if not move:
                continue
            for line in move.line_ids:
                if sign > 0 and line.debit > 0:
                    res[(line.account_id.id, tuple(sorted((line.analytic_distribution or {}).items())))] += line.debit
                elif sign < 0 and line.credit > 0:
                    res[(line.account_id.id, tuple(sorted((line.analytic_distribution or {}).items())))] -= line.credit
        return res

    def _lww_gross_lines(self):
        self.ensure_one()
        return self._lww_wip_lines(self.move_ids.filtered(lambda m: m.state == 'done'), 1)

    def _lww_return_lines(self):
        self.ensure_one()
        returns = self.return_ids.filtered(lambda p: p.state == 'done')
        res = defaultdict(float)
        for ret in returns:
            for key, amount in ret._lww_wip_lines(ret.move_ids.filtered(lambda m: m.state == 'done'), -1).items():
                res[key] += amount
        return res

    def _lww_net_lines(self):
        self.ensure_one()
        net = defaultdict(float)
        for key, amount in self._lww_gross_lines().items():
            net[key] += amount
        for key, amount in self._lww_return_lines().items():
            net[key] += amount
        return {k: v for k, v in net.items() if not float_is_zero(v, precision_digits=2)}

    def _lww_journal_net(self, types):
        """Net WIP debit per key over active journals of the given entry types."""
        self.ensure_one()
        payable = self._lww_config().payable_account_id
        res = defaultdict(float)
        for move in self._lww_active_moves(types):
            for line in move.line_ids.filtered(lambda l: l.account_id != payable):
                key = (line.account_id.id, tuple(sorted((line.analytic_distribution or {}).items())))
                res[key] += line.debit - line.credit
        return {k: v for k, v in res.items() if not float_is_zero(v, precision_digits=2)}

    def _lww_make_move(self, entry_type, move_date, wip_amounts, year, ref):
        """wip_amounts: {key: signed wip debit amount}."""
        self.ensure_one()
        config = self._lww_config()
        lines = []
        partner = (self.sale_id.partner_id or self.partner_id).commercial_partner_id
        for (account_id, analytic), amount in wip_amounts.items():
            if float_is_zero(amount, precision_digits=2):
                continue
            dist = dict(analytic) or False
            debit = amount if amount > 0 else 0.0
            credit = -amount if amount < 0 else 0.0
            lines.append((0, 0, {'account_id': account_id, 'debit': debit, 'credit': credit,
                                 'analytic_distribution': dist, 'name': ref, 'partner_id': partner.id}))
            lines.append((0, 0, {'account_id': config.payable_account_id.id, 'debit': credit, 'credit': debit,
                                 'analytic_distribution': dist, 'name': ref, 'partner_id': partner.id}))
        if not lines:
            return self.env['account.move']
        move = self.env['account.move'].sudo().with_company(self.company_id).create({
            'move_type': 'entry', 'journal_id': config.journal_id.id, 'date': move_date, 'ref': ref,
            'partner_id': partner.id,
            'company_id': self.company_id.id, 'line_ids': lines,
            'lww_project_id': self.x_project_id.id, 'lww_picking_id': self.id,
            'lww_entry_type': entry_type, 'lww_recognition_year': year,
            'lww_active': entry_type in ('reclass', 'backdated'),
        })
        move._post(soft=False)
        if move.date != move_date:
            raise UserError(_('Recognition journal date was moved by the system to %(d)s because of a lock date. '
                              'Unlock the period manually first.', d=move.date))
        return move

    def _lww_log(self, action, project, old_year=0, new_year=0, moves=None, note=False):
        self.ensure_one()
        self.env['lww.recognition.log'].sudo().create({
            'company_id': self.company_id.id, 'project_id': project.id, 'picking_id': self.id,
            'action': action, 'old_year': old_year, 'new_year': new_year,
            'move_ids': [(6, 0, (moves or self.env['account.move']).ids)], 'note': note})

    # ------------------------------------------------------------------
    # core: bring a delivery in line with a recognition year
    # ------------------------------------------------------------------
    def _lww_plan(self, year):
        """Return what _lww_sync would do for the given year (without doing it)."""
        self.ensure_one()
        has = bool(self._lww_active_moves(('reclass', 'backdated')))
        do_year = self.x_do_date.year
        if year and year < do_year:
            if has:
                old = self._lww_active_moves(('backdated',))[:1].lww_recognition_year
                return 'none' if old == year else 'rebuild'
            return 'create'
        if has:
            return 'reverse'
        return 'status'

    def _lww_required_dates(self, year):
        self.ensure_one()
        plan = self._lww_plan(year)
        dates = []
        today = fields.Date.context_today(self)
        old_years = {m.lww_recognition_year for m in self._lww_active_moves(('backdated', 'reversal_backdated'))}
        if plan == 'create':
            dates += [self.x_do_date, self._lww_end_of_year(year)]
        elif plan == 'rebuild':
            dates += [self._lww_end_of_year(y) for y in old_years] + [self._lww_end_of_year(year)]
        elif plan == 'reverse':
            dates += [self._lww_end_of_year(y) for y in old_years] + [today]
        return dates

    def _lww_sync(self, year, mode, action='recognized'):
        """Apply recognition year to a delivery (done, tracked, not return)."""
        for picking in self:
            project = picking.x_project_id
            plan = picking._lww_plan(year)
            old_year = picking.x_recognition_year
            net = picking._lww_net_lines()
            created = self.env['account.move']
            today = fields.Date.context_today(picking)
            if plan in ('rebuild', 'reverse'):
                for entry_types, rev_type, rev_date_fn in (
                        (('backdated', 'reversal_backdated'), 'reversal_backdated',
                         lambda y: picking._lww_end_of_year(y)),
                        (('reclass', 'reversal_reclass'), 'reversal_reclass', lambda y: today)):
                    if plan == 'rebuild' and rev_type == 'reversal_reclass':
                        continue
                    actives = picking._lww_active_moves(entry_types)
                    if not actives:
                        continue
                    ref_year = actives[:1].lww_recognition_year
                    amounts = {k: -v for k, v in picking._lww_journal_net(entry_types).items()}
                    move = picking._lww_make_move(rev_type, rev_date_fn(ref_year), amounts, ref_year,
                                                  _('Reversal %s', picking.name))
                    actives.write({'lww_active': False})
                    actives.flush_recordset(['lww_active'])
                    created |= move
            if plan in ('create', 'rebuild') and net:
                if plan == 'create':
                    created |= picking._lww_make_move(
                        'reclass', picking.x_do_date, {k: -v for k, v in net.items()}, year,
                        _('Reclass %s', picking.name))
                created |= picking._lww_make_move(
                    'backdated', picking._lww_end_of_year(year), dict(net), year,
                    _('Backdate %s', picking.name))
            if not year:
                status = 'awaiting'
            elif not net and (picking.x_has_return or picking._lww_return_lines()):
                status = 'returned'
            else:
                status = 'recognized'
            picking.sudo().write({
                'x_accounting_status': status,
                'x_recognition_year': year or 0,
                'x_recognition_mode': mode if year else False,
            })
            if created:
                picking._lww_log('journal' if plan in ('create', 'rebuild') else 'reversal', project,
                                 old_year, year or 0, created)
                picking.message_post(body=_('Recognition journals: %s', ', '.join(created.mapped('name'))))
            elif old_year != (year or 0) or action:
                picking._lww_log(action if year else 'recognized', project, old_year, year or 0,
                                 note=_('Status: %s', status))

    def _lww_year_appeared(self, year):
        """Year appeared via the billing threshold for awaiting deliveries."""
        for picking in self:
            project = picking.x_project_id
            if year >= picking.x_do_date.year:
                picking._lww_sync(year, 'auto', action='recognized')
            else:
                picking.sudo().write({'x_accounting_status': 'pending', 'x_recognition_year': year,
                                      'x_recognition_mode': 'auto'})
                picking._lww_log('pending', project, 0, year, note=_('Waiting for processing'))

    # ------------------------------------------------------------------
    # validation hooks
    # ------------------------------------------------------------------
    def _lww_precheck(self):
        today = fields.Date.context_today(self)
        for picking in self:
            config = picking._lww_config()
            if not config or today < config.go_live_date:
                continue
            if picking._lww_is_delivery():
                project = picking._lww_find_project()
                year = project.lww_rec_year if project else 0
                if year and year < today.year:
                    picking._lww_require_config(config)
                    self._lww_check_dates(picking.company_id, [today, picking._lww_end_of_year(year)])
            elif picking._lww_is_return():
                origin = picking.return_id
                if origin._lww_active_moves(('reclass', 'backdated')):
                    picking._lww_require_config(config)
                    years = {m.lww_recognition_year for m in origin._lww_active_moves(('backdated',))}
                    self._lww_check_dates(picking.company_id,
                                          [today] + [picking._lww_end_of_year(y) for y in years])

    def _lww_require_config(self, config):
        if not config.journal_id or not config.payable_account_id:
            raise UserError(_('Project Recognition settings are incomplete (journal / Hutang Biaya Proyek account).'))

    def _action_done(self):
        self._lww_precheck()
        res = super()._action_done()
        for picking in self.filtered(lambda p: p.state == 'done'):
            picking._lww_after_done()
        return res

    def _lww_after_done(self):
        self.ensure_one()
        config = self._lww_config()
        today = fields.Date.context_today(self)
        if not config or today < config.go_live_date:
            return
        if self._lww_is_delivery() and not self.x_accounting_status:
            project = self._lww_find_project()
            if not project:
                return
            self.sudo().write({'x_project_id': project.id, 'x_do_date': today})
            year = project.lww_rec_year
            if not year:
                self.sudo().write({'x_accounting_status': 'awaiting'})
                self._lww_log('recognized', project, note=_('Awaiting recognition year'))
            else:
                self._lww_sync(year, project.lww_rec_mode, action='recognized')
        elif self._lww_is_return() and not self.x_is_return:
            origin = self.return_id
            if not origin.x_accounting_status:
                return
            self.sudo().write({'x_is_return': True, 'x_project_id': origin.x_project_id.id, 'x_do_date': today})
            origin.sudo().write({'x_has_return': True})
            net = origin._lww_net_lines()
            created = self.env['account.move']
            if origin._lww_active_moves(('reclass', 'backdated')):
                ret = {k: -v for k, v in self._lww_wip_lines(
                    self.move_ids.filtered(lambda m: m.state == 'done'), -1).items()}
                year = origin.x_recognition_year
                origin_self = origin
                created |= origin_self._lww_make_move('reversal_reclass', today, ret, year,
                                                      _('Return reclass reversal %s', self.name))
                created |= origin_self._lww_make_move(
                    'reversal_backdated', origin._lww_end_of_year(year), {k: -v for k, v in ret.items()}, year,
                    _('Return backdate reversal %s', self.name))
            if not net:
                origin.sudo().write({'x_accounting_status': 'returned'})
            origin._lww_log('return', origin.x_project_id, origin.x_recognition_year, origin.x_recognition_year,
                            created, note=_('Return %s', self.name))
            if created:
                origin.message_post(body=_('Return %(ret)s journals: %(moves)s', ret=self.name,
                                           moves=', '.join(created.mapped('name'))))
