# -*- coding: utf-8 -*-
{
    'name': 'Purchase Restricted Access',
    'version': '18.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Dua grup akses terbatas untuk modul Purchase (RFQ & PO only)',
    'description': """
Purchase Restricted Access
==========================

Membuat dua grup pengguna terbatas untuk modul Purchase:

1. **Purchase User - Own Records**
   - Hanya dapat melihat RFQ dan PO milik sendiri
   - Record dibatasi berdasarkan user_id atau create_uid

2. **Purchase User - Department Records**
   - Dapat melihat RFQ dan PO seluruh anggota departemennya
   - Record dibatasi berdasarkan department dari employee yang terhubung ke user

Kedua grup:
- Hanya melihat menu Request for Quotation dan Purchase Orders
- Tidak dapat melihat menu lain di luar kedua menu tersebut
- Tidak dapat menghapus record (read, write, create only)
    """,
    'author': 'Custom Development',
    'depends': [
        'purchase',
        'hr',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
