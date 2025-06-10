from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    no_po = fields.Char(string='Order Number', store=True, required=True)

    def action_print_report(self):
        company = self.env['res.company'].browse(self.env.company.id)
        
        if company.name == 'PT. LIMAWIRA WISESA' and self.customer_id:
            # Gunakan template jasa jika customer_id tidak kosong
            return self.env.ref('lww_purchase.action_report_lww_po_jasa').report_action(self)
        elif company.name == 'PT. BINA SERVICE' and self.customer_id:
            # Gunakan template jasa jika customer_id tidak kosong
            return self.env.ref('lww_purchase.action_report_bs_po_jasa').report_action(self)
        elif company.name == 'PT. BINA SERVICE':
            return self.env.ref('lww_purchase.action_report_bs_po').report_action(self)
        elif company.name == 'PT. SPARTADUA RIBUJAYA' and self.customer_id:
            # Gunakan template jasa jika customer_id tidak kosong
            return self.env.ref('lww_purchase.action_report_spartadua_po_jasa').report_action(self)
        elif company.name == 'PT. SPARTADUA RIBUJAYA':
            return self.env.ref('lww_purchase.action_report_spartadua_po').report_action(self)
        elif company.name == 'PT. PRATAMA DATAMAKSIMA':
            return self.env.ref('lww_purchase.action_report_pratama_po').report_action(self)
        elif company.name == 'PT. IMADEA MAGKASAMA':
            return self.env.ref('lww_purchase.action_report_imadea_po').report_action(self)
        elif company.name == 'PT. CARITAS LESTARI BAKTI':
            return self.env.ref('lww_purchase.action_report_caritas_po').report_action(self)
        elif company.name == 'PT. SPARINDO ALFA PERSADA':
            return self.env.ref('lww_purchase.action_report_sparindo_po').report_action(self)
        elif company.name == 'PT. WASTU DAYA PRIMA':
            return self.env.ref('lww_purchase.action_report_wastu_po').report_action(self)
        elif company.name == 'PT. AMANERA BERSAMA ABADI':
            return self.env.ref('lww_purchase.action_report_amanera_po').report_action(self)
        else:
            return self.env.ref('lww_purchase.action_report_limawira_po').report_action(self)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'no_po' in vals and vals['no_po']:
                existing_record = self.env['purchase.order'].search([
                    ('no_po', '=', vals['no_po'])
                ], limit=1)
                if existing_record:
                    raise ValidationError('PO already exists!')
        return super().create(vals_list)

    def write(self, vals):
        if 'no_po' in vals and vals['no_po']:
            for record in self:
                existing_record = self.env['purchase.order'].search([
                    ('no_po', '=', vals['no_po']),
                    ('id', '!=', record.id)
                ], limit=1)
                if existing_record:
                    raise ValidationError('PO already exist!')
        return super().write(vals)
    
    def get_print_report_name(self):
        return 'Purchase Order - %s' % (self.no_po)
