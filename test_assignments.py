import ast
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('engine', Path(__file__).parent / 'assignment_engine.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)

SOLUTIONS = {
    'partition': '''    pivot = arr[r-1]
    i = l
    for j in range(l, r):
        if arr[j] <= pivot:
            arr[i], arr[j] = arr[j], arr[i]
            i += 1
    return i-1''',
    'merge': '''    tmp = arr[l:r]
    i, j, k = 0, m-l, l
    while i < m-l and j < r-l:
        if tmp[i] < tmp[j]:
            arr[k] = tmp[i]
            i += 1
        else:
            arr[k] = tmp[j]
            j += 1
        k += 1
    while i < m-l:
        arr[k] = tmp[i]
        i += 1; k += 1
    while j < r-l:
        arr[k] = tmp[j]
        j += 1; k += 1''',
    'siftdown': '''    while 2*root+1 < size:
        child = 2*root+1
        if child+1 < size and arr[child] < arr[child+1]:
            child += 1
        if arr[root] >= arr[child]:
            break
        arr[root], arr[child] = arr[child], arr[root]
        root = child''',
}


class AssignmentTests(unittest.TestCase):
    def test_reference_solutions_get_full_credit(self):
        for kind, body in SOLUTIONS.items():
            with self.subTest(kind=kind):
                result = engine.grade_assignment(kind, body)
                self.assertEqual(result['score'], 100, result)

    def test_recursive_siftdown(self):
        body = '''    child = 2*root+1
    if child >= size: return
    if child+1 < size and arr[child] < arr[child+1]:
        child += 1
    if arr[root] < arr[child]:
        arr[root], arr[child] = arr[child], arr[root]
        siftdown(arr, child, size)'''
        self.assertEqual(engine.grade_assignment('siftdown', body)['score'], 100)

    def test_quadratic_extra_work_fails_linear_budget(self):
        body = '    for a in range(r-l):\n        for b in range(r-l):\n            x = a+b\n' + SOLUTIONS['partition']
        result = engine.grade_assignment('partition', body)
        self.assertEqual(result['groups'][0]['points'], 40)
        self.assertEqual(result['groups'][1]['points'], 40)
        self.assertEqual(result['groups'][2]['points'], 0)

    def test_full_array_scan_fails_logarithmic_budget(self):
        body = '    for x in arr:\n        unused = x\n' + SOLUTIONS['siftdown']
        result = engine.grade_assignment('siftdown', body)
        self.assertEqual(result['groups'][0]['points'], 40)
        self.assertLess(result['groups'][2]['points'], 20)

    def test_correctness_required_for_complexity_points(self):
        for kind in SOLUTIONS:
            result = engine.grade_assignment(kind, '    pass')
            self.assertLess(result['score'], 100)
            self.assertEqual(result['groups'][2]['points'], 0)

    def test_forbidden_code_and_scaffold_override(self):
        for body in ('    arr.sort()', '    arr[:] = sorted(arr)', '    import os',
                     '    pass\n\ndef sort(arr):\n    pass',
                     '    return arr.__class__', '    def helper():\n        pass',
                     '    x = [v for v in arr]', '    eval("1")'):
            with self.subTest(body=body):
                self.assertIsNotNone(engine.grade_assignment('partition', body)['error'])

    def test_loop_limit_and_cyclic_array_are_bounded(self):
        for body in ('    while True:\n        pass', '    arr[0] = arr', '    arr.append(arr)'):
            result = engine.grade_assignment('siftdown', body)
            self.assertLess(result['score'], 100)

    def test_slicing_and_builtin_work_is_metered(self):
        for body in ('    x = arr[:]', '    x = list(arr)', '    x = min(arr)', '    x = [0] * len(arr)'):
            fn = engine.parse_student('siftdown', body)
            vm = engine.Interpreter(fn, 'siftdown', 1024, float('inf'))
            vm.invoke([list(range(1024)),0,1024])
            self.assertGreaterEqual(vm.ops, 1024)

    def test_loop_and_short_circuit_semantics(self):
        body = '''    i = l
    while i < r:
        i += 1
        if i == r: break
        if i < r and arr[i] < 0: continue
    else:
        return -1
    return i-1'''
        fn=engine.parse_student('partition',body)
        vm=engine.Interpreter(fn,'partition',3,float('inf'))
        self.assertEqual(vm.invoke([[3,2,1],0,3]),2)

    def test_augmented_list_assignment_preserves_alias(self):
        body = '''    tmp = []
    alias = tmp
    tmp += (3, 4)
    tmp *= 2
    return alias[3]'''
        fn=engine.parse_student('partition',body)
        vm=engine.Interpreter(fn,'partition',3,float('inf'))
        self.assertEqual(vm.invoke([[3,2,1],0,3]),4)

    def test_oversized_constant_reports_code_error(self):
        result=engine.grade_assignment('partition','    return '+('9'*400))
        self.assertIsNotNone(result['error'])


if __name__ == '__main__': unittest.main()
