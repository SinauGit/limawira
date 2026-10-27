from datetime import date

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRecognition(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(su=True)
        env = cls.env
        cls.company = env.company
        cls.today = fields.Date.context_today(env.user)
        cls.Y = cls.today.year
        Account = env['account.account']

        def acc(code, atype, **kw):
            return Account.create({'code': code, 'name': code, 'account_type': atype, **kw})
        cls.acc_wip = acc('LW1061', 'asset_current')
        cls.acc_stock = acc('LW1101', 'asset_current')
        cls.acc_payable = acc('LW2201', 'liability_current')
        cls.acc_income = acc('LW4001', 'income')
        cls.acc_recv = acc('LW1201', 'asset_receivable', reconcile=True)
        cls.acc_pay = acc('LW2101', 'liability_payable', reconcile=True)
        cls.journal_rec = env['account.journal'].create({'name': 'Recognition', 'code': 'LWR', 'type': 'general'})
        cls.journal_stock = env['account.journal'].create({'name': 'Stock LW', 'code': 'LWS', 'type': 'general'})
        cls.journal_sale = env['account.journal'].create({'name': 'Sales LW', 'code': 'LWI', 'type': 'sale'})
        env['lww.recognition.config'].create({
            'company_id': cls.company.id, 'journal_id': cls.journal_rec.id,
            'payable_account_id': cls.acc_payable.id, 'threshold': 90.0,
            'go_live_date': date(cls.Y - 5, 1, 1)})
        cls.partner = env['res.partner'].create({
            'name': 'Cust LW', 'property_account_receivable_id': cls.acc_recv.id,
            'property_account_payable_id': cls.acc_pay.id})
        cls.categ = env['product.category'].create({
            'name': 'LW', 'property_cost_method': 'average', 'property_valuation': 'real_time',
            'property_stock_valuation_account_id': cls.acc_stock.id,
            'property_stock_account_input_categ_id': cls.acc_wip.id,
            'property_stock_account_output_categ_id': cls.acc_wip.id,
            'property_account_expense_categ_id': cls.acc_wip.id,
            'property_account_income_categ_id': cls.acc_income.id,
            'property_stock_journal': cls.journal_stock.id})
        cls.product = env['product.product'].create({
            'name': 'LW Product', 'is_storable': True, 'type': 'consu', 'categ_id': cls.categ.id,
            'standard_price': 100.0, 'list_price': 1000.0})
        wh = env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)
        quant = env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': cls.product.id, 'location_id': wh.lot_stock_id.id, 'inventory_quantity': 1000})
        quant.action_apply_inventory()

    def _project(self, name='P1', qty=10, price=1000.0):
        analytic_plan = self.env['account.analytic.plan'].search([], limit=1) or \
            self.env['account.analytic.plan'].create({'name': 'Project'})
        analytic = self.env['account.analytic.account'].create({'name': name, 'plan_id': analytic_plan.id})
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {'product_id': self.product.id, 'product_uom_qty': qty, 'price_unit': price,
                                   'tax_id': [(5, 0, 0)],
                                   'analytic_distribution': {str(analytic.id): 100}})]})
        project = self.env['project.project'].create({
            'name': name, 'account_id': analytic.id, 'partner_id': self.partner.id,
            'sale_line_id': order.order_line.id})
        if order.state != 'sale':
            order.action_confirm()
        return project, order

    def _invoice(self, project, amount, inv_date, move_type='out_invoice'):
        move = self.env['account.move'].create({
            'move_type': move_type, 'partner_id': self.partner.id, 'invoice_date': inv_date,
            'journal_id': self.journal_sale.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'bill', 'quantity': 1, 'price_unit': amount, 'account_id': self.acc_income.id,
                'tax_ids': [(5, 0, 0)], 'analytic_distribution': {str(project.account_id.id): 100}})]})
        move.action_post()
        return move

    def _validate(self, order, qty=None):
        picking = order.picking_ids.filtered(lambda p: p.state != 'done' and p.picking_type_code == 'outgoing')[:1]
        picking.project_id = self.env['project.project'].search([
            '|', ('sale_line_id', 'in', order.order_line.ids), ('sale_order_id', '=', order.id)], limit=1) \
            or order.project_id
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = qty if qty is not None else move.product_uom_qty
            move.picked = True
        picking.with_context(skip_backorder=True, skip_sms=True).button_validate()
        return picking

    def _return(self, picking, qty):
        wiz = self.env['stock.return.picking'].with_context(
            active_id=picking.id, active_model='stock.picking').create({})
        wiz.product_return_moves.quantity = qty
        res = wiz.action_create_returns()
        ret = self.env['stock.picking'].browse(res['res_id'])
        for move in ret.move_ids:
            move.quantity = qty
            move.picked = True
        ret.with_context(skip_backorder=True, skip_sms=True).button_validate()
        return ret

    def _balance(self, project, account):
        lines = self.env['account.move.line'].search([
            ('account_id', '=', account.id), ('parent_state', '=', 'posted'),
            ('analytic_distribution', 'in', project.account_id.ids)])
        return round(sum(lines.mapped('balance')), 2)

    def _entries(self, picking, etype=None, active=None):
        moves = self.env['account.move'].search([('lww_picking_id', '=', picking.id)])
        if etype:
            moves = moves.filtered(lambda m: m.lww_entry_type == etype)
        if active is not None:
            moves = moves.filtered(lambda m: m.lww_active == active)
        return moves

    def _reach(self, project, year):
        self._invoice(project, 6000, date(year, 3, 10))
        self._invoice(project, 3000, date(year, 5, 20))

    def _override(self, project, year):
        wiz = self.env['lww.recognition.wizard'].create({
            'project_id': project.id, 'mode': 'override', 'manual': bool(year), 'new_year': year or 0})
        wiz.confirm = True
        wiz.action_apply()

    # ------------------------------------------------------------------
    def test_01_billing_year_reclass_backdate(self):
        project, order = self._project()
        self._invoice(project, 6000, date(self.Y - 1, 3, 10))
        self.assertEqual(project.lww_rec_year, 0)
        self._invoice(project, 3000, date(self.Y - 1, 12, 20))
        self.assertEqual(project.lww_rec_year, self.Y - 1)
        self.assertEqual(project.lww_rec_mode, 'auto')
        picking = self._validate(order)
        self.assertEqual(picking.state, 'done')
        self.assertEqual(picking.x_accounting_status, 'recognized')
        reclass = self._entries(picking, 'reclass')
        backdated = self._entries(picking, 'backdated')
        self.assertEqual(reclass.date, self.today)
        self.assertEqual(backdated.date, date(self.Y - 1, 12, 31))
        self.assertEqual(sum(reclass.line_ids.filtered(lambda l: l.account_id == self.acc_payable).mapped('debit')), 1000.0)
        self.assertEqual(reclass.partner_id, self.partner)
        self.assertEqual(set(reclass.line_ids.partner_id.ids), {self.partner.id})
        self.assertEqual(self._balance(project, self.acc_wip), 1000.0)
        self.assertEqual(self._balance(project, self.acc_payable), 0.0)
        self.assertEqual(picking.x_reclass_move_id, reclass)
        self.assertEqual(picking.x_backdated_move_id, backdated)

    def test_02_same_year_no_journal(self):
        project, order = self._project()
        self._reach(project, self.Y)
        picking = self._validate(order)
        self.assertEqual(picking.x_accounting_status, 'recognized')
        self.assertFalse(self._entries(picking))

    def test_03_awaiting_then_year_ge_do_year(self):
        project, order = self._project()
        picking = self._validate(order)
        self.assertEqual(picking.x_accounting_status, 'awaiting')
        self.assertFalse(self._entries(picking))
        self._reach(project, self.Y)
        self.assertEqual(picking.x_accounting_status, 'recognized')
        self.assertFalse(self._entries(picking))

    def test_04_awaiting_then_prior_year_pending_then_wizard(self):
        project, order = self._project()
        picking = self._validate(order)
        self._reach(project, self.Y - 1)
        self.assertEqual(picking.x_accounting_status, 'pending')
        self.assertFalse(self._entries(picking))
        self.assertEqual(project.lww_pending_count, 1)
        wiz = self.env['lww.recognition.wizard'].create({'project_id': project.id, 'mode': 'pending'})
        self.assertEqual(wiz.impacted_count, 1)
        with self.assertRaises(UserError):
            wiz.action_apply()
        wiz.confirm = True
        wiz.action_apply()
        self.assertEqual(picking.x_accounting_status, 'recognized')
        self.assertEqual(len(self._entries(picking, active=True)), 2)
        self.assertEqual(self._balance(project, self.acc_wip), 1000.0)

    def test_05_partial_and_full_return(self):
        project, order = self._project()
        self._reach(project, self.Y - 1)
        picking = self._validate(order)
        ret = self._return(picking, 4)
        self.assertTrue(ret.x_is_return)
        rr = self._entries(picking, 'reversal_reclass')
        rb = self._entries(picking, 'reversal_backdated')
        self.assertEqual(rr.date, self.today)
        self.assertEqual(rb.date, date(self.Y - 1, 12, 31))
        self.assertEqual(sum(rr.line_ids.filtered(lambda l: l.account_id == self.acc_payable).mapped('credit')), 400.0)
        self.assertEqual(picking.x_accounting_status, 'recognized')
        self.assertTrue(picking.x_has_return)
        self.assertEqual(self._balance(project, self.acc_wip), 600.0)
        self._return(picking, 6)
        self.assertEqual(picking.x_accounting_status, 'returned')
        self.assertEqual(self._balance(project, self.acc_wip), 0.0)
        self.assertEqual(self._balance(project, self.acc_payable), 0.0)

    def test_06_override_flow(self):
        project, order = self._project()
        picking = self._validate(order)
        self._override(project, self.Y - 1)
        self.assertEqual(project.lww_rec_mode, 'manual')
        self.assertEqual(picking.x_accounting_status, 'recognized')
        self.assertEqual(self._entries(picking, 'backdated').date, date(self.Y - 1, 12, 31))
        self._override(project, self.Y - 3)
        old = self._entries(picking, 'backdated').filtered(lambda m: m.date.year == self.Y - 1)
        self.assertFalse(old.lww_active)
        self.assertEqual(len(self._entries(picking, 'reversal_backdated')), 1)
        self.assertEqual(self._entries(picking, 'backdated', active=True).date, date(self.Y - 3, 12, 31))
        self.assertEqual(self._entries(picking, 'reclass', active=True).date, self.today)
        self.assertEqual(self._balance(project, self.acc_wip), 1000.0)
        self._override(project, self.Y)
        self.assertFalse(self._entries(picking, active=True))
        self.assertEqual(picking.x_accounting_status, 'recognized')
        self.assertEqual(self._balance(project, self.acc_wip), 1000.0)
        self.assertEqual(self._balance(project, self.acc_payable), 0.0)
        self._override(project, False)
        self.assertEqual(picking.x_accounting_status, 'awaiting')
        self.assertEqual(project.lww_rec_year, 0)

    def test_07_override_blocked_after_threshold(self):
        project, order = self._project()
        self._reach(project, self.Y - 1)
        with self.assertRaises(UserError):
            self._override(project, self.Y - 2)

    def test_08_override_before_threshold_keeps_override(self):
        project, order = self._project()
        picking = self._validate(order)
        self._override(project, self.Y - 2)
        self._reach(project, self.Y - 1)
        self.assertEqual(project.lww_rec_year, self.Y - 2)
        self.assertEqual(project.lww_auto_year, self.Y - 1)
        self.assertEqual(self._entries(picking, 'backdated', active=True).date, date(self.Y - 2, 12, 31))

    def test_09_lock_blocks_validation(self):
        project, order = self._project()
        self._reach(project, self.Y - 1)
        self.company.fiscalyear_lock_date = date(self.Y - 1, 12, 31)
        picking = order.picking_ids[:1]
        picking.project_id = project
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        with self.assertRaises(UserError):
            picking.with_context(skip_backorder=True).button_validate()
        self.assertNotEqual(picking.state, 'done')
        self.assertFalse(self._entries(picking))

    def test_10_lock_blocks_wizard(self):
        project, order = self._project()
        picking = self._validate(order)
        self.company.fiscalyear_lock_date = date(self.Y - 2, 12, 31)
        with self.assertRaises(UserError):
            self._override(project, self.Y - 2)
        self.assertEqual(picking.x_accounting_status, 'awaiting')
        self.assertFalse(project.lww_manual_override)

    def test_11_before_go_live_not_tracked(self):
        self.env['lww.recognition.config'].search([]).go_live_date = date(self.Y + 1, 1, 1)
        project, order = self._project()
        picking = self._validate(order)
        self.assertFalse(picking.x_accounting_status)

    def test_12_return_before_journals_net(self):
        project, order = self._project()
        picking = self._validate(order)
        self._return(picking, 4)
        self.assertEqual(picking.x_accounting_status, 'awaiting')
        self._override(project, self.Y - 1)
        reclass = self._entries(picking, 'reclass')
        self.assertEqual(sum(reclass.line_ids.filtered(lambda l: l.account_id == self.acc_payable).mapped('debit')), 600.0)
        self.assertEqual(self._balance(project, self.acc_wip), 600.0)

    def test_13_progress_ignores_credit_notes_and_no_so(self):
        project, order = self._project()
        self._invoice(project, 6000, date(self.Y - 1, 3, 10))
        self._invoice(project, 5000, date(self.Y - 1, 4, 10), move_type='out_refund')
        self.assertEqual(project.lww_rec_year, 0)
        self.assertAlmostEqual(project.lww_progress, 60.0)
        orphan = self.env['project.project'].create({'name': 'NoSO'})
        self.assertEqual(orphan.lww_progress, 0.0)
        self.assertFalse(orphan.lww_rec_year)

    def test_14_actions_and_audit(self):
        project, order = self._project()
        self._reach(project, self.Y - 1)
        picking = self._validate(order)
        self.assertEqual(project.lww_recognized_count, 1)
        self.assertEqual(project.lww_move_count, 3)
        valuation = picking.move_ids.stock_valuation_layer_ids.account_move_id
        self.assertTrue(valuation)
        self.assertTrue(valuation <= self.env['account.move'].browse(project.action_lww_view_moves()['domain'][0][2]))
        for action in (project.action_lww_view_recognized, project.action_lww_view_moves,
                       project.action_lww_view_awaiting, project.action_lww_view_pending):
            self.assertTrue(action()['res_model'])
        logs = self.env['lww.recognition.log'].search([('project_id', '=', project.id)])
        self.assertTrue(logs.filtered(lambda l: l.action == 'year_auto'))
        self.assertTrue(logs.filtered(lambda l: l.action == 'journal'))
        with self.assertRaises(Exception):
            self.env['account.move'].create({
                'move_type': 'entry', 'journal_id': self.journal_rec.id, 'lww_picking_id': picking.id,
                'lww_entry_type': 'backdated', 'lww_active': True})

    def _project_via_so(self, name='PSO'):
        plan = self.env['account.analytic.plan'].search([], limit=1) or \
            self.env['account.analytic.plan'].create({'name': 'Project'})
        analytic = self.env['account.analytic.account'].create({'name': name, 'plan_id': plan.id})
        project = self.env['project.project'].create({'name': name, 'account_id': analytic.id,
                                                      'partner_id': self.partner.id})
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {'product_id': self.product.id, 'product_uom_qty': 10, 'price_unit': 1000.0,
                                   'tax_id': [(5, 0, 0)], 'analytic_distribution': {str(analytic.id): 100}})]})
        order.project_id = project
        if order.state != 'sale':
            order.action_confirm()
        return project, order

    def test_15_project_linked_by_so_project_id(self):
        project, order = self._project_via_so()
        self.assertFalse(project.sale_line_id)
        self.assertEqual(project.lww_sale_order_id, order)
        self.assertIn(project, self.env['project.project'].search([('lww_sale_order_id', '!=', False)]))
        self._invoice(project, 6000, date(self.Y - 1, 3, 10))
        self._invoice(project, 3000, date(self.Y - 1, 5, 20))
        self.assertEqual(project.lww_rec_year, self.Y - 1)
        picking = self._validate(order)
        self.assertEqual(picking.x_project_id, project)
        self.assertEqual(picking.x_accounting_status, 'recognized')
        self.assertEqual(len(self._entries(picking, active=True)), 2)

    def test_16_reset_to_draft_updates_threshold_date_keeps_year(self):
        project, order = self._project()
        self._invoice(project, 6000, date(self.Y - 1, 3, 10))
        last = self._invoice(project, 3000, date(self.Y - 1, 5, 20))
        self.assertEqual(project.lww_auto_date, date(self.Y - 1, 5, 20))
        last.button_draft()
        self.assertEqual(project.lww_auto_year, self.Y - 1)
        self.assertEqual(project.lww_auto_date, date(self.Y - 1, 5, 20))
        self.assertAlmostEqual(project.lww_progress, 60.0)
        last.invoice_date = date(self.Y - 1, 11, 20)
        last.action_post()
        self.assertEqual(project.lww_auto_year, self.Y - 1)
        self.assertEqual(project.lww_auto_date, date(self.Y - 1, 11, 20))
        logs = self.env['lww.recognition.log'].search([('project_id', '=', project.id)])
        self.assertTrue(logs.filtered(lambda l: l.action == 'date_update'))
        self.assertFalse(logs.filtered(lambda l: l.action == 'year_warning'))
        last.button_draft()
        last.name = '/'
        last.invoice_date = date(self.Y, 1, 15)
        last.action_post()
        self.assertEqual(project.lww_auto_year, self.Y - 1)
        self.assertEqual(project.lww_rec_year, self.Y - 1)
        warn = self.env['lww.recognition.log'].search([('project_id', '=', project.id), ('action', '=', 'year_warning')])
        self.assertEqual(len(warn), 1)
        self.assertEqual(warn.new_year, self.Y)

    def test_17_dashboard(self):
        project, order = self._project()
        self._validate(order)
        dash = self.env['lww.recognition.dashboard'].create({})
        self.assertEqual(dash.awaiting_count, 1)
        self.assertEqual(dash.no_year_count, 1)
        self.assertEqual(dash.pending_count, 0)
        self._invoice(project, 9000, date(self.Y, 3, 10))
        dash = self.env['lww.recognition.dashboard'].create({})
        self.assertEqual(dash.awaiting_count, 0)
        self.assertEqual(dash.recognized_count, 1)
        self.assertEqual(dash.no_year_count, 0)
        p2, o2 = self._project('P2')
        self._invoice(p2, 8000, date(self.Y, 3, 10))
        dash = self.env['lww.recognition.dashboard'].create({})
        self.assertEqual(dash.near_count, 1)
        for name in ('awaiting', 'pending', 'recognized', 'no_year', 'near', 'override', 'journals'):
            self.assertTrue(getattr(dash, 'action_' + name)()['res_model'])

    def test_18_dashboard_menu_visible(self):
        user = self.env['res.users'].create({
            'name': 'Acc LW', 'login': 'acc_lw', 'company_id': self.company.id, 'company_ids': [(6, 0, self.company.ids)],
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id, self.env.ref('account.group_account_user').id])]})
        menu = self.env.ref('lww_project_recognition.menu_lww_recognition_dashboard')
        self.assertIn(menu.id, self.env['ir.ui.menu'].with_user(user)._visible_menu_ids())
        action = self.env.ref('lww_project_recognition.lww_dashboard_action')
        self.assertEqual(action.res_id, self.env.ref('lww_project_recognition.lww_dashboard_record').id)
        self.assertEqual(self.env['lww.recognition.dashboard'].with_user(user).browse(action.res_id).awaiting_count, 0)

    def test_19_dashboard_title(self):
        dash = self.env['lww.recognition.dashboard'].create({})
        self.assertEqual(dash.display_name, 'Project DO Recognition Management Dashboard')
