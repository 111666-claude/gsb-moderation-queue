"""举报队列：按目标合并、举报人去重、优先级排序、超时升级与处理幂等。

内部按目标合并存放举报：每个目标只记录最早举报时间与去重后的
举报人集合。两个组（紧急/普通）各维护一条按优先级排好序的键
列表，举报变更做增量插入/删除，升级时限用小顶堆懒触发，因此
查询与变更的摊还代价只随待处理目标数增长，与举报总条数无关。
"""

import bisect
import heapq


class Queue:
    """举报队列。"""

    def __init__(self, escalate_ms, max_pending):
        self.escalate_ms = escalate_ms
        self.max_pending = max_pending
        self.targets = {}
        self.resolved = set()
        self.reqs = set()
        self.scanned = 0
        self._pending_size = 0
        self._deadlines = []
        self._groups = {0: [], 1: []}
        self._ordered = None

    def _key(self, target, entry):
        return (-len(entry[1]), entry[0], target)

    def _remove_key(self, group, key):
        ordered = self._groups[group]
        index = bisect.bisect_left(ordered, key)
        if index < len(ordered) and ordered[index] == key:
            ordered.pop(index)

    def report(self, target, reporter, now_ms):
        """提交一次举报。超出待处理上限时返回 False。"""
        if target in self.resolved:
            return True
        entry = self.targets.get(target)
        if entry is not None:
            if reporter not in entry[1]:
                group = entry[2]
                self._remove_key(group, self._key(target, entry))
                entry[1].add(reporter)
                bisect.insort(self._groups[group], self._key(target, entry))
                self._ordered = None
            return True
        if self._pending_size >= self.max_pending:
            return False
        entry = [now_ms, {reporter}, 1]
        self.targets[target] = entry
        self._pending_size += 1
        heapq.heappush(self._deadlines,
                       (now_ms + self.escalate_ms, target))
        bisect.insort(self._groups[1], self._key(target, entry))
        self._ordered = None
        return True

    def reporters(self, target):
        """目标当前的举报人数（同一举报人只算一次）。"""
        entry = self.targets.get(target)
        return len(entry[1]) if entry is not None else 0

    def first_seen(self, target):
        entry = self.targets.get(target)
        return entry[0] if entry is not None else None

    def urgent(self, target, now_ms):
        """是否已经达到升级时限。"""
        entry = self.targets.get(target)
        if entry is None or target in self.resolved:
            return False
        return now_ms - entry[0] >= self.escalate_ms

    def pending(self, now_ms):
        """当前待处理的举报目标，紧急的排在普通目标前面。"""
        changed = self._ordered is None
        while self._deadlines and self._deadlines[0][0] <= now_ms:
            _, target = heapq.heappop(self._deadlines)
            entry = self.targets.get(target)
            if entry is None or target in self.resolved or entry[2] == 0:
                continue
            self._remove_key(1, self._key(target, entry))
            entry[2] = 0
            bisect.insort(self._groups[0], self._key(target, entry))
            changed = True
        if changed:
            self._ordered = [key[2] for key in self._groups[0]]
            self._ordered.extend(key[2] for key in self._groups[1])
        self.scanned += self._pending_size
        return self._ordered

    def resolve(self, target, req_id, now_ms):
        """处理一个举报目标，同一个 req_id 只生效一次。"""
        if req_id in self.reqs:
            return False
        self.reqs.add(req_id)
        entry = self.targets.get(target)
        if entry is not None and target not in self.resolved:
            self._remove_key(entry[2], self._key(target, entry))
            self._pending_size -= 1
        self.resolved.add(target)
        self._ordered = None
        return True

    def scanned_count(self):
        return self.scanned
