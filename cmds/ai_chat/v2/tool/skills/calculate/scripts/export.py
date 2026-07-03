import ast
import operator

ops = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod
}

class Tool:
    def call(self, expression: str) -> str:
        def eval_expr(node):
            if isinstance(node, ast.BinOp) and type(node.op) in ops:
                return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
            elif isinstance(node, ast.Constant):
                return node.value
            else:
                return '沒有計算結果，請自己計算。'

        try:
            tree = ast.parse(expression, mode='eval')
            result = eval_expr(tree.body)
            if str(result).endswith('.0'):
                return str(int(result))
            else:
                return str(result)
        except Exception:
            return "無效的數學表達式"
