from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ProjectAnalyticTransferWizard(models.TransientModel):
    _name = 'project.analytic.transfer.wizard'
    _description = 'Project and Analytic Transfer Wizard'

    # Source filters
    source_project_id = fields.Many2one('project.project', string='Source Project')
    source_analytic_account_id = fields.Many2one('account.analytic.account', string='Source Analytic Account')
    
    # Target
    target_project_id = fields.Many2one('project.project', string='Target Project', required=True)
    target_analytic_account_id = fields.Many2one('account.analytic.account', string='Target Analytic Account')
    
    # Options
    update_project = fields.Boolean(string='Update Project', default=True)
    update_analytic = fields.Boolean(string='Update Analytic', default=True)
    
    # Document types to process
    process_sale_orders = fields.Boolean(string='Sales Orders', default=True)
    process_purchase_orders = fields.Boolean(string='Purchase Orders', default=True)
    process_account_moves = fields.Boolean(string='Invoices/Bills/Journal Entries', default=True)
    process_expenses = fields.Boolean(string='Expenses', default=True)
    process_stock_moves = fields.Boolean(string='Stock Moves', default=True)

    @api.onchange('target_project_id')
    def _onchange_target_project_id(self):
        """Auto-fill target analytic account from target project"""
        if self.target_project_id:
            # In Odoo 18, project analytic account might be accessed differently
            # Try to get the analytic account from project's account_id field
            if hasattr(self.target_project_id, 'account_id') and self.target_project_id.account_id:
                self.target_analytic_account_id = self.target_project_id.account_id
            # Alternative: check if there's an analytic_account_id field
            elif hasattr(self.target_project_id, 'analytic_account_id') and self.target_project_id.analytic_account_id:
                self.target_analytic_account_id = self.target_project_id.analytic_account_id

    def action_transfer(self):
        """Main transfer action"""
        self.ensure_one()
        
        if not self.update_project and not self.update_analytic:
            raise UserError(_('Please select at least one option to update (Project or Analytic).'))
        
        # Create log entry
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
            
            # Process each document type
            if self.process_sale_orders:
                updated_records.extend(self._process_sale_orders())
            
            if self.process_purchase_orders:
                updated_records.extend(self._process_purchase_orders())
            
            if self.process_account_moves:
                updated_records.extend(self._process_account_moves())
            
            if self.process_expenses:
                # Try sheet-based approach first
                expense_results = self._process_expenses_via_sheets()
                if not expense_results:
                    _logger.info("Sheet-based expense processing yielded no results, trying direct method")
                    expense_results = self._process_expenses()
                updated_records.extend(expense_results)
            
            if self.process_stock_moves:
                updated_records.extend(self._process_stock_moves())
            
            # Update log
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

    def _get_domain_filters(self):
        """Build domain filters based on source criteria - DEPRECATED"""
        # This method is deprecated, use specific domain building in each process method
        domain = []
        if self.source_analytic_account_id:
            domain.append(('analytic_distribution', '!=', False))
        return domain

    def _update_analytic_distribution(self, record, field_name='analytic_distribution'):
        """Update analytic distribution for a record"""
        if not self.update_analytic or not self.target_analytic_account_id:
            return False
        
        # Check if field exists
        if field_name not in record._fields:
            return False
            
        current_distribution = record[field_name] or {}
        new_distribution = {}
        
        if self.source_analytic_account_id:
            # Update specific source analytic to target
            source_id_str = str(self.source_analytic_account_id.id)
            target_id_str = str(self.target_analytic_account_id.id)
            
            for key, value in current_distribution.items():
                if key == source_id_str:
                    new_distribution[target_id_str] = value
                else:
                    new_distribution[key] = value
        else:
            # Replace all with target analytic
            total_percentage = sum(current_distribution.values()) if current_distribution else 100.0
            new_distribution = {str(self.target_analytic_account_id.id): total_percentage}
        
        if new_distribution != current_distribution:
            record[field_name] = new_distribution
            return True
        return False

    def _process_sale_orders(self):
        """Process Sale Orders and their lines"""
        updated = []
        
        # Process Sale Orders (header level) - use only project_id
        so_domain = []
        if self.source_project_id:
            so_domain.append(('project_id', '=', self.source_project_id.id))
        
        if so_domain:
            sale_orders = self.env['sale.order'].search(so_domain)
            for order in sale_orders:
                try:
                    if not order.exists():
                        continue
                        
                    update_vals = {}
                    
                    if self.update_project and self.target_project_id:
                        update_vals['project_id'] = self.target_project_id.id
                    
                    if update_vals:
                        order.write(update_vals)
                        updated.append(f"SO: {order.name}")
                        
                except Exception as e:
                    _logger.warning(f"Error processing sale.order {order.id}: {str(e)}")
                    continue
        
        # Process Sale Order Lines for analytic_distribution
        sol_domain = []
        if self.source_analytic_account_id:
            sol_domain.append(('analytic_distribution', '!=', False))
        
        if sol_domain:
            sol_records = self.env['sale.order.line'].search(sol_domain)
            for line in sol_records:
                try:
                    if not line.exists():
                        continue
                        
                    if self._update_analytic_distribution(line):
                        line.write({'analytic_distribution': line.analytic_distribution})
                        updated.append(f"SO Line: {line.order_id.name} - {line.name}")
                        
                except Exception as e:
                    _logger.warning(f"Error processing sale.order.line {line.id}: {str(e)}")
                    continue
        
        return updated

    def _process_purchase_orders(self):
        """Process Purchase Orders and their lines"""
        updated = []
        
        # Process Purchase Orders (header level) - check if project_id exists
        po_domain = []
        if self.source_project_id and 'project_id' in self.env['purchase.order']._fields:
            po_domain.append(('project_id', '=', self.source_project_id.id))
        
        if po_domain:
            purchase_orders = self.env['purchase.order'].search(po_domain)
            for order in purchase_orders:
                try:
                    if not order.exists():
                        continue
                        
                    update_vals = {}
                    
                    if self.update_project and self.target_project_id and 'project_id' in order._fields:
                        update_vals['project_id'] = self.target_project_id.id
                    
                    if update_vals:
                        order.write(update_vals)
                        updated.append(f"PO: {order.name}")
                        
                except Exception as e:
                    _logger.warning(f"Error processing purchase.order {order.id}: {str(e)}")
                    continue
        
        # Process Purchase Order Lines for analytic_distribution
        pol_domain = []
        if self.source_analytic_account_id:
            pol_domain.append(('analytic_distribution', '!=', False))
        
        if pol_domain:
            pol_records = self.env['purchase.order.line'].search(pol_domain)
            for line in pol_records:
                try:
                    if not line.exists():
                        continue
                        
                    if self._update_analytic_distribution(line):
                        line.write({'analytic_distribution': line.analytic_distribution})
                        updated.append(f"PO Line: {line.order_id.name} - {line.name}")
                        
                except Exception as e:
                    _logger.warning(f"Error processing purchase.order.line {line.id}: {str(e)}")
                    continue
        
        return updated

    def _process_account_moves(self):
        """Process Account Moves (Invoices/Bills/Journal Entries)"""
        updated = []
        
        # Account Move Lines - remove project_id filter since it doesn't exist on account.move.line
        domain = []
        if self.source_analytic_account_id:
            domain.append(('analytic_distribution', '!=', False))
        
        aml_records = self.env['account.move.line'].search(domain)
        
        moves_to_repost = set()
        
        for line in aml_records:
            try:
                # Check if record still exists
                if not line.exists():
                    continue
                    
                update_vals = {}
                
                # Remove project_id update since account.move.line doesn't have project_id field
                # Project information is typically handled through analytic distribution
                
                if self._update_analytic_distribution(line):
                    update_vals['analytic_distribution'] = line.analytic_distribution
                
                if update_vals:
                    move = line.move_id
                    
                    # Check if move still exists
                    if not move.exists():
                        continue
                    
                    # Handle posted moves
                    if move.state == 'posted':
                        moves_to_repost.add(move)
                        move.button_draft()
                    
                    line.write(update_vals)
                    updated.append(f"Journal Item: {move.name} - {line.name}")
                    
            except Exception as e:
                _logger.warning(f"Error processing account.move.line {line.id}: {str(e)}")
                continue
        
        # Repost moves
        for move in moves_to_repost:
            try:
                if move.exists():
                    move.action_post()
            except Exception as e:
                _logger.warning(f"Error reposting move {move.name}: {str(e)}")
        
        return updated

    def _process_expenses(self):
        """Process HR Expenses"""
        updated = []
        
        try:
            # Check if analytic_distribution field exists
            if 'analytic_distribution' not in self.env['hr.expense']._fields:
                _logger.error("Field 'analytic_distribution' does not exist in hr.expense model")
                return updated
                
            # HR Expenses - filter by analytic_distribution only
            domain = []
            if self.source_analytic_account_id:
                domain.append(('analytic_distribution', '!=', False))
            
            _logger.info(f"Expense domain: {domain}")
            
            if domain:
                expense_records = self.env['hr.expense'].search(domain)
                _logger.info(f"Found {len(expense_records)} expense records")
                
                # Group expenses by sheet to handle sheet-level operations
                sheets_to_reset = set()
                expenses_to_update = []
                
                for expense in expense_records:
                    try:
                        if not expense.exists():
                            continue
                        
                        _logger.info(f"Processing expense {expense.id}: {expense.name}")
                        _logger.info(f"Current analytic_distribution: {expense.analytic_distribution}")
                        _logger.info(f"Expense state: {expense.state if hasattr(expense, 'state') else 'no state field'}")
                        
                        # Check if expense needs update
                        if self._should_update_expense_analytic(expense):
                            expenses_to_update.append(expense)
                            
                            # If expense has sheet and sheet is not in draft, collect for reset
                            if hasattr(expense, 'sheet_id') and expense.sheet_id:
                                sheet = expense.sheet_id
                                _logger.info(f"Expense sheet {sheet.id} state: {sheet.state}")
                                if sheet.state != 'draft':
                                    sheets_to_reset.add(sheet)
                            elif expense.state != 'draft':
                                _logger.warning(f"Expense {expense.id} is not in draft and has no sheet")
                                
                    except Exception as e:
                        _logger.error(f"Error checking expense {expense.id}: {str(e)}")
                        continue
                
                # Reset expense sheets first
                for sheet in sheets_to_reset:
                    try:
                        _logger.info(f"Resetting expense sheet {sheet.id} to draft")
                        sheet.sudo().action_reset_expense_sheets()
                        _logger.info(f"Successfully reset sheet {sheet.id}")
                    except Exception as e:
                        _logger.error(f"Failed to reset expense sheet {sheet.id}: {str(e)}")
                
                # Now update expenses
                for expense in expenses_to_update:
                    try:
                        if not expense.exists():
                            continue
                            
                        # Double-check state after sheet reset
                        expense.invalidate_recordset()  # Refresh cache
                        current_state = expense.state if hasattr(expense, 'state') else 'unknown'
                        _logger.info(f"Expense {expense.id} state after sheet reset: {current_state}")
                        
                        if self._update_analytic_distribution(expense):
                            _logger.info(f"Updated analytic_distribution: {expense.analytic_distribution}")
                            
                            # Try to update
                            expense.sudo().write({'analytic_distribution': expense.analytic_distribution})
                            updated.append(f"Expense: {expense.name}")
                            _logger.info(f"Successfully updated expense {expense.id}")
                            
                    except Exception as e:
                        _logger.error(f"Error updating expense {expense.id}: {str(e)}")
                        continue
            else:
                _logger.warning("No domain criteria provided for expense processing")
                
        except Exception as e:
            _logger.error(f"Error in _process_expenses: {str(e)}")
        
        return updated

    def _should_update_expense_analytic(self, expense):
        """Check if expense analytic distribution should be updated"""
        if not self.update_analytic or not self.target_analytic_account_id:
            return False
            
        current_distribution = expense.analytic_distribution or {}
        
        if self.source_analytic_account_id:
            # Check if source analytic exists in current distribution
            source_id_str = str(self.source_analytic_account_id.id)
            return source_id_str in current_distribution
        else:
            # Update all distributions
            return bool(current_distribution)

    def _process_expenses_via_sheets(self):
        """Process expenses by handling expense sheets directly"""
        updated = []
        
        try:
            # Find expense sheets that contain expenses with our target analytics
            domain = []
            if self.source_analytic_account_id:
                domain = [
                    ('expense_line_ids.analytic_distribution', '!=', False)
                ]
            
            expense_sheets = self.env['hr.expense.sheet'].search(domain)
            _logger.info(f"Found {len(expense_sheets)} expense sheets to process")
            
            for sheet in expense_sheets:
                try:
                    _logger.info(f"Processing expense sheet {sheet.id}: {sheet.name}")
                    _logger.info(f"Sheet state: {sheet.state}")
                    
                    # Reset sheet to draft if needed
                    if sheet.state != 'draft':
                        sheet.sudo().action_reset_expense_sheets()
                        _logger.info(f"Reset sheet {sheet.id} to draft")
                    
                    # Process expenses in this sheet
                    relevant_expenses = sheet.expense_line_ids.filtered(
                        lambda exp: exp.analytic_distribution and 
                        (not self.source_analytic_account_id or 
                        str(self.source_analytic_account_id.id) in exp.analytic_distribution)
                    )
                    
                    for expense in relevant_expenses:
                        try:
                            if self._update_analytic_distribution(expense):
                                expense.sudo().write({'analytic_distribution': expense.analytic_distribution})
                                updated.append(f"Expense: {expense.name} (via sheet {sheet.name})")
                                _logger.info(f"Updated expense {expense.id} via sheet")
                        except Exception as exp_error:
                            _logger.error(f"Error updating expense {expense.id} in sheet: {str(exp_error)}")
                            
                except Exception as sheet_error:
                    _logger.error(f"Error processing sheet {sheet.id}: {str(sheet_error)}")
                    continue
                    
        except Exception as e:
            _logger.error(f"Error in _process_expenses_via_sheets: {str(e)}")
        
        return updated

    def _process_expenses_alternative(self):
        """Alternative method to process expenses by temporarily changing state"""
        updated = []
        
        try:
            domain = []
            if self.source_analytic_account_id:
                domain.append(('analytic_distribution', '!=', False))
            
            if domain:
                # Search for expenses with specific states that can be modified
                expense_domain = domain + [('state', 'in', ['draft', 'reported'])]
                expense_records = self.env['hr.expense'].search(expense_domain)
                
                for expense in expense_records:
                    try:
                        if not expense.exists():
                            continue
                        
                        original_state = expense.state
                        
                        # If not in draft, try to reset to draft temporarily
                        if expense.state != 'draft':
                            try:
                                expense.sudo().action_reset_expense_sheets()  # Reset to draft
                                _logger.info(f"Reset expense {expense.id} to draft state")
                            except:
                                _logger.warning(f"Cannot reset expense {expense.id} to draft")
                                continue
                        
                        # Now try to update
                        if self._update_analytic_distribution(expense):
                            expense.sudo().write({'analytic_distribution': expense.analytic_distribution})
                            updated.append(f"Expense: {expense.name}")
                            _logger.info(f"Successfully updated expense {expense.id}")
                        
                    except Exception as e:
                        _logger.error(f"Error in alternative expense processing {expense.id}: {str(e)}")
                        continue
        
        except Exception as e:
            _logger.error(f"Error in _process_expenses_alternative: {str(e)}")
        
        return updated

    def _process_stock_moves(self):
        """Process Stock Moves, Delivery Orders, and Receipts"""
        updated = []
        
        # Process Stock Picking (DO/Receipt) with custom project_id field
        picking_domain = []
        if self.source_project_id and 'project_id' in self.env['stock.picking']._fields:
            picking_domain.append(('project_id', '=', self.source_project_id.id))
        
        if picking_domain:
            picking_records = self.env['stock.picking'].search(picking_domain)
            for picking in picking_records:
                try:
                    if not picking.exists():
                        continue
                        
                    update_vals = {}
                    
                    if self.update_project and self.target_project_id:
                        update_vals['project_id'] = self.target_project_id.id
                    
                    if update_vals:
                        picking.write(update_vals)
                        updated.append(f"DO/Receipt: {picking.name}")
                        
                except Exception as e:
                    _logger.warning(f"Error processing stock.picking {picking.id}: {str(e)}")
                    continue
        
        # Process Stock Move Lines with analytic distribution
        sml_domain = []
        if self.source_analytic_account_id:
            sml_domain.append(('analytic_distribution', '!=', False))
        
        if sml_domain:
            sml_records = self.env['stock.move.line'].search(sml_domain)
            for line in sml_records:
                try:
                    if not line.exists():
                        continue
                        
                    if self._update_analytic_distribution(line):
                        line.write({'analytic_distribution': line.analytic_distribution})
                        updated.append(f"Stock Move Line: {line.move_id.name} - {line.product_id.name}")
                        
                except Exception as e:
                    _logger.warning(f"Error processing stock.move.line {line.id}: {str(e)}")
                    continue
        
        # Process Stock Moves with analytic distribution
        sm_domain = []
        if self.source_analytic_account_id and 'analytic_distribution' in self.env['stock.move']._fields:
            sm_domain.append(('analytic_distribution', '!=', False))
        
        if sm_domain:
            sm_records = self.env['stock.move'].search(sm_domain)
            for move in sm_records:
                try:
                    if not move.exists():
                        continue
                        
                    if self._update_analytic_distribution(move):
                        move.write({'analytic_distribution': move.analytic_distribution})
                        updated.append(f"Stock Move: {move.name} - {move.product_id.name}")
                        
                except Exception as e:
                    _logger.warning(f"Error processing stock.move {move.id}: {str(e)}")
                    continue
        
        return updated