"""Compare batch latency with serial and persistent-pool controls (issue #530).

Run against the installed tiktoken build; see investigate_batch_latency.md.
This is a diagnostic experiment, not a replacement implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


PARAGRAPH = (
    "This is a reproducible synthetic document about batch tokenization. "
    "İstanbul'da ışık, ölçüm ve çalışma süreleri karşılaştırılıyor. "
    "東京で文章を読み、結果を比較します。 "
    "نقارن النتائج باستخدام النص نفسه. "
    "Unicode: café, naïve, Ελληνικά, हिन्दी, 😀 🧪.\n"
)


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def measure(
    run: Callable[[], list[list[int]]], expected: list[list[int]]
) -> dict[str, float]:
    # Keep outputs alive until both clocks stop. Validation and output destruction
    # are outside the timing window, consistently for every condition.
    wall_start = time.perf_counter_ns()
    cpu_start = time.process_time_ns()
    output = run()
    cpu_ns = time.process_time_ns() - cpu_start
    wall_ns = time.perf_counter_ns() - wall_start
    if output != expected:
        raise RuntimeError("token output differs from serial reference")
    del output
    return {"wall_ms": wall_ns / 1e6, "process_cpu_ms": cpu_ns / 1e6}


def summarize(samples: list[dict]) -> dict[str, float | int]:
    times = [sample["wall_ms"] for sample in samples]
    median = statistics.median(times)
    return {
        "runs": len(times),
        "median_ms": median,
        "min_ms": min(times),
        "max_ms": max(times),
        "max_over_median": max(times) / median if median else 0.0,
        "median_process_cpu_ms": statistics.median(
            sample["process_cpu_ms"] for sample in samples
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--build-label", required=True, help="e.g. pypi-wheel-0.14.0")
    parser.add_argument("--encoding", default="o200k_base")
    parser.add_argument("--corpus", type=Path, help="optional UTF-8 text file")
    parser.add_argument("--repeat", type=positive_int, default=64)
    parser.add_argument("--batch-size", type=positive_int, default=32)
    parser.add_argument("--runs", type=positive_int, default=10)
    parser.add_argument("--warmups", type=positive_int, default=2)
    parser.add_argument("--threads", type=positive_int, nargs="+", default=[1, 2, 4, 8])
    parser.add_argument("--seed", type=int, default=530)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose a new result filename")
    if len(set(args.threads)) != len(args.threads):
        parser.error("thread counts must be unique")

    import tiktoken
    from tiktoken import _tiktoken

    # Read bytes explicitly to preserve CRLF in user-supplied corpus hashes.
    text = args.corpus.read_bytes().decode("utf-8") if args.corpus else PARAGRAPH
    text *= args.repeat
    if not text:
        parser.error("corpus must not be empty")
    documents = [text] * args.batch_size
    encoded = text.encode("utf-8")
    enc = tiktoken.get_encoding(args.encoding)
    expected_one = enc.encode_ordinary(text)
    expected = [expected_one] * args.batch_size
    root = Path(__file__).resolve().parents[1]
    try:
        harness_commit = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        harness_commit = None

    report = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "build_label": args.build_label,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "logical_cpus": os.cpu_count(),
            "tiktoken_version": tiktoken.__version__,
            "native_module_filename": Path(_tiktoken.__file__).name,
            "native_module_sha256": hashlib.sha256(
                Path(_tiktoken.__file__).read_bytes()
            ).hexdigest(),
            "core_py_sha256": hashlib.sha256(
                Path(tiktoken.core.__file__).read_bytes()
            ).hexdigest(),
            "harness_checkout_commit": harness_commit,
            "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "workload": {
            "source": args.corpus.name if args.corpus else "synthetic-multilingual-v1",
            "document_sha256": hashlib.sha256(encoded).hexdigest(),
            "document_utf8_bytes": len(encoded),
            "document_tokens": len(expected_one),
            "repeat": args.repeat,
            "batch_size": args.batch_size,
            "encoding": args.encoding,
        },
        "settings": {
            "runs": args.runs, "warmups": args.warmups,
            "threads": args.threads, "seed": args.seed,
        },
        "method": {
            "order": "seeded shuffle of all conditions for each round",
            "timed": "encoding, output allocation, and public-call pool lifecycle",
            "untimed": "encoding load, parity checks, output destruction, reused-pool lifecycle",
            "reference": "encode_ordinary(text), compared to every document in every call",
            "warning": "persistent-pool is a diagnostic control, not a proposed API change",
        },
        "samples": [],
    }
    samples = report["samples"]
    with ExitStack() as stack:
        conditions = {"serial": lambda: [enc.encode_ordinary(doc) for doc in documents]}
        for threads in args.threads:
            pool = stack.enter_context(ThreadPoolExecutor(max_workers=threads))
            conditions[f"public_batch/{threads}"] = (
                lambda threads=threads: enc.encode_ordinary_batch(documents, num_threads=threads)
            )
            conditions[f"reused_pool/{threads}"] = (
                lambda pool=pool: list(pool.map(enc.encode_ordinary, documents))
            )
        for run in conditions.values():
            for _ in range(args.warmups):
                measure(run, expected)
        rng = random.Random(args.seed)
        for round_index in range(args.runs):
            order = list(conditions)
            rng.shuffle(order)
            for order_index, name in enumerate(order):
                sample = measure(conditions[name], expected)
                samples.append({
                    "round": round_index, "order": order_index,
                    "condition": name, **sample,
                })
            print(f"Completed round {round_index + 1}/{args.runs}", flush=True)
    report["parity"] = "all warmup and measured outputs equal serial reference"
    report["summary"] = {
        name: summarize([sample for sample in samples if sample["condition"] == name])
        for name in conditions
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)
        file.write("\n")
    for name, result in report["summary"].items():
        print(
            f"{name:18s} median={result['median_ms']:.2f} ms "
            f"max={result['max_ms']:.2f} ms ratio={result['max_over_median']:.2f}"
        )


if __name__ == "__main__":
    main()
