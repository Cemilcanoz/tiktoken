# Batch latency investigation

This experiment investigates [issue #530](https://github.com/openai/tiktoken/issues/530).
It complements the benchmark in [#548](https://github.com/openai/tiktoken/pull/548)
and the changes in [#561](https://github.com/openai/tiktoken/pull/561) with a serial
control and a persistent Python thread-pool control. It is not a production fix.

## Run

Install the tiktoken build you intend to measure in an isolated environment. For
example, `python -m pip install tiktoken==0.14.0` installs the released build.
From the checkout, using that environment's Python:

```sh
python scripts/investigate_batch_latency.py --build-label pypi-wheel-0.14.0 --output latency.json
```

The script imports the installed package. A checkout commit in the output identifies
the harness repository, **not the native extension being measured**. The JSON also
records the extension and Python core hashes, package version, and harness hash.
To measure a source change, build/install that source into a separate environment
first and use an appropriate label; do not relabel a released wheel as current main.

The built-in corpus is synthetic multilingual prose with Turkish, Japanese, Arabic,
Greek, Hindi, accents and emoji. All documents in a batch are identical, matching
the structure of the issue's reproducer. For a supplied UTF-8 corpus:

```sh
python scripts/investigate_batch_latency.py --build-label my-source-build --corpus corpus.txt --repeat 1 --batch-size 256 --runs 20 --output custom-latency.json
```

The first encoding load may download tokenizer vocabulary files to tiktoken's
cache. No model API, API key, or paid inference is used. Encoding load and downloads
occur before timing. An existing result file is never overwritten.

## Measurement boundaries

- `serial`: Python loop over `encode_ordinary`.
- `public_batch/N`: `encode_ordinary_batch(..., num_threads=N)`; on the 0.14.0
  implementation this includes creating and shutting down a pool each call.
- `reused_pool/N`: a persistent `ThreadPoolExecutor` maps `encode_ordinary`.
  Pool creation and shutdown are outside the timer; warmups precede measurements.

Each condition is run once per round in seeded shuffled order. Both wall time and
process CPU time are saved, preserving round and order. Outputs remain alive until
both clocks stop; exact equality checks and destruction occur after timing. All
warmup and measured outputs must match the serial token sequence, or the run fails.

Persistent pools remain alive during the experiment, so their idle threads,
warm worker/regex caches, and shared process history are a limitation. Process CPU time is not per-thread CPU
time. The operating system, other applications, thermals, and scheduling can all
affect these results. Repeat in fresh processes before drawing conclusions.

The report gives median, minimum, maximum, maximum/median, and every raw sample.
Maximum-of-N is not a p99 estimate. A faster persistent-pool control does not prove
pool creation causes the original long tail, nor does it establish thread safety,
memory lifecycle, or a suitable public API for persistent executors. A profiler
trace and representative Linux reproduction are still needed for root-cause claims.

## Validation

```sh
python -m unittest discover -s scripts -p test_investigate_batch_latency.py -v
python scripts/investigate_batch_latency.py --build-label smoke --repeat 1 --batch-size 2 --runs 2 --warmups 1 --threads 1 2 --output smoke.json
```

The unit checks validate measurement boundaries and rejection of wrong token
outputs. The smoke run exercises all conditions with the installed native extension.
