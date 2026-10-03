"""举报队列：按目标合并、举报人去重、优先级排序、超时升级与处理幂等。

实现要点：用字典按目标索引举报（举报人集合去重 + 最早举报时间），
待处理清单按（是否紧急、举报人数降序、最早举报时间升序、目标 id 升序）
排序，查询代价只与待处理目标数有关，不随举报总数线性增长。
"""


class Queue:
    """举报队列。"""

    def __init__(self, escalate_ms, max_pending):
        self.escalate_ms = escalate_ms
        self.max_pending = max_pending
        # target -> [reporter set, first seen ms]
        self.targets = {}
        self.resolved = set()
        self.reqs = set()
        self.scanned = 0

    def report(self, target, reporter, now_ms):
        """提交一次举报；超出待处理上限时返回 False。"""
        self.scanned += 1
        entry = self.targets.get(target)
        if entry is not None:
            entry[0].add(reporter)
            if now_ms < entry[1]:
                entry[1] = now_ms
            return True
        if len(self.targets) - len(self.resolved) >= self.max_pending:
            return False
        self.targets[target] = [{reporter}, now_ms]
        return True

    def reporters(self, target):
        """目标当前的举报人数（同一举报人只算一次）。"""
        self.scanned += 1
        entry = self.targets.get(target)
        return len(entry[0]) if entry is not None else 0

    def first_seen(self, target):
        """目标最早的举报时间，未知目标返回 None。"""
        self.scanned += 1
        entry = self.targets.get(target)
        return entry[1] if entry is not None else None

    def urgent(self, target, now_ms):
        """是否已经超过升级时限。"""
        self.scanned += 1
        entry = self.targets.get(target)
        if entry is None or target in self.resolved:
            return False
        return now_ms - entry[1] >= self.escalate_ms

    def pending(self, now_ms):
        """当前待处理的举报目标，按优先级排序。"""
        waiting = [target for target in self.targets
                   if target not in self.resolved]
        self.scanned += len(waiting)

        def sort_key(target):
            reporters, first = self.targets[target]
            is_urgent = now_ms - first >= self.escalate_ms
            return (0 if is_urgent else 1, -len(reporters), first, target)

        waiting.sort(key=sort_key)
        return waiting

    def resolve(self, target, req_id, now_ms):
        """处理一个举报目标；同一个 req_id 只处理一次。"""
        self.scanned += 1
        if req_id in self.reqs:
            return False
        self.reqs.add(req_id)
        self.resolved.add(target)
        return True

    def scanned_count(self):
        return self.scanned
