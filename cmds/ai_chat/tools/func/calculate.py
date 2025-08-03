import ast
import operator

ops = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod
}

def calculate(expression: str) -> str:
    """計算一個包含多個數字的四則運算表達式"""

    def eval_expr(node):
        """遞迴解析 AST (Abstract Syntax Tree)"""
        if isinstance(node, ast.BinOp) and type(node.op) in ops:
            # 如果是運算符節點，遞迴計算左邊與右邊的數字
            return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
        elif isinstance(node, ast.Num):
            # 如果是數字節點，直接返回數字
            return node.n
        else:
            return '沒有計算結果，請自己計算。'
        
    try:
        tree = ast.parse(expression, mode='eval')  # 解析表達式為 AST
        result = eval_expr(tree.body)  # 遞迴解析 AST
        if str(result).endswith('.0'):
            return int(result)  # 如果是整數則轉為 int
        else:
            return result
    except Exception:
        return "無效的數學表達式"