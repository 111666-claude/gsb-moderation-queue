# moderation-queue

举报队列：按目标合并、举报人去重、优先级排序、超时升级与处理幂等，
只用 Python 标准库。

```
python3 -m reports.cli --sample merge
python3 -m reports.cli --sample priority
python3 -m reports.cli --sample escalate
python3 -m reports.cli --sample cap
python3 -m reports.cli --sample resolve
python3 -m reports.cli --sample scan
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **合并**：同一个目标只占一条待处理记录，`pending` 里同一个目标只出现一次。
- **举报人去重**：同一个举报人重复举报同一个目标只算一个人。
- **优先级**：待处理清单按举报人数降序、最早举报时间升序、目标 id 升序排列。
- **超时升级**：最早举报时间距当前达到 `escalate_ms` 的目标是 urgent，
  排在所有普通目标前面。
- **上限**：待处理目标数不超过 `max_pending`，超出时 `report` 返回 False。
- **幂等**：同一个 `req_id` 只处理一次，重复 `resolve` 返回 False。
- **不变量**：已处理的目标不再出现在 `pending` 里；同一串举报与处理序列
  重复执行结果相同。
- **查询代价**：`pending` 不许遍历全部举报记录，`scanned_count`
  不随举报总数线性增长。
- **规模**：10 万条举报、每秒 10 万次查询，单次摊还 O(待处理目标数)。

## 输出契约（不改格式）

```
pending=..
first=..
urgent=..
third=..
second=..
scanned=..
```

## 目录

```
reports/core.py   合并、去重、优先级、升级与幂等
reports/cli.py    命令行入口
tests/            unittest 用例
```
