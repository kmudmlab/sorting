"""Deterministic, metered interpreter for the three sorting exercises.

Student code is parsed, validated, and interpreted; it is never passed to exec.
Only the instructor-owned sorting drivers below are executed as Python code.
The browser grade is practice feedback, not a server-attested submission grade.
"""
import ast
import json
import math
import operator
import random
import time

VERSION = '2026-09-28.1'
ASSIGNMENTS = {
    'partition': {
        'title': '퀵 정렬 · partition', 'args': ['arr', 'l', 'r'],
        'signature': 'def partition(arr, l, r):', 'complexity': 'O(n)',
        'driver': '''def quicksort(arr, l, r):
    if l + 1 >= r: return
    p = partition(arr, l, r)
    quicksort(arr, l, p)
    quicksort(arr, p+1, r)

def sort(arr):
    quicksort(arr, 0, len(arr))''',
    },
    'merge': {
        'title': '병합 정렬 · merge', 'args': ['arr', 'l', 'm', 'r'],
        'signature': 'def merge(arr, l, m, r):', 'complexity': 'O(n)',
        'driver': '''def mergesort(arr, l, r):
    if l + 1 >= r: return
    m = (l + r) // 2
    mergesort(arr, l, m)
    mergesort(arr, m, r)
    merge(arr, l, m, r)

def sort(arr):
    mergesort(arr, 0, len(arr))''',
    },
    'siftdown': {
        'title': '힙 정렬 · siftdown', 'args': ['arr', 'root', 'size'],
        'signature': 'def siftdown(arr, root, size):', 'complexity': 'O(log n)',
        'driver': '''def heapsort(arr):
    size = len(arr)
    for root in range(size // 2 - 1, -1, -1):
        siftdown(arr, root, size)
    for end in range(size - 1, 0, -1):
        arr[0], arr[end] = arr[end], arr[0]
        siftdown(arr, 0, end)

def sort(arr):
    heapsort(arr)''',
    },
}


class InvalidCode(Exception): pass
class BudgetExceeded(Exception): pass
class Returned(Exception):
    def __init__(self, value): self.value = value
class BreakLoop(Exception): pass
class ContinueLoop(Exception): pass


BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
          ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod}
CMPOPS = {ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt,
          ast.GtE: operator.ge, ast.Eq: operator.eq, ast.NotEq: operator.ne}
BUILTINS = {'len', 'range', 'min', 'max', 'abs', 'list'}


