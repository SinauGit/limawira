from datetime import date

from odoo import fields


def _post_init(env, company_id=None):
    if company_id:
        company = env['res.company'].browse(company_id)
    else:
        company = env.companies[:1] or env['res.company'].search([], limit=1)
    env = env(context=dict(env.context, allowed_company_ids=company.ids))
    today = fields.Date.context_today(env['res.users'])
    year = today.year
    Account = env['account.account']
    Journal = env['account.journal']

    def acc(code, name, atype, exclude=(), **kw):
        found = Account.search([('company_ids', 'in', company.id), ('account_type', '=', atype),
                                ('id', 'not in', [a.id for a in exclude])], limit=1, order='code')
        if found:
            return found
        return Account.create({'code': code, 'name': name, 'account_type': atype,
                               'company_ids': [(6, 0, company.ids)], **kw})

    wip = acc('DUM1061', 'DUMMY WIP Project', 'asset_current')
    stock = acc('DUM1101', 'DUMMY Inventory', 'asset_current', exclude=wip)
    payable = acc('DUM2201', 'DUMMY Hutang Biaya Proyek', 'liability_current')
    income = acc('DUM4001', 'DUMMY Income', 'income')
    journal_rec = Journal.create({'name': 'DUMMY Recognition', 'code': 'DUMR', 'type': 'general', 'company_id': company.id})
    journal_stock = Journal.create({'name': 'DUMMY Stock', 'code': 'DUMS', 'type': 'general', 'company_id': company.id})
    journal_sale = Journal.create({'name': 'DUMMY Sales', 'code': 'DUMI', 'type': 'sale', 'company_id': company.id})

    if not env['lww.recognition.config'].search([('company_id', '=', company.id)]):
        env['lww.recognition.config'].create({
            'company_id': company.id, 'journal_id': journal_rec.id, 'payable_account_id': payable.id,
            'threshold': 90.0, 'go_live_date': date(year - 5, 1, 1)})

    partner = env['res.partner'].create({'name': 'DUMMY Customer'})
    if not partner.property_account_receivable_id:
        partner.property_account_receivable_id = acc('DUM1201', 'DUMMY Receivable', 'asset_receivable', reconcile=True)
    if not partner.property_account_payable_id:
        partner.property_account_payable_id = acc('DUM2101', 'DUMMY Payable', 'liability_payable', reconcile=True)

    categ = env['product.category'].create({
        'name': 'DUMMY Project Goods', 'property_cost_method': 'average', 'property_valuation': 'real_time',
        'property_stock_valuation_account_id': stock.id,
        'property_stock_account_input_categ_id': wip.id,
        'property_stock_account_output_categ_id': wip.id,
        'property_account_expense_categ_id': wip.id,
        'property_account_income_categ_id': income.id,
        'property_stock_journal': journal_stock.id})
    product = env['product.product'].create({
        'name': 'DUMMY Project Item', 'is_storable': True, 'tracking': 'none', 'type': 'consu', 'categ_id': categ.id,
        'standard_price': 100.0, 'list_price': 1000.0})
    warehouse = env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
    env['stock.quant'].with_context(inventory_mode=True).create({
        'product_id': product.id, 'location_id': warehouse.lot_stock_id.id,
        'inventory_quantity': 1000}).action_apply_inventory()
    plan = env['account.analytic.plan'].search([], limit=1) or env['account.analytic.plan'].create({'name': 'Project'})

    def project(name):
        analytic = env['account.analytic.account'].create({'name': name, 'plan_id': plan.id, 'company_id': company.id})
        so_vals = {}
        if 'no_so' in env['sale.order']._fields:
            so_vals['no_so'] = '%s-%s' % (name.split()[0], today.strftime('%y%m%d'))
        order = env['sale.order'].create({
            'partner_id': partner.id, 'company_id': company.id, **so_vals,
            'order_line': [(0, 0, {'product_id': product.id, 'product_uom_qty': 10, 'price_unit': 1000.0,
                                   'tax_id': [(5, 0, 0)], 'analytic_distribution': {str(analytic.id): 100}})]})
        proj = env['project.project'].create({
            'name': name, 'account_id': analytic.id, 'partner_id': partner.id,
            'sale_line_id': order.order_line.id})
        if order.state != 'sale':
            order.action_confirm()
        return proj, order

    counter = [0]

    def invoice(proj, amount, inv_date):
        counter[0] += 1
        inv_vals = {}
        if 'invoice_no' in env['account.move']._fields:
            inv_vals['invoice_no'] = 'DUMMY-INV-%s-%s' % (today.strftime('%y%m%d'), counter[0])
        move = env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': partner.id, 'invoice_date': inv_date, **inv_vals,
            'journal_id': journal_sale.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'DUMMY billing', 'quantity': 1, 'price_unit': amount, 'account_id': income.id,
                'tax_ids': [(5, 0, 0)], 'analytic_distribution': {str(proj.account_id.id): 100}})]})
        move.action_post()

    def ready(order):
        picking = order.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')[:1]
        field = picking._fields.get('customer_id')
        if field and field.type == 'many2one' and field.comodel_name == 'res.partner':
            picking.customer_id = partner
        picking.action_assign()
        return picking

    # A: 90% reached last year, DO not validated yet -> validate: reclass + backdate
    proj, order = project('DUMMY-A 90% tahun lalu')
    invoice(proj, 6000, date(year - 1, 3, 10))
    invoice(proj, 3000, date(year - 1, 11, 20))
    ready(order)

    # B: only 60% billed, DO not validated yet -> validate: Awaiting; then override / add invoices
    proj, order = project('DUMMY-B 60% belum 90%')
    invoice(proj, 6000, date(year - 1, 6, 15))
    ready(order)

    # C: 90% reached this year, DO not validated yet -> validate: Recognized without journals
    proj, order = project('DUMMY-C 90% tahun ini')
    invoice(proj, 6000, date(year, 1, 10))
    invoice(proj, 3000, today)
    ready(order)

    # D: DO already validated (Awaiting), then 90% reached last year -> Pending, use "Process Pending DOs"
    proj, order = project('DUMMY-D DO sudah done lalu 90% tahun lalu')
    picking = ready(order)
    for move in picking.move_ids:
        move.quantity = move.product_uom_qty
        move.picked = True
    picking.with_context(skip_backorder=True, skip_sms=True).button_validate()
    invoice(proj, 6000, date(year - 1, 4, 5))
    invoice(proj, 3000, date(year - 1, 9, 25))
