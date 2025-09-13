import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectAnalyticTransferWizard(models.TransientModel):
    _name = 'project.analytic.transfer.wizard'
    _description = 'Project & Analytic Transfer Wizard'

    # Company & Basic Info
    company_id = fields.Many2one('res.company', 'Company', required=True, 
                                default=lambda self: self.env.company)
    
    # Source Fields
    source_project_id = fields.Many2one('project.project', 'Source Project',
                                       domain="[('company_id', '=', company_id)]")
    source_analytic_id = fields.Many2one('account.analytic.account', 'Source Analytic Account',
                                        domain="[('company_id', '=', company_id)]")
    
    # Update Options
    update_project = fields.Boolean('Update Project', default=True)
    update_analytic = fields.Boolean('Update Analytic', default=True)

    # Target Fields  
    target_project_id = fields.Many2one('project.project', 'Target Project',
                                       domain="[('company_id', '=', company_id)]")
    target_analytic_id = fields.Many2one('account.analytic.account', 'Target Analytic Account',
                                        domain="[('company_id', '=', company_id)]")
    
    # Document Type Selection
    transfer_sales = fields.Boolean('Sales Orders', default=True)
    transfer_purchase = fields.Boolean('Purchase Orders', default=True)
    transfer_invoices = fields.Boolean('Invoices/Bills/Journal Entries', default=True)
    transfer_expenses = fields.Boolean('Expenses', default=True)
    transfer_stock = fields.Boolean('Stock Moves/Receipts/Deliveries', default=True)
    
    # Date filters removed per requirements
    
    # Results
    state = fields.Selection([
        ('draft', 'Draft'),
        ('progress', 'In Progress'),
        ('done', 'Completed')
    ], default='draft')
    
    log_message = fields.Html('Transfer Log', readonly=True)

    def _get_project_default_analytic(self, project):
        """Return default analytic account for a given project, if any."""
        if not project:
            return False
        project = project.sudo()
        if 'analytic_account_id' in project._fields and project.analytic_account_id:
            return project.analytic_account_id
        return False

    @api.onchange('target_project_id', 'update_project', 'update_analytic')
    def _onchange_target_project_sync_analytic(self):
        for wizard in self:
            if wizard.update_project and wizard.update_analytic and wizard.target_project_id:
                analytic = wizard._get_project_default_analytic(wizard.target_project_id)
                if analytic:
                    wizard.target_analytic_id = analytic.id if hasattr(analytic, 'id') else analytic
    
    @api.constrains('source_project_id', 'target_project_id', 'source_analytic_id', 'target_analytic_id', 'update_project', 'update_analytic')
    def _check_source_target_different(self):
        for record in self:
            if record.update_project and record.source_project_id and record.source_project_id == record.target_project_id:
                raise ValidationError(_("Source and target project must be different when updating project."))
            if record.update_analytic and record.source_analytic_id and record.source_analytic_id == record.target_analytic_id:
                raise ValidationError(_("Source and target analytic account must be different when updating analytics."))
    
    def action_preview_records(self):
        """Preview affected records count"""
        self.ensure_one()
        
        # Get counts for each document type
        counts = {}
        if self.transfer_sales:
            counts['sales'] = self._get_sales_orders_count()
        if self.transfer_purchase:
            counts['purchase'] = self._get_purchase_orders_count()
        if self.transfer_invoices:
            counts['invoices'] = self._get_account_moves_count()
        if self.transfer_expenses:
            counts['expenses'] = self._get_expenses_count()
        if self.transfer_stock:
            counts['stock'] = self._get_stock_moves_count()
            
        total = sum(counts.values())
        
        message = f"<h4>Records to be transferred:</h4><ul>"
        for doc_type, count in counts.items():
            if count > 0:
                message += f"<li><b>{doc_type.title()}:</b> {count} records</li>"
        message += f"</ul><p><b>Total: {total} records</b></p>"
        
        if total == 0:
            raise UserError(_("No records found matching the criteria."))
            
        self.log_message = message
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.analytic.transfer.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'show_preview': True}
        }
    
    def action_execute_transfer(self):
        """Execute the transfer process"""
        self.ensure_one()
        # Auto-fill target analytic from project when both updates are enabled
        if self.update_project and self.update_analytic and self.target_project_id and not self.target_analytic_id:
            proj_aa = self._get_project_default_analytic(self.target_project_id)
            if proj_aa:
                self.target_analytic_id = proj_aa
        # Require relevant targets based on switches
        if not (self.update_project or self.update_analytic):
            raise UserError(_("Select at least one update option: Update Project or Update Analytic."))
        if self.update_project and not self.target_project_id:
            raise UserError(_("Target Project is required when Update Project is enabled."))
        if self.update_analytic and not self.target_analytic_id:
            raise UserError(_("Target Analytic Account is required when Update Analytic is enabled."))
        self.state = 'progress'
        
        log_messages = ["<h4>Transfer Process Started</h4>"]
        total_transferred = 0
        total_errors = 0
        
        try:
            # Transfer Sales Orders
            if self.transfer_sales:
                success, errors, msg = self._transfer_sales_orders()
                total_transferred += success
                total_errors += errors
                log_messages.append(msg)
            
            # Transfer Purchase Orders  
            if self.transfer_purchase:
                success, errors, msg = self._transfer_purchase_orders()
                total_transferred += success
                total_errors += errors
                log_messages.append(msg)
            
            # Transfer Account Moves
            if self.transfer_invoices:
                success, errors, msg = self._transfer_account_moves()
                total_transferred += success
                total_errors += errors
                log_messages.append(msg)
            
            # Transfer Expenses
            if self.transfer_expenses:
                success, errors, msg = self._transfer_expenses()
                total_transferred += success
                total_errors += errors
                log_messages.append(msg)
            
            # Transfer Stock Moves
            if self.transfer_stock:
                success, errors, msg = self._transfer_stock_moves()
                total_transferred += success
                total_errors += errors
                log_messages.append(msg)
            
            # Summary
            summary = f"""
            <h4>Transfer Summary</h4>
            <p><b>Total Records Transferred:</b> {total_transferred}</p>
            <p><b>Total Errors:</b> {total_errors}</p>
            <p><b>Status:</b> {'Completed with errors' if total_errors > 0 else 'Successfully Completed'}</p>
            """
            log_messages.append(summary)
            
        except Exception as e:
            log_messages.append(f"<p style='color: red;'><b>Fatal Error:</b> {str(e)}</p>")
            _logger.error(f"Transfer failed: {str(e)}")
        
        self.log_message = ''.join(log_messages)
        self.state = 'done'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.analytic.transfer.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def _get_base_domain(self):
        """Base domain by company only (no date filters)."""
        return [('company_id', '=', self.company_id.id)]
    
    def _get_project_domain(self, base_domain):
        """Add project filter to domain"""
        if self.source_project_id:
            return base_domain + [('project_id', '=', self.source_project_id.id)]
        return base_domain
    
    def _get_analytic_domain(self, base_domain):
        """Add analytic filter to domain"""
        if self.source_analytic_id:
            return base_domain + [('analytic_distribution', 'ilike', f'"{self.source_analytic_id.id}"')]
        return base_domain
    
    def _update_analytic_distribution(self, distribution_json):
        """Update analytic distribution JSON"""
        if not distribution_json:
            return {str(self.target_analytic_id.id): 100.0}

        try:
            distribution = json.loads(distribution_json) if isinstance(distribution_json, str) else distribution_json
            if not isinstance(distribution, dict):
                distribution = {}
            # Normalize keys to str to be consistent across sources that may use int keys
            distribution = {str(k): v for k, v in distribution.items()}
            
            # If source analytic is specified, replace only that one
            if self.source_analytic_id:
                source_id_str = str(self.source_analytic_id.id)
                if source_id_str in distribution:
                    percentage = distribution[source_id_str]
                    del distribution[source_id_str]
                    distribution[str(self.target_analytic_id.id)] = percentage
            else:
                # Replace all analytics with target analytic
                total_percentage = sum(distribution.values())
                distribution = {str(self.target_analytic_id.id): total_percentage}
                
            return distribution
        except Exception as e:
            _logger.error(f"Error updating analytic distribution: {str(e)}")
            return {str(self.target_analytic_id.id): 100.0}

    def _dist_has_source(self, distribution):
        """Check if given distribution contains the source analytic (handles int/str keys)."""
        if not self.source_analytic_id:
            return False
        try:
            dist = json.loads(distribution) if isinstance(distribution, str) else distribution or {}
        except Exception:
            dist = {}
        if not isinstance(dist, dict):
            return False
        sid = self.source_analytic_id.id
        return (str(sid) in dist) or (sid in dist)
    
    # Count Methods
    def _get_sales_orders_count(self):
        domain = self._get_base_domain()
        orders_set = set()
        if self.source_project_id:
            project_orders = self.env['sale.order'].search(domain + [('project_id', '=', self.source_project_id.id)])
            orders_set.update(project_orders.ids)
        if self.source_analytic_id:
            lines_domain = [('order_id.company_id', '=', self.company_id.id),
                            ('analytic_distribution', 'ilike', f'"{self.source_analytic_id.id}"')]
            line_orders = self.env['sale.order.line'].search(lines_domain).mapped('order_id')
            orders_set.update(line_orders.ids)
        if not self.source_project_id and not self.source_analytic_id:
            orders_set.update(self.env['sale.order'].search(domain).ids)
        return len(orders_set)
    
    def _get_purchase_orders_count(self):
        domain = self._get_base_domain()
        orders_set = set()
        if self.source_project_id:
            project_orders = self.env['purchase.order'].search(domain + [('project_id', '=', self.source_project_id.id)])
            orders_set.update(project_orders.ids)
        if self.source_analytic_id:
            lines_domain = [('order_id.company_id', '=', self.company_id.id),
                            ('analytic_distribution', 'ilike', f'"{self.source_analytic_id.id}"')]
            line_orders = self.env['purchase.order.line'].search(lines_domain).mapped('order_id')
            orders_set.update(line_orders.ids)
        if not self.source_project_id and not self.source_analytic_id:
            orders_set.update(self.env['purchase.order'].search(domain).ids)
        return len(orders_set)
    
    def _get_account_moves_count(self):
        domain = self._get_base_domain()
        moves_set = set()
        if self.source_project_id:
            header_moves = self.env['account.move'].search(domain + [('project_id', '=', self.source_project_id.id)])
            moves_set.update(header_moves.ids)
        if self.source_analytic_id:
            lines_domain = [('move_id.company_id', '=', self.company_id.id),
                            ('analytic_distribution', 'ilike', f'"{self.source_analytic_id.id}"')]
            line_moves = self.env['account.move.line'].search(lines_domain).mapped('move_id')
            moves_set.update(line_moves.ids)
        if not self.source_project_id and not self.source_analytic_id:
            moves_set.update(self.env['account.move'].search(domain).ids)
        return len(moves_set)
    
    def _get_expenses_count(self):
        domain = self._get_base_domain()
        if self.source_analytic_id:
            domain.append(('analytic_distribution', 'ilike', f'"{self.source_analytic_id.id}"'))
        return self.env['hr.expense'].search_count(domain)
    
    def _get_stock_moves_count(self):
        domain = self._get_base_domain()
        # Include picking's project when available and field exists
        if self.source_project_id and 'project_id' in self.env['stock.picking']._fields:
            domain.append(('picking_id.project_id', '=', self.source_project_id.id))
        # Keep analytic filter for rough pre-count (actual update logic rechecks precisely)
        if self.source_analytic_id and 'analytic_distribution' in self.env['stock.move']._fields:
            domain.append(('analytic_distribution', 'ilike', f'"{self.source_analytic_id.id}"'))
        return self.env['stock.move'].search_count(domain)
    
    # Transfer Methods
    def _transfer_sales_orders(self):
        """Transfer sales orders"""
        success_count = 0
        error_count = 0
        messages = ["<h5>Sales Orders Transfer:</h5>"]

        try:
            # Find sales orders to transfer
            domain = self._get_base_domain()
            orders_to_transfer = set()

            # From project_id
            if self.source_project_id:
                project_orders = self.env['sale.order'].search(domain + [('project_id', '=', self.source_project_id.id)])
                orders_to_transfer.update(project_orders.ids)

            # From analytic_distribution in lines
            if self.source_analytic_id:
                lines_domain = [('order_id.company_id', '=', self.company_id.id)]
                lines_domain.append(('analytic_distribution', 'ilike', f'"{self.source_analytic_id.id}"'))
                analytic_orders = self.env['sale.order.line'].search(lines_domain).mapped('order_id')
                orders_to_transfer.update(analytic_orders.ids)

            # If no filters provided, process all orders in the company
            if not self.source_project_id and not self.source_analytic_id:
                orders_to_transfer.update(self.env['sale.order'].search(domain).ids)

            orders = self.env['sale.order'].browse(list(orders_to_transfer))

            for order in orders:
                try:
                    # Allow editing if environment enforces locks
                    if hasattr(order, 'action_unlock'):
                        try:
                            order.sudo().action_unlock()
                        except Exception:
                            pass

                    # Update project_id (only when enabled)
                    if self.update_project:
                        if self.source_project_id:
                            if order.project_id == self.source_project_id:
                                order.sudo().project_id = self.target_project_id
                        else:
                            # No source project filter -> set all to target
                            order.sudo().project_id = self.target_project_id

                    # Update analytic_distribution in lines
                    for line in order.order_line:
                        # If a specific source analytic is provided, only update
                        # lines that actually include that source analytic.
                        if self.update_analytic and self.source_analytic_id:
                            if not self._dist_has_source(line.analytic_distribution):
                                continue
                            new_distribution = self._update_analytic_distribution(line.analytic_distribution)
                            line.sudo().analytic_distribution = new_distribution
                        elif self.update_analytic:
                            # No source filter: set/replace distribution to target
                            new_distribution = self._update_analytic_distribution(line.analytic_distribution)
                            line.sudo().analytic_distribution = new_distribution

                    success_count += 1

                except Exception as e:
                    error_count += 1
                    messages.append(f"<p style='color: red;'>Error in Sales Order {order.name}: {str(e)}</p>")
                    _logger.error(f"Error transferring sales order {order.name}: {str(e)}")
            
            messages.append(f"<p>Sales Orders - Success: {success_count}, Errors: {error_count}</p>")
            
        except Exception as e:
            messages.append(f"<p style='color: red;'>Fatal error in Sales Orders: {str(e)}</p>")
            _logger.error(f"Fatal error in sales orders transfer: {str(e)}")
        
        return success_count, error_count, ''.join(messages)
    
    def _transfer_purchase_orders(self):
        """Transfer purchase orders"""
        success_count = 0
        error_count = 0
        messages = ["<h5>Purchase Orders Transfer:</h5>"]

        try:
            domain = self._get_base_domain()
            orders_to_transfer = set()

            # From project_id
            if self.source_project_id:
                project_orders = self.env['purchase.order'].search(domain + [('project_id', '=', self.source_project_id.id)])
                orders_to_transfer.update(project_orders.ids)

            # From analytic_distribution in lines
            if self.source_analytic_id:
                lines_domain = [('order_id.company_id', '=', self.company_id.id)]
                lines_domain.append(('analytic_distribution', 'ilike', f'"{self.source_analytic_id.id}"'))
                analytic_orders = self.env['purchase.order.line'].search(lines_domain).mapped('order_id')
                orders_to_transfer.update(analytic_orders.ids)

            # No filters -> all purchase orders
            if not self.source_project_id and not self.source_analytic_id:
                orders_to_transfer.update(self.env['purchase.order'].search(domain).ids)

            orders = self.env['purchase.order'].browse(list(orders_to_transfer))

            for order in orders:
                try:
                    if hasattr(order, 'button_unlock'):
                        try:
                            order.sudo().button_unlock()
                        except Exception:
                            pass

                    # Update project_id (only when enabled)
                    if self.update_project:
                        if self.source_project_id:
                            if order.project_id == self.source_project_id:
                                order.sudo().project_id = self.target_project_id
                        else:
                            order.sudo().project_id = self.target_project_id

                    # Update analytic_distribution in lines
                    for line in order.order_line:
                        if self.update_analytic and self.source_analytic_id:
                            if not self._dist_has_source(line.analytic_distribution):
                                continue
                            new_distribution = self._update_analytic_distribution(line.analytic_distribution)
                            line.sudo().analytic_distribution = new_distribution
                        elif self.update_analytic:
                            new_distribution = self._update_analytic_distribution(line.analytic_distribution)
                            line.sudo().analytic_distribution = new_distribution

                    success_count += 1

                except Exception as e:
                    error_count += 1
                    messages.append(f"<p style='color: red;'>Error in Purchase Order {order.name}: {str(e)}</p>")
                    _logger.error(f"Error transferring purchase order {order.name}: {str(e)}")
            
            messages.append(f"<p>Purchase Orders - Success: {success_count}, Errors: {error_count}</p>")
            
        except Exception as e:
            messages.append(f"<p style='color: red;'>Fatal error in Purchase Orders: {str(e)}</p>")
            _logger.error(f"Fatal error in purchase orders transfer: {str(e)}")
        
        return success_count, error_count, ''.join(messages)
    
    def _transfer_account_moves(self):
        """Transfer account moves (invoices/bills/journal entries)"""
        success_count = 0
        error_count = 0
        messages = ["<h5>Account Moves Transfer:</h5>"]

        try:
            domain = self._get_base_domain()
            moves_to_transfer = set()

            # From project_id
            if self.source_project_id:
                project_moves = self.env['account.move'].search(domain + [('project_id', '=', self.source_project_id.id)])
                moves_to_transfer.update(project_moves.ids)

            # From analytic_distribution in lines
            if self.source_analytic_id:
                lines_domain = [('move_id.company_id', '=', self.company_id.id)]
                lines_domain.append(('analytic_distribution', 'ilike', f'"{self.source_analytic_id.id}"'))
                analytic_moves = self.env['account.move.line'].search(lines_domain).mapped('move_id')
                moves_to_transfer.update(analytic_moves.ids)

            # No filters -> all moves in company
            if not self.source_project_id and not self.source_analytic_id:
                moves_to_transfer.update(self.env['account.move'].search(domain).ids)

            moves = self.env['account.move'].browse(list(moves_to_transfer))

            for move in moves:
                try:
                    need_repost = move.state == 'posted'
                    
                    if need_repost and (self.update_project or self.update_analytic):
                        move.sudo().button_draft()  # Unpost safely

                    # Update project_id (now writable via inverse)
                    if self.update_project:
                        if self.source_project_id:
                            if move.project_id == self.source_project_id:
                                move.sudo().project_id = self.target_project_id
                        else:
                            move.sudo().project_id = self.target_project_id

                    # Update analytic_distribution in lines
                    for line in move.line_ids:
                        # Skip display lines (sections/notes)
                        if getattr(line, 'display_type', False):
                            continue
                        # Skip accounts that do not allow analytics when detectable
                        try:
                            if line.account_id and hasattr(line.account_id, 'analytic') and not line.account_id.analytic:
                                continue
                        except Exception:
                            pass

                        if self.update_analytic and self.source_analytic_id:
                            if not self._dist_has_source(line.analytic_distribution):
                                # Do not create a new distribution when filtering by source
                                continue
                            new_distribution = self._update_analytic_distribution(line.analytic_distribution)
                            line.sudo().analytic_distribution = new_distribution
                        elif self.update_analytic:
                            new_distribution = self._update_analytic_distribution(line.analytic_distribution)
                            line.sudo().analytic_distribution = new_distribution
                    
                    if need_repost and (self.update_project or self.update_analytic):
                        move.sudo().action_post()  # Repost
                    
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    messages.append(f"<p style='color: red;'>Error in Account Move {move.name}: {str(e)}</p>")
                    _logger.error(f"Error transferring account move {move.name}: {str(e)}")
            
            messages.append(f"<p>Account Moves - Success: {success_count}, Errors: {error_count}</p>")
            
        except Exception as e:
            messages.append(f"<p style='color: red;'>Fatal error in Account Moves: {str(e)}</p>")
            _logger.error(f"Fatal error in account moves transfer: {str(e)}")
        
        return success_count, error_count, ''.join(messages)
    
    def _transfer_expenses(self):
        """Transfer expenses"""
        success_count = 0
        error_count = 0
        messages = ["<h5>Expenses Transfer:</h5>"]

        try:
            domain = self._get_base_domain()
            if self.update_analytic and self.source_analytic_id:
                domain.append(('analytic_distribution', 'ilike', f'"{self.source_analytic_id.id}"'))
            
            expenses = self.env['hr.expense'].sudo().search(domain)
            
            for expense in expenses:
                try:
                    # Update analytic_distribution directly; account moves are handled
                    # separately in the account move transfer step.
                    if self.update_analytic and self.source_analytic_id:
                        if not self._dist_has_source(expense.analytic_distribution):
                            # When filtering by source, only update those containing the source
                            continue
                        new_distribution = self._update_analytic_distribution(expense.analytic_distribution)
                        expense.sudo().analytic_distribution = new_distribution
                    elif self.update_analytic:
                        new_distribution = self._update_analytic_distribution(expense.analytic_distribution)
                        expense.sudo().analytic_distribution = new_distribution
                    
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    messages.append(f"<p style='color: red;'>Error in Expense {expense.name}: {str(e)}</p>")
                    _logger.error(f"Error transferring expense {expense.name}: {str(e)}")
            
            messages.append(f"<p>Expenses - Success: {success_count}, Errors: {error_count}</p>")
            
        except Exception as e:
            messages.append(f"<p style='color: red;'>Fatal error in Expenses: {str(e)}</p>")
            _logger.error(f"Fatal error in expenses transfer: {str(e)}")
        
        return success_count, error_count, ''.join(messages)
    
    def _transfer_stock_moves(self):
        """Transfer stock moves"""
        success_count = 0
        error_count = 0
        messages = ["<h5>Stock Transfers:</h5>"]

        try:
            domain = self._get_base_domain()
            # 1) Update Stock Pickings project_id
            picking_domain = [('company_id', '=', self.company_id.id)]
            if self.source_project_id and 'project_id' in self.env['stock.picking']._fields:
                picking_domain.append(('project_id', '=', self.source_project_id.id))
            pickings = self.env['stock.picking'].sudo().search(picking_domain)
            for picking in pickings:
                try:
                    if self.update_project and 'project_id' in picking._fields:
                        if self.source_project_id:
                            if picking.project_id == self.source_project_id:
                                picking.sudo().project_id = self.target_project_id
                        else:
                            picking.sudo().project_id = self.target_project_id
                        success_count += 1
                except Exception as e:
                    error_count += 1
                    messages.append(f"<p style='color: red;'>Error in Picking {picking.name}: {str(e)}</p>")
                    _logger.error(f"Error updating picking {picking.name}: {str(e)}")

            # 2) Update Stock Moves and Move Lines analytic_distribution (no state changes)
            # Use picking's project to target moves when provided; avoid over-filtering by analytic here.
            if self.source_project_id and 'project_id' in self.env['stock.picking']._fields:
                domain.append(('picking_id.project_id', '=', self.source_project_id.id))
            moves = self.env['stock.move'].sudo().search(domain)

            for move in moves:
                try:
                    # Update analytic_distribution
                    if 'analytic_distribution' in move._fields:
                        if self.update_analytic and self.source_analytic_id:
                            if self._dist_has_source(move.analytic_distribution):
                                new_distribution = self._update_analytic_distribution(move.analytic_distribution)
                                move.sudo().analytic_distribution = new_distribution
                        elif self.update_analytic:
                            new_distribution = self._update_analytic_distribution(move.analytic_distribution)
                            move.sudo().analytic_distribution = new_distribution

                    # Also update stock.move.line if exists
                    for move_line in move.move_line_ids:
                        if 'analytic_distribution' not in move_line._fields:
                            continue
                        if self.update_analytic and self.source_analytic_id:
                            if not self._dist_has_source(move_line.analytic_distribution):
                                continue
                            new_distribution = self._update_analytic_distribution(move_line.analytic_distribution)
                            move_line.sudo().analytic_distribution = new_distribution
                        elif self.update_analytic:
                            new_distribution = self._update_analytic_distribution(move_line.analytic_distribution)
                            move_line.sudo().analytic_distribution = new_distribution

                    success_count += 1

                except Exception as e:
                    error_count += 1
                    messages.append(f"<p style='color: red;'>Error in Stock Move {move.name}: {str(e)}</p>")
                    _logger.error(f"Error transferring stock move {move.name}: {str(e)}")

            messages.append(f"<p>Stock - Success: {success_count}, Errors: {error_count}</p>")
            
        except Exception as e:
            messages.append(f"<p style='color: red;'>Fatal error in Stock Moves: {str(e)}</p>")
            _logger.error(f"Fatal error in stock moves transfer: {str(e)}")
        
        return success_count, error_count, ''.join(messages)
    
    def action_reset(self):
        """Reset wizard to draft state"""
        self.write({
            'state': 'draft',
            'log_message': False,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.analytic.transfer.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
