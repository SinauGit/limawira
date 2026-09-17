from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

SEARCH_BATCH_SIZE = 1000


class ProjectAnalyticTransferWizard(models.TransientModel):
    _name = 'project.analytic.transfer.wizard'
    _description = 'Project and Analytic Transfer Wizard'

    source_project_id = fields.Many2one('project.project', string='Source Project')
    source_analytic_account_id = fields.Many2one('account.analytic.account', string='Source Analytic Account')

    target_project_id = fields.Many2one('project.project', string='Target Project', required=True)
    target_analytic_account_id = fields.Many2one('account.analytic.account', string='Target Analytic Account')

    update_project = fields.Boolean(string='Update Project', default=True)
    update_analytic = fields.Boolean(string='Update Analytic', default=True)

    process_sale_orders = fields.Boolean(string='Sales Orders', default=True)
    process_purchase_orders = fields.Boolean(string='Purchase Orders', default=True)
    process_account_moves = fields.Boolean(string='Invoices/Bills/Journal Entries', default=True)
    process_expenses = fields.Boolean(string='Expenses', default=True)
    process_stock_moves = fields.Boolean(string='Stock Moves', default=True)

    @api.onchange('source_project_id')
    def _onchange_source_project_id(self):
        """Auto-fill source analytic account from source project.

        This is only a default - user can still override it manually,
        e.g. when the project's analytic account was changed later and
        older transactions still reference the previous one.
        """
        if self.source_project_id:
            if hasattr(self.source_project_id, 'account_id') and self.source_project_id.account_id:
                self.source_analytic_account_id = self.source_project_id.account_id
            elif hasattr(self.source_project_id, 'analytic_account_id') and self.source_project_id.analytic_account_id:
                self.source_analytic_account_id = self.source_project_id.analytic_account_id

    @api.onchange('target_project_id')
    def _onchange_target_project_id(self):
        """Auto-fill target analytic account from target project"""
        if self.target_project_id:
            if hasattr(self.target_project_id, 'account_id') and self.target_project_id.account_id:
                self.target_analytic_account_id = self.target_project_id.account_id
            elif hasattr(self.target_project_id, 'analytic_account_id') and self.target_project_id.analytic_account_id:
                self.target_analytic_account_id = self.target_project_id.analytic_account_id

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def action_transfer(self):
        """Main transfer action"""
        self.ensure_one()

        if not self.update_project and not self.update_analytic:
            raise UserError(_('Please select at least one option to update (Project or Analytic).'))

        if not self.source_project_id and not self.source_analytic_account_id:
            raise UserError(_(
                'Please select at least one source criterion (Source Project or Source Analytic Account). '
                'Leaving both empty would match every record in the system.'
            ))

        # Precompute string ids once per run instead of on every record.
        self._source_id_str = str(self.source_analytic_account_id.id) if self.source_analytic_account_id else False
        self._target_id_str = str(self.target_analytic_account_id.id) if self.target_analytic_account_id else False

        log = self.env['project.analytic.transfer.log'].create({
            'source_project_id': self.source_project_id.id,
            'source_analytic_account_id': self.source_analytic_account_id.id,
            'target_project_id': self.target_project_id.id,
            'target_analytic_account_id': self.target_analytic_account_id.id,
            'user_id': self.env.user.id,
            'state': 'in_progress',
        })

        try:
            updated_records = []

            if self.process_sale_orders:
                updated_records.extend(self._process_sale_orders())

            if self.process_purchase_orders:
                updated_records.extend(self._process_purchase_orders())

            if self.process_account_moves:
                updated_records.extend(self._process_account_moves())

            if self.process_expenses:
                expense_results = self._process_expenses_via_sheets()
                if not expense_results:
                    _logger.debug("Sheet-based expense processing yielded no results, trying direct method")
                    expense_results = self._process_expenses()
                updated_records.extend(expense_results)

            if self.process_stock_moves:
                updated_records.extend(self._process_stock_moves())

            log.write({
                'state': 'done',
                'records_updated': len(updated_records),
                'details': '\n'.join(updated_records),
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'title': _('Transfer Complete'),
                    'message': _('%d records updated successfully.') % len(updated_records),
                    'sticky': False,
                }
            }

        except Exception as e:
            log.write({
                'state': 'error',
                'details': str(e),
            })
            raise

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _search_in_batches(self, model_name, domain):
        """Search a model in chunks so large tables don't load into memory at once.

        Returns the model recordset (all matches), fetched batch by batch.
        """
        Model = self.env[model_name]
        result = Model
        offset = 0
        while True:
            batch = Model.search(domain, limit=SEARCH_BATCH_SIZE, offset=offset)
            if not batch:
                break
            result |= batch
            if len(batch) < SEARCH_BATCH_SIZE:
                break
            offset += SEARCH_BATCH_SIZE
        return result

    def _update_analytic_distribution(self, record, field_name='analytic_distribution'):
        """Compute the new analytic distribution for a record, if it should change.

        Returns the new distribution dict, or False if no update is needed.
        (Does not write - caller decides whether/how to write, so callers can batch.)
        """
        if not self.update_analytic or not self.target_analytic_account_id:
            return False

        if field_name not in record._fields:
            return False

        current_distribution = record[field_name] or {}
        new_distribution = {}

        if self._source_id_str:
            for key, value in current_distribution.items():
                if key == self._source_id_str:
                    new_distribution[self._target_id_str] = value
                else:
                    new_distribution[key] = value
        else:
            total_percentage = sum(current_distribution.values()) if current_distribution else 100.0
            new_distribution = {self._target_id_str: total_percentage}

        if new_distribution != current_distribution:
            return new_distribution
        return False

    def _batch_update_project(self, records, label):
        """Set project_id on a whole recordset in a single write call."""
        updated = []
        if not records:
            return updated
        if self.update_project and self.target_project_id and 'project_id' in records._fields:
            records.write({'project_id': self.target_project_id.id})
            updated.extend([f"{label}: {r.display_name}" for r in records])
        return updated

    def _batch_update_analytic(self, records, label_field='display_name', label_prefix=''):
        """Compute and write analytic_distribution changes per-record (values differ
        per record) but group the log message building; still one write per record
        because each new distribution dict is different, which is unavoidable for
        this field. Kept isolated so callers stay simple.
        """
        updated = []
        for rec in records:
            if not rec.exists():
                continue
            new_distribution = self._update_analytic_distribution(rec)
            if new_distribution:
                rec.write({'analytic_distribution': new_distribution})
                updated.append(f"{label_prefix}{getattr(rec, label_field, rec.display_name)}")
        return updated

    # ------------------------------------------------------------------
    # Sale Orders
    # ------------------------------------------------------------------
    def _process_sale_orders(self):
        """Process Sale Orders and their lines"""
        updated = []

        if self.source_project_id:
            sale_orders = self._search_in_batches(
                'sale.order', [('project_id', '=', self.source_project_id.id)]
            )
            updated.extend(self._batch_update_project(sale_orders, 'SO'))

        if self.source_analytic_account_id:
            sol_domain = [('analytic_distribution', '!=', False)]
            if self.source_project_id:
                sol_domain.append(('order_id.project_id', '=', self.source_project_id.id))
            sol_records = self._search_in_batches('sale.order.line', sol_domain)
            for line in sol_records:
                if not line.exists():
                    continue
                new_distribution = self._update_analytic_distribution(line)
                if new_distribution:
                    line.write({'analytic_distribution': new_distribution})
                    updated.append(f"SO Line: {line.order_id.name} - {line.name}")

        return updated

    # ------------------------------------------------------------------
    # Purchase Orders
    # ------------------------------------------------------------------
    def _process_purchase_orders(self):
        """Process Purchase Orders and their lines"""
        updated = []

        if self.source_project_id and 'project_id' in self.env['purchase.order']._fields:
            purchase_orders = self._search_in_batches(
                'purchase.order', [('project_id', '=', self.source_project_id.id)]
            )
            updated.extend(self._batch_update_project(purchase_orders, 'PO'))

        if self.source_analytic_account_id:
            pol_domain = [('analytic_distribution', '!=', False)]
            if self.source_project_id and 'project_id' in self.env['purchase.order']._fields:
                pol_domain.append(('order_id.project_id', '=', self.source_project_id.id))
            pol_records = self._search_in_batches('purchase.order.line', pol_domain)
            for line in pol_records:
                if not line.exists():
                    continue
                new_distribution = self._update_analytic_distribution(line)
                if new_distribution:
                    line.write({'analytic_distribution': new_distribution})
                    updated.append(f"PO Line: {line.order_id.name} - {line.name}")

        return updated

    # ------------------------------------------------------------------
    # Account Moves (Invoices/Bills/Journal Entries)
    # ------------------------------------------------------------------
    def _process_account_moves(self):
        """Process Account Moves (Invoices/Bills/Journal Entries)"""
        updated = []

        if not self.source_analytic_account_id:
            return updated

        domain = [('analytic_distribution', '!=', False)]
        if self.source_project_id and 'project_id' in self.env['account.move']._fields:
            domain.append(('move_id.project_id', '=', self.source_project_id.id))

        aml_records = self._search_in_batches('account.move.line', domain)

        moves_to_repost = self.env['account.move']
        lines_to_write = []  # list of (line, new_distribution)

        for line in aml_records:
            if not line.exists():
                continue
            new_distribution = self._update_analytic_distribution(line)
            if not new_distribution:
                continue
            move = line.move_id
            if not move.exists():
                continue
            if move.state == 'posted':
                moves_to_repost |= move
            lines_to_write.append((line, new_distribution))

        if moves_to_repost:
            moves_to_repost.button_draft()

        for line, new_distribution in lines_to_write:
            line.write({'analytic_distribution': new_distribution})
            updated.append(f"Journal Item: {line.move_id.name} - {line.name}")

        if moves_to_repost:
            try:
                moves_to_repost.action_post()
            except Exception as e:
                _logger.warning(f"Error reposting moves {moves_to_repost.mapped('name')}: {str(e)}")

        return updated

    # ------------------------------------------------------------------
    # Expenses
    # ------------------------------------------------------------------
    def _should_update_expense_analytic(self, expense):
        """Check if expense analytic distribution should be updated"""
        if not self.update_analytic or not self.target_analytic_account_id:
            return False

        current_distribution = expense.analytic_distribution or {}

        if self._source_id_str:
            return self._source_id_str in current_distribution
        return bool(current_distribution)

    def _process_expenses(self):
        """Process HR Expenses directly (fallback when sheet-based processing found nothing)"""
        updated = []

        if 'analytic_distribution' not in self.env['hr.expense']._fields:
            _logger.debug("Field 'analytic_distribution' does not exist in hr.expense model")
            return updated

        if not self.source_analytic_account_id:
            # No safe criterion to narrow the expense search on this path.
            return updated

        domain = [
            ('analytic_distribution', '!=', False),
            ('state', 'in', ['draft', 'reported']),
        ]
        expense_records = self._search_in_batches('hr.expense', domain)
        _logger.debug(f"Found {len(expense_records)} expense records")

        sheets_to_reset = self.env['hr.expense.sheet']
        expenses_to_update = self.env['hr.expense']

        for expense in expense_records:
            if not expense.exists():
                continue
            if self._should_update_expense_analytic(expense):
                expenses_to_update |= expense
                if hasattr(expense, 'sheet_id') and expense.sheet_id:
                    if expense.sheet_id.state != 'draft':
                        sheets_to_reset |= expense.sheet_id

        if sheets_to_reset:
            try:
                sheets_to_reset.sudo().action_reset_expense_sheets()
            except Exception as e:
                _logger.error(f"Failed to reset expense sheets {sheets_to_reset.ids}: {str(e)}")

        for expense in expenses_to_update:
            if not expense.exists():
                continue
            expense.invalidate_recordset()
            new_distribution = self._update_analytic_distribution(expense)
            if new_distribution:
                expense.sudo().write({'analytic_distribution': new_distribution})
                updated.append(f"Expense: {expense.name}")

        return updated

    def _process_expenses_via_sheets(self):
        """Process expenses by handling expense sheets directly"""
        updated = []

        if not self.source_analytic_account_id:
            return updated

        domain = [('expense_line_ids.analytic_distribution', '!=', False)]
        if self.source_project_id:
            # Narrow to the source project wherever the sheet is linked to one.
            if 'project_id' in self.env['hr.expense.sheet']._fields:
                domain.append(('project_id', '=', self.source_project_id.id))

        expense_sheets = self._search_in_batches('hr.expense.sheet', domain)
        _logger.debug(f"Found {len(expense_sheets)} expense sheets to process")

        sheets_to_reset = expense_sheets.filtered(lambda s: s.state != 'draft')
        if sheets_to_reset:
            sheets_to_reset.sudo().action_reset_expense_sheets()

        for sheet in expense_sheets:
            relevant_expenses = sheet.expense_line_ids.filtered(
                lambda exp: exp.analytic_distribution and
                (not self._source_id_str or self._source_id_str in exp.analytic_distribution)
            )
            for expense in relevant_expenses:
                new_distribution = self._update_analytic_distribution(expense)
                if new_distribution:
                    expense.sudo().write({'analytic_distribution': new_distribution})
                    updated.append(f"Expense: {expense.name} (via sheet {sheet.name})")

        return updated

    # ------------------------------------------------------------------
    # Stock Moves
    # ------------------------------------------------------------------
    def _process_stock_moves(self):
        """Process Stock Moves, Delivery Orders, and Receipts"""
        updated = []

        if self.source_project_id and 'project_id' in self.env['stock.picking']._fields:
            picking_records = self._search_in_batches(
                'stock.picking', [('project_id', '=', self.source_project_id.id)]
            )
            updated.extend(self._batch_update_project(picking_records, 'DO/Receipt'))

        picking_has_project = 'project_id' in self.env['stock.picking']._fields

        if self.source_analytic_account_id:
            sml_domain = [('analytic_distribution', '!=', False)]
            if self.source_project_id and picking_has_project:
                sml_domain.append(('picking_id.project_id', '=', self.source_project_id.id))
            sml_records = self._search_in_batches('stock.move.line', sml_domain)
            for line in sml_records:
                if not line.exists():
                    continue
                new_distribution = self._update_analytic_distribution(line)
                if new_distribution:
                    line.write({'analytic_distribution': new_distribution})
                    updated.append(f"Stock Move Line: {line.move_id.name} - {line.product_id.name}")

            if 'analytic_distribution' in self.env['stock.move']._fields:
                sm_domain = [('analytic_distribution', '!=', False)]
                if self.source_project_id and picking_has_project:
                    sm_domain.append(('picking_id.project_id', '=', self.source_project_id.id))
                sm_records = self._search_in_batches('stock.move', sm_domain)
                for move in sm_records:
                    if not move.exists():
                        continue
                    new_distribution = self._update_analytic_distribution(move)
                    if new_distribution:
                        move.write({'analytic_distribution': new_distribution})
                        updated.append(f"Stock Move: {move.name} - {move.product_id.name}")

        return updated
