"""Безопасное вычисление арифметических выражений без eval()."""
import ast
import operator

MAX_LENGTH = 100
MAX_POWER = 100

BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

UNARY = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _value(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(
            node.value, bool
        ):
            return node.value

        raise ValueError("разрешены только числа")

    if isinstance(node, ast.BinOp) and type(node.op) in BINARY:
        left = _value(node.left)
        right = _value(node.right)

        if isinstance(node.op, ast.Pow) and abs(right) > MAX_POWER:
            raise ValueError("слишком большая степень")

        return BINARY[type(node.op)](left, right)

    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:
        return UNARY[type(node.op)](_value(node.operand))

    raise ValueError("недопустимое выражение")


def answer(text):
    """Возвращает строку-ответ: '= результат' или 'ошибка: причина'."""
    text = text.strip()

    if not text:
        return "ошибка: пустое выражение"

    if len(text) > MAX_LENGTH:
        return "ошибка: слишком длинное выражение"

    try:
        tree = ast.parse(text, mode="eval")
        return f"= {_value(tree.body)}"
    except ZeroDivisionError:
        return "ошибка: деление на ноль"
    except SyntaxError:
        return "ошибка: синтаксическая ошибка"
    except (ValueError, OverflowError) as error:
        return f"ошибка: {error}"
