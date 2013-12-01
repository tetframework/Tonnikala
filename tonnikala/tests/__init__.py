import unittest

from . import test_expressions, test_html_templates, test_chameleon_templates

test_modules = [
    test_expressions,
    test_html_templates,
    test_chameleon_templates,
]

def create_test_suite(modules):
    suites = []
    for module in modules:
        suites.append(unittest.TestLoader().loadTestsFromModule(module))

    suite = unittest.TestSuite()
    suite.addTests(suites)
    return suite

test_all = create_test_suite(test_modules)
