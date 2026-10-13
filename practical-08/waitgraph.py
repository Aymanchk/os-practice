"""Поиск цикла в графе ожидания (обход в глубину)."""


def find_cycle(graph):
    """graph: словарь {вершина: набор вершин, которых она ждёт}.
    Возвращает список вершин одного цикла (без повтора первой) или None."""
    white, gray, black = 0, 1, 2
    color = {}
    path = []

    def dfs(v):
        color[v] = gray
        path.append(v)
        for w in sorted(graph.get(v, ())):
            c = color.get(w, white)
            if c == gray:
                # нашли ребро в вершину, которая лежит в текущем пути: это цикл
                return path[path.index(w):]
            if c == white:
                found = dfs(w)
                if found:
                    return found
        path.pop()
        color[v] = black
        return None

    for v in sorted(graph):
        if color.get(v, white) == white:
            found = dfs(v)
            if found:
                return found
    return None
