# __author__ = 'BinhTT'
# -*- coding: utf-8 -*-

{
    'name': 'Rent Flow',
    'version': '1.2',
    'category': 'Base',
    'sequence': 60,
    'summary': 'Purchase orders, tenders and agreements',
    'description': "",
    'depends': ['sale', 'rent_product', 'delivery'],
    'data': [
        'security/ir.model.access.csv',
        'views/cash.xml',
        'views/sale_order.xml',
        'views/rent_pricelist.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}