def parse_student(kind, body):
    if kind not in ASSIGNMENTS: raise InvalidCode('알 수 없는 과제입니다.')
    if not isinstance(body, str) or len(body) > 12000:
        raise InvalidCode('함수 본문은 12,000자 이내로 작성하세요.')
    spec = ASSIGNMENTS[kind]
    source = spec['signature'] + '\n' + body
    tree = ast.parse(source, filename='<student>')
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise InvalidCode('지정된 함수의 본문만 작성할 수 있습니다.')
    fn = tree.body[0]
    if fn.name != kind or [a.arg for a in fn.args.args] != spec['args']:
        raise InvalidCode('함수 이름과 매개변수는 수정할 수 없습니다.')
    allowed = (ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Assign,
               ast.AugAssign, ast.If, ast.For, ast.While, ast.Return, ast.Break,
               ast.Continue, ast.Pass, ast.Expr, ast.Name, ast.Constant, ast.List,
               ast.Tuple, ast.Subscript, ast.Slice, ast.BinOp, ast.UnaryOp,
               ast.BoolOp, ast.Compare, ast.Call, ast.Attribute, ast.IfExp,
               ast.Load, ast.Store, ast.Add, ast.Sub, ast.Mult, ast.Div,
               ast.FloorDiv, ast.Mod, ast.USub, ast.UAdd, ast.Not, ast.And,
               ast.Or, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq)
    nodes = list(ast.walk(tree))
    if len(nodes) > 2500: raise InvalidCode('코드가 너무 깁니다.')
    for node in nodes:
        line = getattr(node, 'lineno', 1)
        def reject(message): raise InvalidCode(f'{line}행: {message}')
        if not isinstance(node, allowed):
            reject('기본 대입·조건문·반복문·배열 연산만 사용할 수 있습니다. import, 내장 정렬, 컴프리헨션 등은 지원하지 않습니다.')
        if isinstance(node, ast.FunctionDef) and node is not fn:
            reject('새 함수를 정의할 수 없습니다. 자기 자신을 호출하는 재귀는 가능합니다.')
        if isinstance(node, ast.Name):
            if node.id.startswith('_') and node.id != '_': reject('밑줄로 시작하는 내부 이름은 사용할 수 없습니다.')
            if isinstance(node.ctx, ast.Store) and node.id in BUILTINS | {kind}:
                reject('함수 이름을 변수로 사용할 수 없습니다.')
        if isinstance(node, ast.Call):
            if node.keywords: reject('키워드 인수는 지원하지 않습니다.')
            valid_name = isinstance(node.func, ast.Name) and node.func.id in BUILTINS | {kind}
            valid_method = isinstance(node.func, ast.Attribute) and node.func.attr == 'append'
            if not (valid_name or valid_method): reject('len, range, min, max, abs, list, append, 자기 재귀만 호출할 수 있습니다.')
        if isinstance(node, ast.Attribute) and node.attr != 'append': reject('append 외의 속성이나 메서드는 사용할 수 없습니다.')
        if isinstance(node, ast.Constant):
            if type(node.value) not in (int, float, bool, str, type(None)): reject('지원하지 않는 상수입니다.')
            if isinstance(node.value, str) and len(node.value) > 1000: reject('문자열이 너무 깁니다.')
            if type(node.value) in (int, float) and (abs(node.value) > 10**9 or not math.isfinite(node.value)): reject('상수가 너무 큽니다.')
    # Also checks break/continue/return placement without executing student code.
    compile(tree, '<student>', 'exec')
    return fn


def operation_limit(kind, n):
    if kind == 'siftdown': return 120 * math.ceil(math.log2(max(1, n) + 1)) + 120
    return 100 * max(0, n) + 160


