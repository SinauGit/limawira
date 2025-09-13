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
                updated_records.extend(self._process_expenses())
            
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
        
        # HR Expenses - filter by analytic_distribution only
        domain = []
        if self.source_analytic_account_id:
            domain.append(('analytic_distribution', '!=', False))
        
        if domain:
            expense_records = self.env['hr.expense'].search(domain)
            
            for expense in expense_records:
                try:
                    if not expense.exists():
                        continue
                        
                    if self._update_analytic_distribution(expense):
                        expense.write({'analytic_distribution': expense.analytic_distribution})
                        updated.append(f"Expense: {expense.name}")
                        
                except Exception as e:
                    _logger.warning(f"Error processing hr.expense {expense.id}: {str(e)}")
                    continue
        
        return updated

    def _process_stock_moves(self):
        """Process Stock Moves and Move Lines"""
        updated = []
        
        # Stock Move Lines with analytic
        domain = []
        if self.source_analytic_account_id:
            domain.append(('analytic_distribution', '!=', False))
        
        sml_records = self.env['stock.move.line'].search(domain)
        
        for line in sml_records:
            if self._update_analytic_distribution(line):
                line.write({'analytic_distribution': line.analytic_distribution})
                updated.append(f"Stock Move Line: {line.move_id.name} - {line.product_id.name}")
        
        return updated