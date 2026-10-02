import json
import logging
from collections import defaultdict
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

ENTRY_LABELS = {
    'reclass': 'Reclassification',
    'backdated': 'Backdated Recognition',
    'reversal_reclass': 'Reversal Reclassification',
    'reversal_backdated': 'Reversal Backdated Recognition',
}


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    x_project_id = fields.Many2one(
        'project.project', string='Recognition Project', compute='_compute_x_project_id',
        store=True, index='btree_not_null', recursive=True)
    x_is_return = fields.Boolean(
        string='Return of Delivery Order', compute='_compute_x_is_return', store=True)
    x_recognized = fields.Boolean(string='Recognition Processed', copy=False, readonly=True)
    x_recognized_year = fields.Integer(copy=False, readonly=True)
    x_recognized_mode = fields.Selection(
        [('automatic', 'Automatic (90% Rule)'), ('manual', 'Manual Override')],
        copy=False, readonly=True)
    x_recognition_year = fields.Integer(
        string='Recognition Year', compute='_compute_x_recognition', store=True)
    x_recognition_mode = fields.Selection(
        [('automatic', 'Automatic (90% Rule)'), ('manual', 'Manual Override')],
        string='Recognition Mode', compute='_compute_x_recognition', store=True)
    x_accounting_status = fields.Selection(
        [('awaiting', 'Awaiting Recognition'),
         ('pending', 'Pending Recognition'),
         ('recognized', 'Recognized'),
         ('returned', 'Returned & Reversed')],
        string='Accounting Status', compute='_compute_x_accounting_status', store=True)
    x_reclass_move_id = fields.Many2one(
        'account.move', string='Reclassification Journal', copy=False, readonly=True,
        index='btree_not_null')
    x_backdated_move_id = fields.Many2one(
        'account.move', string='Backdated Journal', copy=False, readonly=True,
        index='btree_not_null')
    x_reclass_reversal_move_id = fields.Many2one(
        'account.move', string='Reclassification Reversal Journal', copy=False, readonly=True,
        index='btree_not_null')
    x_backdated_reversal_move_id = fields.Many2one(
        'account.move', string='Backdated Reversal Journal', copy=False, readonly=True,
        index='btree_not_null')

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('sale_id', 'sale_id.project_id', 'return_id.x_project_id')
    def _compute_x_project_id(self):
        Project = self.env['project.project'].sudo()
        for picking in self:
            project = Project
            if picking.sale_id:
                project = Project._lww_projects_from_orders(picking.sale_id)[:1]
            if not project and picking.return_id:
                project = picking.return_id.x_project_id
            picking.x_project_id = project

    @api.depends('return_id', 'return_id.picking_type_id.code')
    def _compute_x_is_return(self):
        for picking in self:
            picking.x_is_return = bool(
                picking.return_id and picking.return_id.picking_type_id.code == 'outgoing')

    @api.depends('x_recognized', 'x_recognized_year', 'x_recognized_mode',
                 'x_project_id.lww_rec_year', 'x_project_id.lww_manual_override')
    def _compute_x_recognition(self):
        for picking in self:
            if picking.x_recognized:
                picking.x_recognition_year = picking.x_recognized_year
                picking.x_recognition_mode = picking.x_recognized_mode
            elif picking.x_project_id:
                picking.x_recognition_year = picking.x_project_id.lww_rec_year
                picking.x_recognition_mode = (
                    'manual' if picking.x_project_id.lww_manual_override else 'automatic')
            else:
                picking.x_recognition_year = 0
                picking.x_recognition_mode = False

    @api.depends('x_project_id', 'x_project_id.lww_rec_year', 'x_recognized',
                 'x_is_return', 'picking_type_id.code')
    def _compute_x_accounting_status(self):
        for picking in self:
            if not picking.x_project_id:
                picking.x_accounting_status = False
            elif picking.x_is_return:
                picking.x_accounting_status = 'returned' if picking.x_recognized else False
            elif picking.picking_type_id.code != 'outgoing':
                picking.x_accounting_status = False
            elif picking.x_recognized:
                picking.x_accounting_status = 'recognized'
            elif picking.x_project_id.lww_rec_year:
                picking.x_accounting_status = 'pending'
            else:
                picking.x_accounting_status = 'awaiting'

    # ------------------------------------------------------------------
    # Hook
    # ------------------------------------------------------------------
    def _action_done(self):
        res = super()._action_done()
        self._lww_process_recognition()
        return res

    def _lww_process_recognition(self):
        pickings = self.filtered(
            lambda p: p.state == 'done' and p.x_project_id and not p.x_recognized
            and (p.x_is_return or p.picking_type_id.code == 'outgoing'))
        for picking in pickings:
            try:
                with self.env.cr.savepoint():
                    if picking.x_is_return:
                        picking._lww_process_return()
                    else:
                        picking._lww_process_delivery()
            except Exception as error:  # never block the warehouse flow
                _logger.exception('Project recognition failed for %s', picking.name)
                message = _('Recognition journals could not be generated: %s', str(error))
                picking.sudo().message_post(body=message)
                picking.x_project_id.sudo().message_post(
                    body=_('%(picking)s: %(message)s', picking=picking.name, message=message))

    # ------------------------------------------------------------------
    # Delivery Order processing (FR-03 / FR-04 / FR-06)
    # ------------------------------------------------------------------
    def _lww_done_date(self):
        self.ensure_one()
        return fields.Date.context_today(self, self.date_done or fields.Datetime.now())

    def _lww_process_delivery(self):
        self.ensure_one()
        project = self.x_project_id.sudo()
        year = project.lww_rec_year
        if not year:
            return  # stays "Awaiting Recognition": no journal without a recognition year
        picking = self.sudo()
        done_date = picking._lww_done_date()
        values = {
            'x_recognized': True,
            'x_recognized_year': year,
            'x_recognized_mode': 'manual' if project.lww_manual_override else 'automatic',
        }
        if year < done_date.year:
            lines = picking._lww_collect_lines(1)
            if lines:
                reclass = picking._lww_create_move('reclass', done_date, lines, year)
                backdated = picking._lww_create_move(
                    'backdated', date(year, 12, 31), lines, year)
                values.update({
                    'x_reclass_move_id': reclass.id,
                    'x_backdated_move_id': backdated.id,
                })
        picking.write(values)
        if values.get('x_reclass_move_id'):
            project.message_post(body=_(
                '%(picking)s recognized in %(year)s: %(reclass)s / %(backdated)s',
                picking=picking.name, year=year,
                reclass=reclass.name, backdated=backdated.name))

    # ------------------------------------------------------------------
    # Return processing (FR-07)
    # ------------------------------------------------------------------
    def _lww_process_return(self):
        self.ensure_one()
        picking = self.sudo()
        origin = picking.return_id
        values = {
            'x_recognized': True,
            'x_recognized_year': origin.x_recognized_year,
            'x_recognized_mode': origin.x_recognized_mode,
        }
        if origin.x_reclass_move_id and origin.x_backdated_move_id:
            lines = picking._lww_collect_lines(-1)
            if lines:
                year = origin.x_recognized_year
                reversal_reclass = picking._lww_create_move(
                    'reversal_reclass', picking._lww_done_date(), lines, year,
                    origin_move=origin.x_reclass_move_id)
                reversal_backdated = picking._lww_create_move(
                    'reversal_backdated', date(year, 12, 31), lines, year,
                    origin_move=origin.x_backdated_move_id)
                values.update({
                    'x_reclass_reversal_move_id': reversal_reclass.id,
                    'x_backdated_reversal_move_id': reversal_backdated.id,
                })
        picking.write(values)
        if values.get('x_reclass_reversal_move_id'):
            picking.x_project_id.sudo().message_post(body=_(
                '%(picking)s reversed: %(reclass)s / %(backdated)s',
                picking=picking.name, reclass=reversal_reclass.name,
                backdated=reversal_backdated.name))

    # ------------------------------------------------------------------
    # Journal helpers
    # ------------------------------------------------------------------
    def _lww_collect_lines(self, sign):
        """Aggregate the stock valuation journal lines of this transfer.

        sign=1: debit lines (delivery: Dr WIP / output account).
        sign=-1: credit lines (return: Cr WIP / output account).
        Returns {(account_id, analytic_distribution_json): amount}."""
        self.ensure_one()
        project = self.x_project_id.sudo()
        currency = self.company_id.currency_id
        lines = self.move_ids.sudo().stock_valuation_layer_ids.account_move_id.line_ids
        grouped = defaultdict(float)
        for line in lines:
            amount = line.balance * sign
            if float_compare(amount, 0.0, precision_rounding=currency.rounding) <= 0:
                continue
            distribution = line.analytic_distribution
            if not distribution and project.account_id:
                distribution = {str(project.account_id.id): 100.0}
            key = (line.account_id.id, json.dumps(distribution or {}, sort_keys=True))
            grouped[key] += amount
        return {key: currency.round(amount) for key, amount in grouped.items()}

    def _lww_create_move(self, entry_type, move_date, lines, year, origin_move=None):
        self.ensure_one()
        company = self.company_id
        journal = company.lww_rec_journal_id
        payable = company.lww_rec_payable_account_id
        if not journal or not payable:
            raise UserError(_(
                'Set the Recognition Journal and the Project Cost Payable Account '
                'in the accounting settings of %s.', company.name))
        wip_is_debit = entry_type in ('backdated', 'reversal_reclass')
        label = _('%(picking)s - %(type)s', picking=self.name, type=ENTRY_LABELS[entry_type])
        line_vals = []
        for (account_id, distribution), amount in lines.items():
            distribution = json.loads(distribution) or False
            line_vals.append((0, 0, {
                'name': label,
                'account_id': account_id,
                'analytic_distribution': distribution,
                'debit': amount if wip_is_debit else 0.0,
                'credit': 0.0 if wip_is_debit else amount,
            }))
            line_vals.append((0, 0, {
                'name': label,
                'account_id': payable.id,
                'analytic_distribution': distribution,
                'debit': 0.0 if wip_is_debit else amount,
                'credit': amount if wip_is_debit else 0.0,
            }))
        move = self.env['account.move'].with_company(company).create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'company_id': company.id,
            'date': move_date,
            'ref': label,
            'line_ids': line_vals,
            'lww_project_id': self.x_project_id.id,
            'lww_picking_id': self.id,
            'lww_entry_type': entry_type,
            'lww_recognition_year': year,
            'lww_origin_move_id': origin_move.id if origin_move else False,
        })
        move._post(soft=False)
        if move.date != move_date:
            # Odoo silently moves the date of an entry posted in a locked period:
            # never accept a recognition journal outside its intended period.
            raise UserError(_(
                'The %(type)s journal must be dated %(date)s but that period is locked '
                '(Odoo moved it to %(actual)s).',
                type=ENTRY_LABELS[entry_type], date=move_date, actual=move.date))
        return move
