from datetime import date

from odoo import fields, Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestProjectRecognition(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.anglo_saxon_accounting = True
        Account = cls.env['account.account']

        def acc(code, name, account_type, reconcile=False):
            return Account.create({
                'code': code, 'name': name, 'account_type': account_type, 'reconcile': reconcile})

        cls.acc_stock = acc('LW1100', 'Stock Valuation', 'asset_current')
        cls.acc_input = acc('LW1101', 'Stock Interim (Received)', 'asset_current', True)
        cls.acc_wip = acc('LW1102', 'WIP Project', 'asset_current', True)
        cls.acc_income = acc('LW4100', 'Project Revenue', 'income')
        cls.acc_cogs = acc('LW5100', 'Project COGS', 'expense')
        cls.acc_hutang = acc('LW2100', 'Hutang Biaya Proyek', 'liability_current')
        cls.acc_receivable = acc('LW1200', 'Receivable', 'asset_receivable', True)

        Journal = cls.env['account.journal']
        cls.stock_journal = Journal.create({'name': 'Stock Journal', 'type': 'general', 'code': 'LWSTJ'})
        cls.rec_journal = Journal.create({'name': 'Recognition', 'type': 'general', 'code': 'LWREC'})
        cls.sale_journal = Journal.search(
            [('type', '=', 'sale'), ('company_id', '=', cls.company.id)], limit=1) or Journal.create(
            {'name': 'Sales', 'type': 'sale', 'code': 'LWSAL', 'default_account_id': cls.acc_income.id})
        cls.company.write({
            'lww_rec_journal_id': cls.rec_journal.id,
            'lww_rec_payable_account_id': cls.acc_hutang.id,
        })

        cls.categ = cls.env['product.category'].create({
            'name': 'Project Material',
            'property_valuation': 'real_time',
            'property_cost_method': 'fifo',
            'property_stock_valuation_account_id': cls.acc_stock.id,
            'property_stock_account_input_categ_id': cls.acc_input.id,
            'property_stock_account_output_categ_id': cls.acc_wip.id,
            'property_stock_journal': cls.stock_journal.id,
            'property_account_income_categ_id': cls.acc_income.id,
            'property_account_expense_categ_id': cls.acc_cogs.id,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Material A', 'type': 'consu', 'is_storable': True,
            'categ_id': cls.categ.id, 'standard_price': 100.0, 'list_price': 150.0,
            'invoice_policy': 'order',
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'PT ABC',
            'property_account_receivable_id': cls.acc_receivable.id,
        })
        cls.year = fields.Date.today().year
        cls.prev = cls.year - 1

        receipt = cls.env['stock.picking'].create({
            'picking_type_id': cls.env.ref('stock.picking_type_in').id
            if cls.env.ref('stock.picking_type_in', raise_if_not_found=False)
            else cls.env['stock.picking.type'].search([('code', '=', 'incoming')], limit=1).id,
            'location_id': cls.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': cls.env['stock.picking.type'].search(
                [('code', '=', 'incoming')], limit=1).default_location_dest_id.id,
            'move_ids': [Command.create({
                'name': 'receipt', 'product_id': cls.product.id, 'product_uom_qty': 100,
                'product_uom': cls.product.uom_id.id,
                'location_id': cls.env.ref('stock.stock_location_suppliers').id,
                'location_dest_id': cls.env['stock.picking.type'].search(
                    [('code', '=', 'incoming')], limit=1).default_location_dest_id.id,
            })],
        })
        receipt.action_confirm()
        receipt.move_ids.quantity = 100
        receipt.move_ids.picked = True
        receipt.button_validate()

    # ------------------------------------------------------------------
    def _make_so_project(self, qty=10):
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': self.product.id, 'product_uom_qty': qty, 'price_unit': 150.0})],
        })
        so.action_confirm()
        project = self.env['project.project'].create({
            'name': 'PROJ-%s' % so.name, 'allow_billable': True,
            'partner_id': self.partner.id, 'sale_line_id': so.order_line[:1].id})
        return so, project

    def _bill(self, so, qty, invoice_date):
        invoice = so._create_invoices()
        invoice.invoice_date = invoice_date
        invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'product').quantity = qty
        invoice.action_post()
        return invoice

    def _validate(self, picking, qty=None):
        for move in picking.move_ids:
            move.quantity = qty if qty is not None else move.product_uom_qty
            move.picked = True
        res = picking.button_validate()
        self.assertTrue(res is True, 'Validation returned a wizard: %s' % res)

    def _delivery(self, so):
        return so.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')[:1]

    # ------------------------------------------------------------------
    def test_01_recognition_year_from_billing_milestone(self):
        so, project = self._make_so_project()
        self.assertEqual(project.lww_rec_status, 'not_ready')
        self._bill(so, 5, date(self.prev - 1, 3, 1))           # 50 %
        self.assertFalse(project.lww_billing_date)
        self.assertEqual(project.lww_rec_year, 0)
        picking = self._delivery(so)
        self.assertEqual(picking.x_project_id, project)
        self.assertEqual(picking.x_accounting_status, 'awaiting')
        self._bill(so, 4.5, date(self.prev, 8, 15))             # 95 % cumulative
        self.assertEqual(project.lww_billing_date, date(self.prev, 8, 15))
        self.assertEqual(project.lww_rec_year, self.prev)
        self.assertEqual(picking.x_accounting_status, 'pending')
        self.assertEqual(picking.x_recognition_year, self.prev)

    def test_02_delivery_creates_reclass_and_backdated(self):
        so, project = self._make_so_project()
        self._bill(so, 9.5, date(self.prev, 8, 15))
        picking = self._delivery(so)
        self._validate(picking)
        self.assertEqual(picking.x_accounting_status, 'recognized')
        self.assertEqual(picking.x_recognition_year, self.prev)
        reclass, backdated = picking.x_reclass_move_id, picking.x_backdated_move_id
        self.assertTrue(reclass and backdated)
        self.assertEqual(reclass.state, 'posted')
        self.assertEqual(backdated.state, 'posted')
        self.assertEqual(reclass.date, fields.Date.today())
        self.assertEqual(backdated.date, date(self.prev, 12, 31))
        # Standard Odoo entry: Dr WIP / Cr stock valuation (1000 = 10 x 100)
        standard = picking.move_ids.stock_valuation_layer_ids.account_move_id
        self.assertEqual(sum(standard.line_ids.filtered(
            lambda l: l.account_id == self.acc_wip).mapped('balance')), 1000.0)
        # Reclass: Dr Hutang / Cr WIP ; Backdated: Dr WIP / Cr Hutang
        self.assertEqual(reclass.line_ids.filtered(lambda l: l.account_id == self.acc_hutang).balance, 1000.0)
        self.assertEqual(reclass.line_ids.filtered(lambda l: l.account_id == self.acc_wip).balance, -1000.0)
        self.assertEqual(backdated.line_ids.filtered(lambda l: l.account_id == self.acc_wip).balance, 1000.0)
        self.assertEqual(backdated.line_ids.filtered(lambda l: l.account_id == self.acc_hutang).balance, -1000.0)
        # Linkage
        for move, kind in ((reclass, 'reclass'), (backdated, 'backdated')):
            self.assertEqual(move.lww_project_id, project)
            self.assertEqual(move.lww_picking_id, picking)
            self.assertEqual(move.lww_entry_type, kind)
        self.assertEqual(project.lww_do_count, 1)
        self.assertEqual(project.lww_reclass_count, 1)
        self.assertEqual(project.lww_backdated_count, 1)
        self.assertEqual(project.lww_rec_status, 'recognized')
        # Duplicate prevention
        picking._lww_process_recognition()
        self.assertEqual(project.lww_reclass_count, 1)
        with self.assertRaises(Exception), self.cr.savepoint():
            picking._lww_create_move('reclass', fields.Date.today(), {(self.acc_wip.id, '{}'): 1.0}, self.prev)

    def test_03_partial_return_reverses_proportionally(self):
        so, project = self._make_so_project()
        self._bill(so, 9.5, date(self.prev, 8, 15))
        picking = self._delivery(so)
        self._validate(picking)
        wizard = self.env['stock.return.picking'].with_context(
            active_id=picking.id, active_model='stock.picking').create({})
        wizard.product_return_moves.quantity = 4
        action = wizard.action_create_returns()
        ret = self.env['stock.picking'].browse(action['res_id'])
        self.assertTrue(ret.x_is_return)
        self.assertEqual(ret.x_project_id, project)
        self._validate(ret)
        self.assertEqual(ret.x_accounting_status, 'returned')
        rev_reclass, rev_back = ret.x_reclass_reversal_move_id, ret.x_backdated_reversal_move_id
        self.assertTrue(rev_reclass and rev_back)
        self.assertEqual(rev_reclass.date, fields.Date.today())
        self.assertEqual(rev_back.date, date(self.prev, 12, 31))
        # reversal reclass: Dr WIP / Cr Hutang (400)
        self.assertEqual(rev_reclass.line_ids.filtered(lambda l: l.account_id == self.acc_wip).balance, 400.0)
        self.assertEqual(rev_reclass.line_ids.filtered(lambda l: l.account_id == self.acc_hutang).balance, -400.0)
        # reversal backdated: Dr Hutang / Cr WIP (400)
        self.assertEqual(rev_back.line_ids.filtered(lambda l: l.account_id == self.acc_hutang).balance, 400.0)
        self.assertEqual(rev_back.line_ids.filtered(lambda l: l.account_id == self.acc_wip).balance, -400.0)
        self.assertEqual(rev_reclass.lww_origin_move_id, picking.x_reclass_move_id)
        self.assertEqual(rev_back.lww_origin_move_id, picking.x_backdated_move_id)
        self.assertEqual(project.lww_return_count, 1)
        self.assertEqual(project.lww_reversal_count, 2)
        self.assertTrue(project.lww_has_return)
        # original delivery stays recognized
        self.assertEqual(picking.x_accounting_status, 'recognized')

    def test_04_manual_override(self):
        so, project = self._make_so_project()
        picking = self._delivery(so)
        self.assertEqual(picking.x_accounting_status, 'awaiting')
        wizard = self.env['lww.recognition.override.wizard'].with_context(
            default_project_id=project.id).create({'manual_override': True, 'year': self.prev - 1})
        wizard.action_apply()
        self.assertEqual(project.lww_rec_year, self.prev - 1)
        self.assertEqual(project.lww_rec_mode, 'manual')
        self.assertEqual(picking.x_accounting_status, 'pending')
        self._validate(picking)
        self.assertEqual(picking.x_recognition_mode, 'manual')
        self.assertEqual(picking.x_backdated_move_id.date, date(self.prev - 1, 12, 31))
        # changing the override afterwards does not alter the recognized DO
        wizard = self.env['lww.recognition.override.wizard'].with_context(
            default_project_id=project.id).create({'manual_override': True, 'year': self.prev})
        wizard.action_apply()
        self.assertEqual(picking.x_recognition_year, self.prev - 1)

    def test_05_delivery_before_milestone_has_no_journal(self):
        so, project = self._make_so_project()
        picking = self._delivery(so)
        self._validate(picking)
        self.assertEqual(picking.state, 'done')
        self.assertFalse(picking.x_reclass_move_id)
        self.assertEqual(picking.x_accounting_status, 'awaiting')

    def test_06_same_year_recognition_creates_no_extra_journal(self):
        so, project = self._make_so_project()
        self._bill(so, 9.5, fields.Date.today())
        picking = self._delivery(so)
        self._validate(picking)
        self.assertEqual(picking.x_accounting_status, 'recognized')
        self.assertFalse(picking.x_reclass_move_id)
        self.assertFalse(picking.x_backdated_move_id)

    def test_07_locked_period_does_not_block_warehouse(self):
        so, project = self._make_so_project()
        self._bill(so, 9.5, date(self.prev, 8, 15))
        self.company.hard_lock_date = date(self.prev, 12, 31)
        picking = self._delivery(so)
        self._validate(picking)
        self.assertEqual(picking.state, 'done')
        self.assertFalse(picking.x_reclass_move_id)
        self.assertFalse(picking.x_backdated_move_id)
        self.assertEqual(picking.x_accounting_status, 'pending')
        self.assertEqual(project.lww_reclass_count, 0)
        self.assertTrue(project.message_ids.filtered(
            lambda m: 'could not be generated' in (m.body or '')))

    def test_08_actions_and_dashboard(self):
        so, project = self._make_so_project()
        self._bill(so, 9.5, date(self.prev, 8, 15))
        picking = self._delivery(so)
        self._validate(picking)
        for method in ('action_view_lww_pickings', 'action_view_lww_returns', 'action_view_lww_reclass',
                       'action_view_lww_backdated', 'action_view_lww_reversals', 'action_view_lww_all_journals'):
            action = getattr(project, method)()
            self.assertTrue(action['domain'])
        reclass_action = project.action_view_lww_reclass()
        self.assertEqual(self.env['account.move'].search_count(reclass_action['domain']), 1)
        self.assertEqual(self.env['stock.picking'].search_count(
            project.action_view_lww_pickings()['domain']), 1)
        self.assertEqual(project.action_open_recognition_wizard()['res_model'],
                         'lww.recognition.override.wizard')
        dashboard = self.env['project.project'].search([
            ('lww_rec_year', '=', self.prev), ('lww_rec_status', '=', 'recognized')])
        self.assertIn(project, dashboard)
        self.assertEqual(
            self.env['project.project'].search([('lww_manual_override', '=', True), ('id', '=', project.id)]),
            self.env['project.project'])
