# __author__ = 'BinhTT'

{
    'name': 'ESS Discount',
    'summary': '',
    'version': '1.0',
    'category': 'Sale',
    'description': """
    standard packet for discount function of elephas
    """,
    'author': "Elephas",
    'website': 'http://www.elephas.solutions/',

    'depends': ['purchase', 'sale'],
    'data': [
             'wizard/sale_global_discount_wizard_view.xml',
             # 'views/account_invoice.xml',
             'views/sale_order_view.xml',
             'views/purchase_order_view.xml',
             # 'views/account_settings.xml',
             'security/ir.model.access.csv',
             ],
    'js': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
