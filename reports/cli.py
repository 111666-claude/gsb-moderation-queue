"""命令行入口：跑举报队列样例。"""

import argparse

from .core import Queue


def build_parser():
    parser = argparse.ArgumentParser(prog="moderation-queue", description="举报队列")
    parser.add_argument("--sample", default="merge",
                        help="merge / priority / escalate / cap / resolve / scan")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.sample == "merge":
        queue = Queue(escalate_ms=100000, max_pending=10)
        queue.report("t1", "p1", 0)
        queue.report("t1", "p2", 10)
        print("pending=%d" % len(queue.pending(20)))
    elif args.sample == "priority":
        queue = Queue(escalate_ms=100000, max_pending=10)
        queue.report("t1", "p1", 0)
        queue.report("t2", "p2", 5)
        queue.report("t2", "p3", 6)
        out = queue.pending(20)
        print("first=%s" % (out[0] if out else "none"))
    elif args.sample == "escalate":
        queue = Queue(escalate_ms=1000, max_pending=10)
        queue.report("t1", "p1", 0)
        print("urgent=%s" % str(queue.urgent("t1", 2000)).lower())
    elif args.sample == "cap":
        queue = Queue(escalate_ms=100000, max_pending=2)
        ok = True
        for index in range(3):
            ok = queue.report("t-%d" % index, "p1", index)
        print("third=%s" % str(ok).lower())
    elif args.sample == "resolve":
        queue = Queue(escalate_ms=100000, max_pending=10)
        queue.report("t1", "p1", 0)
        queue.resolve("t1", "same", 1)
        print("second=%s" % str(queue.resolve("t1", "same", 2)).lower())
    elif args.sample == "scan":
        queue = Queue(escalate_ms=100000, max_pending=10000)
        for index in range(3000):
            queue.report("t1", "p-%d" % index, index)
        for index in range(3000):
            queue.pending(index)
        print("scanned=%d" % queue.scanned_count())
    else:
        raise SystemExit("需要 --sample merge|priority|escalate|cap|resolve|scan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
