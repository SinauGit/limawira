from odoo import models, fields, api, _

class VendorPIC(models.Model):
    _name = 'vendor.pic'
    _description = 'Vendor Person in Charge'
    _order = 'sequence, id'
    
    sequence = fields.Integer(default=10)
    name = fields.Char(
        string='Name',
        required=True,
        help="Full name of the Person in Charge"
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        required=True,
        ondelete='cascade',
        index=True,
        help="The vendor this Person in Charge belongs to"
    )
    
    position = fields.Char(
        string='Position/Title',
        help="Position or job title of the Person in Charge"
    )
    
    department = fields.Char(
        string='Department',
        help="Department the Person in Charge belongs to"
    )
    
    is_primary = fields.Boolean(
        string='Primary Contact',
        default=False,
        help="Mark this PIC as the primary contact for this vendor"
    )
    
    phone = fields.Char(
        string='Phone',
        help="Direct phone number of the Person in Charge"
    )
    
    mobile = fields.Char(
        string='Mobile',
        help="Mobile number of the Person in Charge"
    )
    
    email = fields.Char(
        string='Email',
        help="Email address of the Person in Charge"
    )
    
    notes = fields.Text(
        string='Notes',
        help="Additional notes about the Person in Charge"
    )
    
    active = fields.Boolean(default=True)
    
    @api.model
    def create(self, vals):
        # If setting this PIC as primary, unset others
        if vals.get('is_primary') and vals.get('partner_id'):
            self.search([
                ('partner_id', '=', vals['partner_id']),
                ('is_primary', '=', True)
            ]).write({'is_primary': False})
        return super().create(vals)
    
    def write(self, vals):
        # If setting this PIC as primary, unset others
        if vals.get('is_primary') and vals['is_primary']:
            for pic in self:
                self.search([
                    ('partner_id', '=', pic.partner_id.id),
                    ('id', '!=', pic.id),
                    ('is_primary', '=', True)
                ]).write({'is_primary': False})
        return super().write(vals)