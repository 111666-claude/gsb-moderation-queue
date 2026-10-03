"""举报队列：按目标合并、举报人去重、优先级排序、超时升级与处理幂等。

缺陷：同一目标不合并、同一举报人重复计数、查询不按优先级排序、
超时不升级、处理不幂等、队列上限不生效、每次查询扫描全部举报。
"""


class Queue:
    """举报队列。"""

    def __init__(self, escalate_ms, max_pending):
        self.escalate_ms = escalate_ms
        self.max_pending = max_pending
        self.reports = []
        self.resolved = set()
        self.reqs = set()
        self.scanned = 0

    def report(self, target, reporter, now_ms):
        """提交一次举报。"""
        self.scanned += len(self.reports)
        self.reports.append((target, reporter, now_ms))
        return True

    def reporters(self, target):
        """目标当前的举报人数。"""
        return sum(1 for item, _, _ in self.reports if item == target)

    def first_seen(self, target):
        for item, _, at in self.reports:
            if item == target:
                return at
        return None

    def urgent(self, target, now_ms):
        """是否已经超过升级时限。"""
        return False

    def pending(self, now_ms):
        """当前待处理的举报目标。"""
        self.scanned += len(self.reports)
        return [target for target, _, _ in self.reports if target not in self.resolved]

    def resolve(self, target, req_id, now_ms):
        """处理一个举报目标。"""
        self.reqs.add(req_id)
        self.resolved.add(target)
        return True

    def scanned_count(self):
        return self.scanned
