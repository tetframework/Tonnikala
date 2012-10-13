import ast
import pdb

class FreeVarFinder(ast.NodeVisitor):
    """
    Finds free variables in a Python expression, which may contain lambda 
    functions.
    """
    def __init__(self, masked=[]):
        super(FreeVarFinder, self).__init__()
        self.masked    = set(masked)
        self.vars      = set()
        self.generated = set()

    def visit_Lambda(self, node):
        args = node.args.args
        masked = [ i.id for i in args ]
        subscoper = VarScoper(masked)
        subscoper.generic_visit(node)
        self.vars = self.vars.union(subscoper.get_free_variables())

        self.do_visit_lambda_defaults(node.args)

    def visit_FunctionDef(self, node):
        self.generated.add(node.name)
        self.visit_Lambda(self, node)

    def visit_arguments(self, node):
        pass

    def do_visit_lambda_defaults(self, node):
        for field, value in ast.iter_fields(node):
            if field == 'args':
                continue

            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item)

            elif isinstance(value, ast.AST):
                self.visit(value)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.masked.add(node.id)

        else:
            self.vars.add(node.id)

    def get_free_variables(self):
        return self.vars - self.masked - self.generated

    def get_generated_variables(self):
        return self.generated


def get_free_vars(expression):
    tree = ast.parse(expression, mode='eval')
    fvf = FreeVarFinder()
    fvf.visit(tree)
    return fvf.get_free_variables()