class Interpreter:
    def __init__(self, fn, kind, n, deadline, limit=None):
        self.fn, self.kind, self.n = fn, kind, n
        self.limit = operation_limit(kind, n) if limit is None else limit
        self.ops, self.depth, self.line = 0, 0, 1
        self.deadline = deadline
        self.max_items = max(128, n * 4 + 16)

    def tick(self, cost=1):
        self.ops += cost
        if self.ops > self.limit:
            raise BudgetExceeded(f'연산 수 {self.ops:,}회가 기준 {self.limit:,}회를 넘었습니다.')
        if self.ops % 256 == 0 and time.perf_counter() > self.deadline:
            raise BudgetExceeded('채점 실행 제한 시간을 넘었습니다.')

    def sequence(self, value):
        if type(value) not in (list, tuple, range): raise InvalidCode('리스트·튜플·range가 필요합니다.')
        return value

    def bounded(self, value):
        if type(value) in (int, float) and (abs(value) > 10**12 or not math.isfinite(value)):
            raise InvalidCode('수치가 허용 범위를 벗어났습니다.')
        return value

    def index(self, node, env):
        if isinstance(node, ast.Slice):
            return slice(*(self.expr(v, env) if v else None for v in (node.lower, node.upper, node.step)))
        return self.expr(node, env)

    def getitem(self, base, key):
        self.sequence(base)
        if isinstance(key, slice):
            self.tick(len(range(*key.indices(len(base)))))
        else: self.tick()
        return base[key]

    def setitem(self, base, key, value):
        if type(base) is not list: raise InvalidCode('리스트의 원소만 변경할 수 있습니다.')
        if isinstance(key, slice):
            self.sequence(value)
            count = len(range(*key.indices(len(base))))
            if count != len(value): raise InvalidCode('슬라이스 대입으로 배열 길이를 바꿀 수 없습니다.')
            self.tick(count)
            if any(type(v) not in (int, float, bool, type(None)) for v in value):
                raise InvalidCode('배열 원소에는 숫자 또는 None만 넣을 수 있습니다.')
        else:
            if type(value) not in (int, float, bool, type(None)):
                raise InvalidCode('배열 원소에는 숫자 또는 None만 넣을 수 있습니다.')
            self.tick()
        base[key] = value

    def assign(self, target, value, env):
        self.tick()
        if isinstance(target, ast.Name): env[target.id] = value
        elif isinstance(target, (ast.Tuple, ast.List)):
            self.sequence(value)
            if len(target.elts) != len(value): raise ValueError('대입할 원소 수가 다릅니다.')
            for left, right in zip(target.elts, value): self.assign(left, right, env)
        elif isinstance(target, ast.Subscript):
            base, key = self.expr(target.value, env), self.index(target.slice, env)
            self.setitem(base, key, value)
        else: raise InvalidCode('지원하지 않는 대입입니다.')

    def binary(self, op, left, right):
        if type(left) in (list, tuple) or type(right) in (list, tuple):
            if isinstance(op, ast.Add) and type(left) is type(right): size = len(left) + len(right)
            elif isinstance(op, ast.Mult) and type(left) in (list, tuple) and type(right) is int: size = len(left) * max(0, right)
            elif isinstance(op, ast.Mult) and type(right) in (list, tuple) and type(left) is int: size = len(right) * max(0, left)
            else: raise InvalidCode('지원하지 않는 배열 연산입니다.')
            if size > self.max_items: raise InvalidCode('보조 배열 크기가 허용 범위를 넘었습니다.')
            self.tick(size)
        elif type(left) not in (int, float, bool) or type(right) not in (int, float, bool):
            raise InvalidCode('산술 연산은 숫자와 리스트에만 사용할 수 있습니다.')
        return self.bounded(BINOPS[type(op)](left, right))

    def expr(self, node, env):
        self.tick()
        self.line = getattr(node, 'lineno', self.line)
        if isinstance(node, ast.Constant): return node.value
        if isinstance(node, ast.Name):
            if node.id not in env: raise NameError(f"'{node.id}' 변수가 정의되지 않았습니다.")
            return env[node.id]
        if isinstance(node, (ast.List, ast.Tuple)):
            values = [self.expr(v, env) for v in node.elts]
            return values if isinstance(node, ast.List) else tuple(values)
        if isinstance(node, ast.Subscript): return self.getitem(self.expr(node.value, env), self.index(node.slice, env))
        if isinstance(node, ast.BinOp): return self.binary(node.op, self.expr(node.left, env), self.expr(node.right, env))
        if isinstance(node, ast.UnaryOp):
            value = self.expr(node.operand, env)
            if isinstance(node.op, ast.Not): return not value
            if type(value) not in (int, float, bool): raise InvalidCode('숫자가 필요합니다.')
            return -value if isinstance(node.op, ast.USub) else +value
        if isinstance(node, ast.BoolOp):
            value = self.expr(node.values[0], env)
            for next_node in node.values[1:]:
                if isinstance(node.op, ast.And) and not value: break
                if isinstance(node.op, ast.Or) and value: break
                value = self.expr(next_node, env)
            return value
        if isinstance(node, ast.Compare):
            left = self.expr(node.left, env)
            for op, other in zip(node.ops, node.comparators):
                right = self.expr(other, env)
                # Array comparisons hide linear work; this exercise uses scalar comparisons.
                if type(left) in (list, tuple, range) or type(right) in (list, tuple, range):
                    raise InvalidCode('배열 전체 비교 대신 원소를 비교하세요.')
                if not CMPOPS[type(op)](left, right): return False
                left = right
            return True
        if isinstance(node, ast.IfExp):
            return self.expr(node.body if self.expr(node.test, env) else node.orelse, env)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                base = self.expr(node.func.value, env)
                args = [self.expr(v, env) for v in node.args]
                if type(base) is not list or len(args) != 1: raise InvalidCode('append에는 리스트와 인수 한 개가 필요합니다.')
                if type(args[0]) not in (int, float, bool, type(None)): raise InvalidCode('append에는 숫자 또는 None만 넣을 수 있습니다.')
                if len(base) >= self.max_items: raise InvalidCode('배열 크기 제한을 넘었습니다.')
                self.tick(); base.append(args[0]); return None
            name = node.func.id
            args = [self.expr(v, env) for v in node.args]
            if name == self.kind: return self.invoke(args)
            if name == 'len' and len(args) == 1: return len(self.sequence(args[0]))
            if name == 'range' and 1 <= len(args) <= 3:
                if not all(type(v) is int for v in args): raise InvalidCode('range 인수는 정수여야 합니다.')
                return range(*args)
            if name == 'list' and len(args) <= 1:
                value = self.sequence(args[0]) if args else []
                if len(value) > self.max_items: raise InvalidCode('배열 크기 제한을 넘었습니다.')
                self.tick(len(value)); return list(value)
            if name == 'abs' and len(args) == 1 and type(args[0]) in (int, float): return abs(args[0])
            if name in ('min', 'max') and args:
                values = self.sequence(args[0]) if len(args) == 1 else args
                self.tick(len(values))
                if any(type(v) not in (int, float, bool) for v in values): raise InvalidCode('min/max는 숫자에만 사용할 수 있습니다.')
                return (min if name == 'min' else max)(values)
            raise InvalidCode(f'{name} 호출의 인수를 확인하세요.')
        raise InvalidCode('지원하지 않는 표현식입니다.')

    def block(self, statements, env):
        for node in statements:
            self.tick(); self.line = node.lineno
            if isinstance(node, ast.Assign):
                value = self.expr(node.value, env)
                for target in node.targets: self.assign(target, value, env)
            elif isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Name):
                    name = node.target.id
                    if name not in env: raise NameError(name)
                    left = env[name]
                    right = self.expr(node.value, env)
                    if type(left) is list:
                        # Preserve Python's aliasing for += / *=, but keep
                        # nested/cyclic arrays outside the numeric-array subset.
                        if isinstance(node.op, ast.Add):
                            self.sequence(right)
                            if any(type(v) not in (int, float, bool, type(None)) for v in right):
                                raise InvalidCode('배열 원소에는 숫자 또는 None만 넣을 수 있습니다.')
                            right = list(right)
                        value = self.binary(node.op, left, right)
                        left[:] = value
                        value = left
                    else:
                        value = self.binary(node.op, left, right)
                    self.assign(node.target, value, env)
                elif isinstance(node.target, ast.Subscript):
                    base, key = self.expr(node.target.value, env), self.index(node.target.slice, env)
                    value = self.binary(node.op, self.getitem(base, key), self.expr(node.value, env))
                    self.setitem(base, key, value)
                else: raise InvalidCode('지원하지 않는 복합 대입입니다.')
            elif isinstance(node, ast.Expr): self.expr(node.value, env)
            elif isinstance(node, ast.If): self.block(node.body if self.expr(node.test, env) else node.orelse, env)
            elif isinstance(node, (ast.For, ast.While)):
                iterator = iter(self.sequence(self.expr(node.iter, env))) if isinstance(node, ast.For) else None
                broke = False
                while True:
                    self.tick()
                    if iterator is not None:
                        try: value = next(iterator)
                        except StopIteration: break
                        self.assign(node.target, value, env)
                    elif not self.expr(node.test, env): break
                    try: self.block(node.body, env)
                    except ContinueLoop: continue
                    except BreakLoop: broke = True; break
                if not broke: self.block(node.orelse, env)
            elif isinstance(node, ast.Return): raise Returned(self.expr(node.value, env) if node.value else None)
            elif isinstance(node, ast.Break): raise BreakLoop()
            elif isinstance(node, ast.Continue): raise ContinueLoop()
            elif not isinstance(node, ast.Pass): raise InvalidCode('지원하지 않는 문장입니다.')

    def invoke(self, args):
        self.tick()
        if len(args) != len(self.fn.args.args): raise TypeError('함수 인수 수가 다릅니다.')
        self.depth += 1
        if self.depth > 100: raise BudgetExceeded('재귀 호출 깊이가 100을 넘었습니다.')
        env = dict(zip(ASSIGNMENTS[self.kind]['args'], args))
        try:
            self.block(self.fn.body, env)
        except Returned as result: return result.value
        finally: self.depth -= 1


