from collections import defaultdict
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, format_list


class StockValuationLayerRevaluation(models.TransientModel):
    _inherit = 'stock.valuation.layer.revaluation'

    # Field baru untuk menyimpan layer yang dipilih beserta quantity yang akan di-revaluasi
    selected_layer_ids = fields.One2many(
        'stock.valuation.layer.revaluation.line', 
        'revaluation_id', 
        string="Selected Layers"
    )
    
    # Field untuk menunjukkan mode revaluasi
    revaluation_mode = fields.Selection([
        ('full', 'Full Revaluation (All Layers)'),
        ('partial', 'Revaluation (Selected Layers Only)')
    ], string="Revaluation Mode", default='full')

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        context = self.env.context
        
        # Jika dipanggil dari selected layers di list view
        if context.get('active_model') == 'stock.valuation.layer' and context.get('active_ids'):
            active_ids = context.get('active_ids')
            layers = self.env['stock.valuation.layer'].browse(active_ids).exists()
            
            # Set mode ke partial jika ada layer yang dipilih
            if layers:
                res['revaluation_mode'] = 'partial'
                
                # Buat line untuk setiap layer yang dipilih
                selected_lines = []
                for layer in layers:
                    if layer.remaining_qty > 0:
                        selected_lines.append((0, 0, {
                            'layer_id': layer.id,
                            'original_qty': layer.remaining_qty,
                            'selected_qty': layer.remaining_qty,  # Default semua quantity
                            'original_value': layer.remaining_value,
                        }))
                
                res['selected_layer_ids'] = selected_lines
        
        return res

    @api.depends('selected_layer_ids', 'selected_layer_ids.selected_qty', 'selected_layer_ids.original_value')
    def _compute_current_value_svl(self):
        """Override untuk menghitung berdasarkan selected layers jika mode partial"""
        for reval in self:
            if reval.revaluation_mode == 'partial' and reval.selected_layer_ids:
                # Hitung berdasarkan selected layers
                total_qty = sum(line.selected_qty for line in reval.selected_layer_ids)
                total_value = sum(
                    line.original_value * (line.selected_qty / line.original_qty) 
                    if line.original_qty > 0 else 0
                    for line in reval.selected_layer_ids
                )
                
                reval.current_quantity_svl = total_qty
                reval.current_value_svl = total_value
            else:
                # Gunakan logika standard
                super(StockValuationLayerRevaluation, reval)._compute_current_value_svl()

    def action_validate_revaluation(self):
        """Override untuk mendukung partial revaluation"""
        self.ensure_one()
        
        if self.revaluation_mode == 'partial':
            return self._validate_partial_revaluation()
        else:
            return super().action_validate_revaluation()

    def _validate_partial_revaluation(self):
        """Validasi revaluasi untuk layer yang dipilih saja"""
        if self.currency_id.is_zero(self.added_value):
            raise UserError(_("The added value doesn't have any impact on the stock valuation"))
        
        if not self.selected_layer_ids:
            raise UserError(_("No layers selected for revaluation"))

        product_id = self.product_id.with_company(self.company_id)
        
        # Validasi selected quantities
        for line in self.selected_layer_ids:
            if line.selected_qty <= 0:
                raise UserError(_("Selected quantity must be greater than 0 for layer %s") % line.layer_id.reference)
            if line.selected_qty > line.original_qty:
                raise UserError(_("Selected quantity cannot exceed original quantity for layer %s") % line.layer_id.reference)

        description = _("Reason Manual Stock Valuation: %s.", self.reason or _("No Reason Given"))
        
        # Hitung total selected quantity
        total_selected_qty = sum(line.selected_qty for line in self.selected_layer_ids)
        
        # Update standard price proportionally
        cost_method = product_id.categ_id.property_cost_method
        if cost_method in ['average', 'fifo']:
            previous_cost = product_id.standard_price
            # Update standard price berdasarkan proporsi dari total quantity
            if product_id.quantity_svl > 0:
                proportion = total_selected_qty / product_id.quantity_svl
                product_id.with_context(disable_auto_svl=True).standard_price += (self.added_value / product_id.quantity_svl)
                
                # description += _(
                #     " Product cost updated from %(previous)s to %(new_cost)s (partial update).",
                #     previous=previous_cost,
                #     new_cost=product_id.standard_price
                # )

        # Buat revaluation SVL
        revaluation_svl_vals = {
            'company_id': self.company_id.id,
            'product_id': product_id.id,
            'description': description,
            'value': self.added_value,
            'quantity': 0,
        }

        # Distribute added value ke selected layers
        remaining_value = self.added_value
        total_weight = sum(line.selected_qty for line in self.selected_layer_ids)
        
        for i, line in enumerate(self.selected_layer_ids):
            layer = line.layer_id
            selected_ratio = line.selected_qty / line.original_qty
            
            # Hitung nilai yang akan ditambahkan ke layer ini
            if i == len(self.selected_layer_ids) - 1:  # Layer terakhir
                layer_added_value = remaining_value
            else:
                layer_added_value = self.currency_id.round(
                    self.added_value * (line.selected_qty / total_weight)
                )
            
            # Hitung perubahan nilai per unit quantity
            value_per_unit = layer_added_value / line.selected_qty if line.selected_qty > 0 else 0
            
            # Update remaining value dari layer
            # Hanya update proporsi dari remaining value
            current_value_to_update = layer.remaining_value * selected_ratio
            new_layer_value = current_value_to_update + layer_added_value
            
            if new_layer_value < 0:
                raise UserError(_('The value of a stock valuation layer cannot be negative. Layer: %s') % layer.reference)
            
            # Update layer value (proportional)
            layer.remaining_value += layer_added_value
            remaining_value -= layer_added_value

        # Buat stock valuation layer untuk revaluasi
        revaluation_svl = self.env['stock.valuation.layer'].create(revaluation_svl_vals)
        
        # Buat journal entry jika real-time valuation
        if self.property_valuation == 'real_time':
            self._create_account_move_partial(revaluation_svl, product_id, description)
        
        return True

    def _create_account_move_partial(self, revaluation_svl, product_id, description):
        """Buat journal entry untuk partial revaluation"""
        accounts = product_id.product_tmpl_id.get_product_accounts()
        
        if self.added_value < 0:
            debit_account_id = self.account_id.id
            credit_account_id = accounts.get('stock_valuation') and accounts['stock_valuation'].id
        else:
            debit_account_id = accounts.get('stock_valuation') and accounts['stock_valuation'].id
            credit_account_id = self.account_id.id

        # Buat deskripsi yang lebih detail
        layer_descriptions = []
        for line in self.selected_layer_ids:
            layer_descriptions.append(
                f"{line.layer_id.reference} (Qty: {line.selected_qty}/{line.original_qty})"
            )

        move_description = _(
            '%(user)s changed stock valuation - %(product)s\n'
            '%(reason)s\n',
            # 'Selected layers: %(layers)s',
            user=self.env.user.name,
            product=product_id.display_name,
            reason=description,
            # layers=', '.join(layer_descriptions)
        )

        move_description = _(
            '%(user)s changed stock valuation - %(product)s\n'
            '%(reason)s\n',
            # 'Selected layers: %(layers)s',
            user=self.env.user.name,
            product=product_id.display_name,
            reason=description,
            # layers=', '.join(layer_descriptions)
        )

        move_vals = {
            'journal_id': self.account_journal_id.id or accounts['stock_journal'].id,
            'company_id': self.company_id.id,
            'ref': _("Revaluation of %s", product_id.display_name),
            'stock_valuation_layer_ids': [(6, None, [revaluation_svl.id])],
            'date': self.date or fields.Date.today(),
            'move_type': 'entry',
            'line_ids': [(0, 0, {
                'name': move_description,
                'account_id': debit_account_id,
                'debit': abs(self.added_value),
                'credit': 0,
                'product_id': product_id.id,
            }), (0, 0, {
                'name': move_description,
                'account_id': credit_account_id,
                'debit': 0,
                'credit': abs(self.added_value),
                'product_id': product_id.id,
            })],
        }
        
        account_move = self.env['account.move'].create(move_vals)
        account_move._post()


