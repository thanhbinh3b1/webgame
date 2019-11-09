# __author__ = 'BinhTT'
# -*- coding: utf-8 -*-

{
    'name': 'Rent Product',
    'version': '1.2',
    'category': 'Base',
    'sequence': 60,
    'summary': 'Purchase orders, tenders and agreements',
    'description': "",
    'depends': ['base', 'product'],
    'data': [
        'views/product_category.xml',
        'views/product_template.xml',
        'views/rent_type.xml',

    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}