def heap_nodes(root, size):
    todo, nodes = [root], []
    while todo:
        i = todo.pop()
        if 0 <= i < size:
            nodes.append(i); todo.extend((2*i+1, 2*i+2))
    return nodes


def unit_check(kind, before, after, args, returned):
    if len(before) != len(after): return False, '배열 길이가 바뀌었습니다.'
    if any(type(v) not in (int, float) for v in after): return False, '배열에 숫자가 아닌 값이 들어갔습니다.'
    if kind == 'partition':
        l, r = args; p = returned
        if type(p) is not int or not l <= p < r: return False, '반환값은 [l, r) 안의 피벗 인덱스여야 합니다.'
        pivot = before[r-1]
        valid = (after[p] == pivot and all(v <= pivot for v in after[l:p])
                 and all(v > pivot for v in after[p+1:r])
                 and sorted(before[l:r]) == sorted(after[l:r])
                 and before[:l] == after[:l] and before[r:] == after[r:])
        return valid, f'피벗 {pivot} 기준으로 왼쪽 ≤ 피벗, 오른쪽 > 피벗이어야 하며 구간 밖 값은 보존해야 합니다.'
    if kind == 'merge':
        l, m, r = args
        expected = before[:l] + sorted(before[l:r]) + before[r:]
        return after == expected, '두 정렬된 구간을 병합하고 구간 밖 원소를 보존해야 합니다.'
    root, size = args
    nodes = heap_nodes(root, size); node_set = set(nodes)
    valid = (sorted(before[i] for i in nodes) == sorted(after[i] for i in nodes)
             and all(before[i] == after[i] for i in range(len(before)) if i not in node_set)
             and all(after[i] >= after[c] for i in nodes for c in (2*i+1,2*i+2) if c < size))
    return valid, 'root의 서브트리는 최대 힙이어야 하고, 다른 위치와 size 이후의 값은 보존해야 합니다.'