class StockValuationLayerRevaluationLine(models.TransientModel):
    _name = 'stock.valuation.layer.revaluation.line'
    _description = 'Stock Valuation Layer Revaluation Line'

    revaluation_id = fields.Many2one(
        'stock.valuation.layer.revaluation', 
        string='Revaluation', 
        required=True, 
        ondelete='cascade'
    )
    layer_id = fields.Many2one(
        'stock.valuation.layer', 
        string='Valuation Layer', 
        required=True
    )
    
    # Display fields dari layer
    reference = fields.Char(related='layer_id.reference', string='Reference')
    product_id = fields.Many2one(related='layer_id.product_id', string='Product')
    lot_id = fields.Many2one(related='layer_id.lot_id', string='Lot/Serial')
    
    # Quantity fields
    original_qty = fields.Float(string='Original Qty', readonly=True)
    selected_qty = fields.Float(string='Selected Qty', required=True)
    
    # Value fields
    original_value = fields.Float(string='Original Value', readonly=True)
    value_per_unit = fields.Float(string='Value per Unit', compute='_compute_value_per_unit')
    selected_value = fields.Float(string='Selected Value', compute='_compute_selected_value')
    
    @api.depends('original_value', 'original_qty')
    def _compute_value_per_unit(self):
        for line in self:
            line.value_per_unit = line.original_value / line.original_qty if line.original_qty > 0 else 0
    
    @api.depends('selected_qty', 'value_per_unit')
    def _compute_selected_value(self):
        for line in self:
            line.selected_value = line.selected_qty * line.value_per_unit
    
    @api.constrains('selected_qty', 'original_qty')
    def _check_selected_qty(self):
        for line in self:
            if line.selected_qty <= 0:
                raise UserError(_("Selected quantity must be greater than 0"))
            if line.selected_qty > line.original_qty:
                raise UserError(_("Selected quantity cannot exceed original quantity"))