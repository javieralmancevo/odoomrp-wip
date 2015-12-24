# -*- coding: utf-8 -*-
{
    'name': "product_attribute_hierarchy",

    'summary': """
        Restrict certain variant combinations.
        """,

    'description': """
        Stablish relationships between attributes values so that certain combinations
        are not valid and the product variant won't be created, even when assigned to
        a product template.
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product', 'product_variants_no_automatic_creation'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'installable': True,
}
