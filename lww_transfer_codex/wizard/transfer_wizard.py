import json
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LwwTransferWizard(models.TransientModel):
    _name = 'lww.transfer.wizard'
    _description = 'LWW Transfer Codex Wizard'

    company_id = fields.Many2one('res.company', required=True, default=lambda s: s.env.company)

    # toggles
    update_project = fields.Boolean('Update Project', default=True)
    update_analytic = fields.Boolean('Update Analytic', default=True)

    # source filters
    source_project_id = fields.Many2one('project.project', domain="[('company_id','=',company_id)]")
    source_analytic_id = fields.Many2one('account.analytic.account', domain="[('company_id','=',company_id)]")

    # targets
    target_project_id = fields.Many2one('project.project', domain="[('company_id','=',company_id)]")
    target_analytic_id = fields.Many2one('account.analytic.account', domain="[('company_id','=',company_id)]")

    state = fields.Selection([('draft','Draft'),('done','Done')], default='draft')
    log_message = fields.Html(readonly=True)

    # document type switches
    process_sales = fields.Boolean('Sales Orders', default=True)
    process_purchase = fields.Boolean('Purchase Orders', default=True)
    process_invoices = fields.Boolean('Invoices/Bills/Journal Entries', default=True)
    process_expenses = fields.Boolean('Expenses', default=True)
    process_stock = fields.Boolean('Stock Moves/Deliveries', default=True)

    # helpers
    def _dist_has_source(self, distribution):
        if not self.source_analytic_id:
            return False
        try:
            dist = json.loads(distribution) if isinstance(distribution, str) else (distribution or {})
        except Exception:
            dist = {}
        if not isinstance(dist, dict):
            return False
        sid = self.source_analytic_id.id
        return (str(sid) in dist) or (sid in dist)

    def _update_distribution(self, distribution):
        # normalize
        if not distribution:
            base = {}
        else:
            try:
                base = json.loads(distribution) if isinstance(distribution, str) else distribution
                if not isinstance(base, dict):
                    base = {}
            except Exception:
                base = {}
        base = {str(k): v for k, v in base.items()}

        if self.source_analytic_id:
            sid = str(self.source_analytic_id.id)
            if sid in base:
                pct = base[sid]
                base.pop(sid, None)
                base[str(self.target_analytic_id.id)] = pct
        else:
            total = sum(base.values()) if base else 100.0
            base = {str(self.target_analytic_id.id): total}
        return base

    @api.onchange('target_project_id', 'update_project', 'update_analytic')
    def _onchange_sync_target_analytic(self):
        for w in self:
            if w.update_project and w.update_analytic and w.target_project_id:
                aa = getattr(w.target_project_id, 'analytic_account_id', False)
                if aa:
                    w.target_analytic_id = aa.id

    def _validate(self):
        if not (self.update_project or self.update_analytic):
            raise UserError(_('Select at least one update option.'))
        if self.update_project and not self.target_project_id:
            raise UserError(_('Target Project is required.'))
        if self.update_analytic and not self.target_analytic_id:
            # try autofill from project
            if self.update_project and self.target_project_id and getattr(self.target_project_id, 'analytic_account_id', False):
                self.target_analytic_id = self.target_project_id.analytic_account_id
            if not self.target_analytic_id:
                raise UserError(_('Target Analytic Account is required.'))

    # core execution
    def action_execute(self):
        self.ensure_one()
        self._validate()

        logs = []
        total_ok = 0
        total_err = 0

        # 1) Sales Orders
        if self.process_sales:
            try:
                ok = 0
                err = 0
                dom = [('company_id', '=', self.company_id.id)]
                orders_to_process = set()
                if self.source_project_id:
                    orders_to_process.update(self.env['sale.order'].sudo().search(dom + [('project_id', '=', self.source_project_id.id)]).ids if 'project_id' in self.env['sale.order']._fields else [])
                if self.source_analytic_id:
                    line_dom = [('order_id.company_id', '=', self.company_id.id)]
                    line_dom.append(('analytic_distribution', 'ilike', '"%s"' % self.source_analytic_id.id))
                    orders_to_process.update(self.env['sale.order.line'].sudo().search(line_dom).mapped('order_id').ids)
                if not self.source_project_id and not self.source_analytic_id:
                    orders_to_process.update(self.env['sale.order'].sudo().search(dom).ids)
                for so in self.env['sale.order'].sudo().browse(list(orders_to_process)):
                    try:
                        if hasattr(so, 'action_unlock'):
                            try:
                                so.sudo().action_unlock()
                            except Exception:
                                pass
                        if self.update_project and 'project_id' in so._fields:
                            if not self.source_project_id or so.project_id == self.source_project_id:
                                so.sudo().project_id = self.target_project_id
                        if self.update_analytic:
                            for ln in so.order_line:
                                if self.source_analytic_id and not self._dist_has_source(ln.analytic_distribution):
                                    continue
                                if 'analytic_distribution' in ln._fields:
                                    ln.sudo().analytic_distribution = self._update_distribution(ln.analytic_distribution)
                        ok += 1
                    except Exception as e:
                        err += 1
                        _logger.exception('SO %s update failed: %s', so.name, e)
                logs.append(_('<p>Sales Orders: %s OK, %s errors</p>') % (ok, err))
            except Exception as e:
                logs.append(_('<p style="color:red;">Sales Orders fatal: %s</p>') % e)

        # 2) Purchase Orders
        if self.process_purchase:
            try:
                ok = 0
                err = 0
                dom = [('company_id', '=', self.company_id.id)]
                orders_to_process = set()
                if self.source_project_id:
                    orders_to_process.update(self.env['purchase.order'].sudo().search(dom + [('project_id', '=', self.source_project_id.id)]).ids if 'project_id' in self.env['purchase.order']._fields else [])
                if self.source_analytic_id:
                    line_dom = [('order_id.company_id', '=', self.company_id.id)]
                    line_dom.append(('analytic_distribution', 'ilike', '"%s"' % self.source_analytic_id.id))
                    orders_to_process.update(self.env['purchase.order.line'].sudo().search(line_dom).mapped('order_id').ids)
                if not self.source_project_id and not self.source_analytic_id:
                    orders_to_process.update(self.env['purchase.order'].sudo().search(dom).ids)
                for po in self.env['purchase.order'].sudo().browse(list(orders_to_process)):
                    try:
                        if hasattr(po, 'button_unlock'):
                            try:
                                po.sudo().button_unlock()
                            except Exception:
                                pass
                        if self.update_project and 'project_id' in po._fields:
                            if not self.source_project_id or po.project_id == self.source_project_id:
                                po.sudo().project_id = self.target_project_id
                        if self.update_analytic:
                            for ln in po.order_line:
                                if self.source_analytic_id and not self._dist_has_source(ln.analytic_distribution):
                                    continue
                                if 'analytic_distribution' in ln._fields:
                                    ln.sudo().analytic_distribution = self._update_distribution(ln.analytic_distribution)
                        ok += 1
                    except Exception as e:
                        err += 1
                        _logger.exception('PO %s update failed: %s', po.name, e)
                logs.append(_('<p>Purchase Orders: %s OK, %s errors</p>') % (ok, err))
            except Exception as e:
                logs.append(_('<p style="color:red;">Purchase Orders fatal: %s</p>') % e)

        # 3) Account Moves (Invoices/Bills/JE)
        if self.process_invoices:
            try:
                dom = [('company_id', '=', self.company_id.id)]
                moves = self.env['account.move'].sudo().search(dom)
                for mv in moves:
                    try:
                        # Unpost when needed and any change will be applied
                        will_change = False
                        if self.update_project and (not self.source_project_id or mv.project_id == self.source_project_id):
                            will_change = True
                        if self.update_analytic:
                            for ln in mv.line_ids:
                                if getattr(ln, 'display_type', False):
                                    continue
                                # Respect non-analytic accounts if detectable
                                try:
                                    if ln.account_id and hasattr(ln.account_id, 'analytic') and not ln.account_id.analytic:
                                        continue
                                except Exception:
                                    pass
                                if self.source_analytic_id:
                                    if self._dist_has_source(ln.analytic_distribution):
                                        will_change = True
                                        break
                                else:
                                    will_change = True
                                    break

                        was_posted = (mv.state == 'posted')
                        if was_posted and will_change:
                            mv.sudo().button_draft()

                        if self.update_project and (not self.source_project_id or mv.project_id == self.source_project_id):
                            mv.sudo().project_id = self.target_project_id

                        if self.update_analytic:
                            for ln in mv.line_ids:
                                if getattr(ln, 'display_type', False):
                                    continue
                                try:
                                    if ln.account_id and hasattr(ln.account_id, 'analytic') and not ln.account_id.analytic:
                                        continue
                                except Exception:
                                    pass
                                if self.source_analytic_id and not self._dist_has_source(ln.analytic_distribution):
                                    continue
                                ln.sudo().analytic_distribution = self._update_distribution(ln.analytic_distribution)

                        if was_posted and will_change:
                            mv.sudo().action_post()
                        total_ok += 1
                    except Exception as e:
                        total_err += 1
                        _logger.exception('Move %s update failed: %s', mv.name, e)
                logs.append(_('<p>Account Moves: %s OK, %s errors</p>') % (total_ok, total_err))
            except Exception as e:
                logs.append(_('<p style="color:red;">Account Moves fatal: %s</p>') % e)

        # 4) Stock Moves and Move Lines (including done)
        if self.process_stock:
            try:
                ok = 0
                err = 0
                dom = [('company_id', '=', self.company_id.id)]
                # If source project filter is given and picking has project_id, use it
                if self.source_project_id and 'project_id' in self.env['stock.picking']._fields:
                    dom.append(('picking_id.project_id', '=', self.source_project_id.id))
                moves = self.env['stock.move'].sudo().search(dom)
                for mv in moves:
                    try:
                        # Optional: update picking's project when enabled
                        if self.update_project and mv.picking_id and 'project_id' in mv.picking_id._fields:
                            if not self.source_project_id or mv.picking_id.project_id == self.source_project_id:
                                mv.picking_id.sudo().project_id = self.target_project_id
                        if self.update_analytic and 'analytic_distribution' in mv._fields:
                            if self.source_analytic_id:
                                if self._dist_has_source(mv.analytic_distribution):
                                    mv.sudo().analytic_distribution = self._update_distribution(mv.analytic_distribution)
                            else:
                                mv.sudo().analytic_distribution = self._update_distribution(mv.analytic_distribution)
                        # move lines
                        for ml in mv.move_line_ids:
                            if 'analytic_distribution' not in ml._fields:
                                continue
                            if self.update_analytic:
                                if self.source_analytic_id and not self._dist_has_source(ml.analytic_distribution):
                                    continue
                                ml.sudo().analytic_distribution = self._update_distribution(ml.analytic_distribution)
                        ok += 1
                    except Exception as e:
                        err += 1
                        _logger.exception('Stock Move %s update failed: %s', mv.name, e)
                logs.append(_('<p>Stock Moves: %s OK, %s errors</p>') % (ok, err))
            except Exception as e:
                logs.append(_('<p style="color:red;">Stock Moves fatal: %s</p>') % e)

        # 5) Expenses
        if self.process_expenses:
            try:
                ok = 0
                err = 0
                dom = [('company_id', '=', self.company_id.id)]
                if self.source_analytic_id:
                    dom.append(('analytic_distribution', 'ilike', '"%s"' % self.source_analytic_id.id))
                expenses = self.env['hr.expense'].sudo().search(dom)
                for ex in expenses:
                    try:
                        if self.update_analytic:
                            if self.source_analytic_id and not self._dist_has_source(ex.analytic_distribution):
                                continue
                            ex.sudo().analytic_distribution = self._update_distribution(ex.analytic_distribution)
                        ok += 1
                    except Exception as e:
                        err += 1
                        _logger.exception('Expense %s update failed: %s', ex.name, e)
                logs.append(_('<p>Expenses: %s OK, %s errors</p>') % (ok, err))
            except Exception as e:
                logs.append(_('<p style="color:red;">Expenses fatal: %s</p>') % e)

        self.state = 'done'
        self.log_message = ''.join(logs)
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