def grade_assignment(kind, body):
    started = time.perf_counter()
    result = {'version': VERSION, 'kind': kind, 'score': 0, 'error': None,
              'groups': [], 'complexity': [], 'failures': []}
    try: fn = parse_student(kind, body)
    except (SyntaxError, InvalidCode, ValueError, RecursionError) as exc:
        result['error'] = str(exc)
        return result
    rng = random.Random(20260928)
    deadline = started + 20

    def run_case(values, params, full=False, enforce=False):
        arr, total, worst, limit_hit = list(values), 0, 0, False
        def student(*args):
            nonlocal total, worst, limit_hit
            n = args[-1] if kind == 'siftdown' else args[-1] - args[1]
            budget = operation_limit(kind, n)
            # Correctness is graded separately with a generous finite bound.
            interpreter = Interpreter(fn, kind, n, deadline, budget if enforce else 250000)
            try: return interpreter.invoke(list(args))
            finally:
                total += interpreter.ops
                worst = max(worst, interpreter.ops / budget)
                limit_hit = limit_hit or interpreter.ops > budget
        try:
            if full:
                namespace = {kind: student}
                exec(ASSIGNMENTS[kind]['driver'], namespace)
                namespace['sort'](arr)
                passed, reason = arr == sorted(values), '전체 정렬 결과가 오름차순 정렬과 다릅니다.'
                returned = None
            else:
                returned = student(arr, *params)
                passed, reason = unit_check(kind, values, arr, params, returned)
            return {'passed': passed, 'ops': total, 'budgetExceeded': limit_hit,
                    'message': '' if passed else reason, 'actual': arr, 'returned': returned}
        except Exception as exc:
            return {'passed': False, 'ops': total, 'budgetExceeded': limit_hit,
                    'message': f'{type(exc).__name__}: {str(exc)[:300]}', 'actual': arr, 'returned': None}

    basic = [[], [4], [2,1], [1,2], [3,3,3,3], [5,4,3,2,1],
             [1,2,3,4,5], [-3,4,-3,0,2.5], [4,1,4,2,4,0]]
    basic += [[rng.randrange(-30,31) for _ in range(n)] for n in (7,12,25,40)]
    units = []
    if kind == 'partition':
        for values in basic[1:]:
            units += [(values, (0,len(values))), ([901]+values+[-901], (1,len(values)+1))]
    elif kind == 'merge':
        for values in basic:
            for mid in sorted(set((0,len(values)//2,len(values)))):
                prepared = sorted(values[:mid]) + sorted(values[mid:])
                units.append(([901]+prepared+[-901], (1,mid+1,len(values)+1)))
    else:
        for n in (0,1,2,3,4,7,8,15,31,60):
            for root in sorted(set((0, max(0,n//4), max(0,n-1)))):
                values = list(range(n,0,-1)) + [901,-901]
                if root < n: values[root] = -999
                units.append((values, (root,n)))
        units += [([3,3,3,3,901],(0,4)), ([0, -1, 4, -5, -2, 2, 3],(0,7))]

    for group, cases, weight, full in (
        ('함수 단독 정확성', units, 40, False),
        ('고정 코드와 전체 정렬', [(v,()) for v in basic], 40, True),
    ):
        passed = 0
        for values, params in cases:
            record = run_case(values, params, full)
            passed += int(record['passed'])
            if not record['passed'] and len(result['failures']) < 6:
                result['failures'].append({'group':group, 'input':values, 'params':list(params),
                                          'full':full, **record})
        points = round(weight * passed / len(cases))
        result['groups'].append({'name':group, 'passed':passed,'total':len(cases),'points':points,'max':weight})
        result['score'] += points

    for n in (64,128,256,512,1024):
        cases = []
        if kind == 'partition':
            variants = [list(range(n)), list(range(n,0,-1)), [7]*n,
                        [rng.randrange(n) for _ in range(n)]]
            cases = [(v,(0,n)) for v in variants]
        elif kind == 'merge':
            m=n//2
            variants = [list(range(0,n,2))+list(range(1,n,2)),
                        list(range(m,n))+list(range(m)), [7]*n]
            cases = [(v,(0,m,n)) for v in variants]
        else:
            # Descending values form valid child heaps; both shallow and deep
            # starting nodes expose implementations that scan unrelated nodes.
            for root in (0,n//4,n-1):
                v = list(range(n,0,-1)); v[root] = -1
                cases.append((v,(root,n)))
        records = [run_case(v,p,enforce=True) for v,p in cases]
        valid = all(r['passed'] and not r['budgetExceeded'] for r in records)
        failure = next((r for r in records if not r['passed'] or r['budgetExceeded']), None)
        result['complexity'].append({'n':n,'ops':max(r['ops'] for r in records),
                                     'limit':operation_limit(kind,n),'passed':valid,
                                     'message':failure['message'] if failure else ''})
    passed = sum(r['passed'] for r in result['complexity'])
    points = 20 * passed // 5
    result['score'] += points
    result['groups'].append({'name':'연산 수 기준과 정확성','passed':passed,'total':5,'points':points,'max':20})
    result['elapsed'] = round((time.perf_counter()-started)*1000)
    return result
