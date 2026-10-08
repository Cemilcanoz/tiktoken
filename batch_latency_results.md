# Batch latency observations — Windows, tiktoken 0.14.0

Two fresh-process runs on 8 October 2026 did not reproduce the multi-second tail stalls reported in [#530](https://github.com/openai/tiktoken/issues/530). This is negative reproduction evidence for the workload below, not a fix or a disproof of the original report.

Machine: AMD Ryzen 7 7840HS, 8 physical cores / 16 logical processors. Python 3.14.2, Windows, PyPI tiktoken 0.14.0 wheel. The source checkout is release commit `4e71bbe0c078468e00fefbf94b39849389f346e5`; the native extension was installed from PyPI, not built from that checkout.

Each batch has 128 identical synthetic multilingual documents, each 43,264 UTF-8 bytes and 8,064 tokens, encoded with `o200k_base`. Each condition has 2 warmups and 15 measured runs per process. All 270 measured calls and 36 warmup calls matched the serial reference exactly.

## Results

| Condition | Run 1 median ms | Run 1 max/median | Run 2 median ms | Run 2 max/median |
|---|---:|---:|---:|---:|
| serial | 189.20 | 1.16 | 193.61 | 1.28 |
| public_batch/1 | 219.03 | 1.17 | 223.86 | 1.38 |
| reused_pool/1 | 217.34 | 1.13 | 219.96 | 1.24 |
| public_batch/2 | 140.37 | 1.07 | 140.29 | 1.08 |
| reused_pool/2 | 140.50 | 1.05 | 141.55 | 1.09 |
| public_batch/4 | 74.01 | 1.14 | 74.85 | 1.06 |
| reused_pool/4 | 73.55 | 1.04 | 73.83 | 1.08 |
| public_batch/8 | 46.52 | 1.24 | 48.38 | 1.14 |
| reused_pool/8 | 44.24 | 1.37 | 45.61 | 1.18 |

The persistent-pool control has a slightly lower median at 8 threads here, but its worst/median ratio is higher than the public batch API in both runs. This does not support claiming that pool reuse fixes tail latency. Worker startup and warm worker/regex state differ between these controls, so the comparison does not isolate a single cause.

## Limits and next evidence

The original report used tiktoken 0.12.0 on a 32-core Intel/Linux system and different, larger corpora. This experiment uses a synthetic workload, a newer released wheel, Windows, and no process affinity or profiler. Idle persistent pools remain alive while other conditions run. Background activity and thermal state were not controlled. A matched Linux/corpus reproduction and profiler trace are required before proposing a production change.

No comparison against the native changes in PR #561 was executed. No performance improvement to the library is claimed. Related PR #548 already adds a benchmark; this branch is independent supporting research, not a competing fix.

## Reproduce

```sh
python -m pip install tiktoken==0.14.0
python -m unittest discover -s scripts -p test_investigate_batch_latency.py -v
python scripts/investigate_batch_latency.py --build-label pypi-wheel-0.14.0 --repeat 128 --batch-size 128 --runs 15 --warmups 2 --output run1.json
python scripts/investigate_batch_latency.py --build-label pypi-wheel-0.14.0 --repeat 128 --batch-size 128 --runs 15 --warmups 2 --output run2.json
```

Validation: four measurement unit checks passed; a two-round native smoke run passed; all measured outputs matched the reference. Runtime library files are unchanged.

## Provenance

```json
{
  "environment": {
    "python": "3.14.2 (tags/v3.14.2:df79316, Dec  5 2025, 17:18:21) [MSC v.1944 64 bit (AMD64)]",
    "platform": "Windows-11-10.0.26200-SP0",
    "processor": "AMD64 Family 25 Model 116 Stepping 1, AuthenticAMD",
    "logical_cpus": 16,
    "tiktoken_version": "0.14.0",
    "native_module_filename": "_tiktoken.cp314-win_amd64.pyd",
    "native_module_sha256": "213123bc5172ee65455028f53b45e7060e8c27c0fce113db40ec68dca05da143",
    "core_py_sha256": "fd279aa5d510e937a0e1ed48e9a2a346756aacae5d3533cbd27ce6261d728d18",
    "harness_checkout_commit": "4e71bbe0c078468e00fefbf94b39849389f346e5",
    "harness_sha256": "d108440e19b21e36231d61232aef8a2f4557266c32ce52c9d9acb6ab7c44a469"
  },
  "workload": {
    "source": "synthetic-multilingual-v1",
    "document_sha256": "0c018effc54308f0f3bd7670195fb095aa2f761e074b8b828289a240299fd9f8",
    "document_utf8_bytes": 43264,
    "document_tokens": 8064,
    "repeat": 128,
    "batch_size": 128,
    "encoding": "o200k_base"
  },
  "settings": {
    "runs": 15,
    "warmups": 2,
    "threads": [
      1,
      2,
      4,
      8
    ],
    "seed": 530
  },
  "method": {
    "order": "seeded shuffle of all conditions for each round",
    "timed": "encoding, output allocation, and public-call pool lifecycle",
    "untimed": "encoding load, parity checks, output destruction, reused-pool lifecycle",
    "reference": "encode_ordinary(text), compared to every document in every call",
    "warning": "persistent-pool is a diagnostic control, not a proposed API change"
  }
}
```

## Raw measurements

CPU ms is total process CPU time. Row order is execution order. All timings below are milliseconds, rounded to six decimal places; the runner emits full precision JSON.

### Process run 1

Start: 2026-10-08T19:45:12.765166+00:00

| Round | Order | Condition | Wall ms | Process CPU ms |
|---:|---:|---|---:|---:|
| 0 | 0 | reused_pool/1 | 197.080900 | 187.500000 |
| 0 | 1 | reused_pool/4 | 62.480600 | 250.000000 |
| 0 | 2 | serial | 212.915200 | 203.125000 |
| 0 | 3 | public_batch/2 | 137.948700 | 265.625000 |
| 0 | 4 | public_batch/8 | 57.737000 | 281.250000 |
| 0 | 5 | reused_pool/2 | 140.761900 | 281.250000 |
| 0 | 6 | reused_pool/8 | 60.409200 | 390.625000 |
| 0 | 7 | public_batch/1 | 243.810100 | 203.125000 |
| 0 | 8 | public_batch/4 | 76.108400 | 312.500000 |
| 1 | 0 | public_batch/4 | 74.011000 | 265.625000 |
| 1 | 1 | public_batch/1 | 240.553500 | 234.375000 |
| 1 | 2 | public_batch/2 | 140.392000 | 281.250000 |
| 1 | 3 | public_batch/8 | 43.916000 | 328.125000 |
| 1 | 4 | reused_pool/2 | 146.913000 | 296.875000 |
| 1 | 5 | reused_pool/8 | 46.579000 | 250.000000 |
| 1 | 6 | serial | 219.618100 | 218.750000 |
| 1 | 7 | reused_pool/1 | 232.319500 | 218.750000 |
| 1 | 8 | reused_pool/4 | 75.182800 | 281.250000 |
| 2 | 0 | reused_pool/2 | 147.639700 | 312.500000 |
| 2 | 1 | public_batch/2 | 141.766700 | 265.625000 |
| 2 | 2 | reused_pool/8 | 44.883200 | 234.375000 |
| 2 | 3 | public_batch/1 | 238.382400 | 234.375000 |
| 2 | 4 | reused_pool/1 | 245.050500 | 234.375000 |
| 2 | 5 | reused_pool/4 | 73.615900 | 218.750000 |
| 2 | 6 | public_batch/8 | 43.407400 | 343.750000 |
| 2 | 7 | serial | 206.819700 | 218.750000 |
| 2 | 8 | public_batch/4 | 73.455900 | 234.375000 |
| 3 | 0 | reused_pool/2 | 143.809800 | 281.250000 |
| 3 | 1 | public_batch/2 | 135.486500 | 281.250000 |
| 3 | 2 | public_batch/8 | 54.952100 | 296.875000 |
| 3 | 3 | reused_pool/8 | 43.385500 | 328.125000 |
| 3 | 4 | public_batch/4 | 76.134200 | 343.750000 |
| 3 | 5 | reused_pool/1 | 212.169600 | 218.750000 |
| 3 | 6 | reused_pool/4 | 70.945100 | 328.125000 |
| 3 | 7 | serial | 191.417900 | 171.875000 |
| 3 | 8 | public_batch/1 | 255.330300 | 265.625000 |
| 4 | 0 | reused_pool/1 | 220.266200 | 234.375000 |
| 4 | 1 | reused_pool/8 | 41.508000 | 375.000000 |
| 4 | 2 | public_batch/4 | 73.182600 | 234.375000 |
| 4 | 3 | reused_pool/4 | 73.547300 | 312.500000 |
| 4 | 4 | public_batch/8 | 46.524700 | 234.375000 |
| 4 | 5 | public_batch/2 | 140.374300 | 296.875000 |
| 4 | 6 | public_batch/1 | 217.439600 | 218.750000 |
| 4 | 7 | serial | 187.637700 | 187.500000 |
| 4 | 8 | reused_pool/2 | 132.176000 | 281.250000 |
| 5 | 0 | public_batch/4 | 71.776000 | 265.625000 |
| 5 | 1 | reused_pool/8 | 42.940300 | 343.750000 |
| 5 | 2 | reused_pool/2 | 142.030000 | 281.250000 |
| 5 | 3 | public_batch/1 | 207.815700 | 203.125000 |
| 5 | 4 | reused_pool/1 | 223.906400 | 234.375000 |
| 5 | 5 | public_batch/8 | 50.025500 | 359.375000 |
| 5 | 6 | reused_pool/4 | 73.868300 | 234.375000 |
| 5 | 7 | public_batch/2 | 141.768800 | 281.250000 |
| 5 | 8 | serial | 201.950700 | 187.500000 |
| 6 | 0 | reused_pool/4 | 75.130200 | 234.375000 |
| 6 | 1 | serial | 199.099200 | 203.125000 |
| 6 | 2 | public_batch/1 | 218.872300 | 218.750000 |
| 6 | 3 | public_batch/2 | 131.196500 | 250.000000 |
| 6 | 4 | public_batch/4 | 75.655800 | 250.000000 |
| 6 | 5 | reused_pool/8 | 44.214000 | 343.750000 |
| 6 | 6 | reused_pool/1 | 211.998100 | 187.500000 |
| 6 | 7 | reused_pool/2 | 130.765100 | 250.000000 |
| 6 | 8 | public_batch/8 | 44.479100 | 359.375000 |
| 7 | 0 | public_batch/1 | 223.721100 | 218.750000 |
| 7 | 1 | reused_pool/4 | 76.423700 | 281.250000 |
| 7 | 2 | reused_pool/8 | 44.236900 | 250.000000 |
| 7 | 3 | public_batch/2 | 145.938500 | 281.250000 |
| 7 | 4 | public_batch/8 | 45.989700 | 328.125000 |
| 7 | 5 | reused_pool/2 | 136.428200 | 250.000000 |
| 7 | 6 | public_batch/4 | 69.423100 | 312.500000 |
| 7 | 7 | reused_pool/1 | 233.276100 | 250.000000 |
| 7 | 8 | serial | 187.461300 | 171.875000 |
| 8 | 0 | reused_pool/4 | 72.266900 | 296.875000 |
| 8 | 1 | public_batch/1 | 213.033600 | 203.125000 |
| 8 | 2 | serial | 188.024600 | 171.875000 |
| 8 | 3 | reused_pool/8 | 42.743200 | 218.750000 |
| 8 | 4 | reused_pool/2 | 135.812100 | 281.250000 |
| 8 | 5 | public_batch/8 | 46.577300 | 265.625000 |
| 8 | 6 | public_batch/4 | 75.633300 | 312.500000 |
| 8 | 7 | public_batch/2 | 137.605800 | 265.625000 |
| 8 | 8 | reused_pool/1 | 215.394000 | 218.750000 |
| 9 | 0 | public_batch/1 | 219.030200 | 218.750000 |
| 9 | 1 | public_batch/4 | 74.885100 | 281.250000 |
| 9 | 2 | reused_pool/2 | 140.764200 | 281.250000 |
| 9 | 3 | public_batch/2 | 137.766200 | 265.625000 |
| 9 | 4 | public_batch/8 | 48.537500 | 328.125000 |
| 9 | 5 | reused_pool/8 | 42.857700 | 343.750000 |
| 9 | 6 | serial | 187.265200 | 187.500000 |
| 9 | 7 | reused_pool/4 | 75.297500 | 265.625000 |
| 9 | 8 | reused_pool/1 | 213.311700 | 218.750000 |
| 10 | 0 | public_batch/8 | 46.496500 | 328.125000 |
| 10 | 1 | serial | 189.200400 | 187.500000 |
| 10 | 2 | reused_pool/2 | 135.871000 | 281.250000 |
| 10 | 3 | reused_pool/1 | 217.339200 | 203.125000 |
| 10 | 4 | public_batch/2 | 127.424900 | 250.000000 |
| 10 | 5 | reused_pool/4 | 72.376800 | 312.500000 |
| 10 | 6 | public_batch/1 | 211.046500 | 203.125000 |
| 10 | 7 | reused_pool/8 | 59.082700 | 296.875000 |
| 10 | 8 | public_batch/4 | 84.273400 | 312.500000 |
| 11 | 0 | public_batch/4 | 77.016300 | 296.875000 |
| 11 | 1 | public_batch/8 | 42.436300 | 343.750000 |
| 11 | 2 | serial | 203.120600 | 203.125000 |
| 11 | 3 | reused_pool/1 | 219.915700 | 234.375000 |
| 11 | 4 | public_batch/1 | 222.902200 | 234.375000 |
| 11 | 5 | reused_pool/8 | 45.700700 | 375.000000 |
| 11 | 6 | public_batch/2 | 144.806700 | 281.250000 |
| 11 | 7 | reused_pool/4 | 71.510500 | 312.500000 |
| 11 | 8 | reused_pool/2 | 135.296000 | 296.875000 |
| 12 | 0 | public_batch/8 | 48.488400 | 328.125000 |
| 12 | 1 | serial | 183.612900 | 187.500000 |
| 12 | 2 | reused_pool/8 | 53.942600 | 390.625000 |
| 12 | 3 | public_batch/2 | 147.813200 | 281.250000 |
| 12 | 4 | reused_pool/2 | 140.499400 | 281.250000 |
| 12 | 5 | reused_pool/1 | 210.580700 | 203.125000 |
| 12 | 6 | public_batch/1 | 215.042800 | 203.125000 |
| 12 | 7 | public_batch/4 | 72.030200 | 296.875000 |
| 12 | 8 | reused_pool/4 | 69.961000 | 234.375000 |
| 13 | 0 | public_batch/1 | 205.528600 | 203.125000 |
| 13 | 1 | public_batch/8 | 44.471700 | 359.375000 |
| 13 | 2 | public_batch/4 | 73.787400 | 312.500000 |
| 13 | 3 | reused_pool/2 | 137.832300 | 281.250000 |
| 13 | 4 | reused_pool/1 | 216.518100 | 203.125000 |
| 13 | 5 | reused_pool/4 | 72.462100 | 328.125000 |
| 13 | 6 | reused_pool/8 | 42.085300 | 375.000000 |
| 13 | 7 | public_batch/2 | 149.928000 | 296.875000 |
| 13 | 8 | serial | 185.381900 | 187.500000 |
| 14 | 0 | public_batch/2 | 133.843900 | 250.000000 |
| 14 | 1 | public_batch/4 | 73.397600 | 328.125000 |
| 14 | 2 | public_batch/1 | 222.243500 | 218.750000 |
| 14 | 3 | reused_pool/1 | 222.459100 | 218.750000 |
| 14 | 4 | public_batch/8 | 47.548300 | 328.125000 |
| 14 | 5 | serial | 186.015300 | 187.500000 |
| 14 | 6 | reused_pool/8 | 54.028900 | 312.500000 |
| 14 | 7 | reused_pool/2 | 142.843000 | 250.000000 |
| 14 | 8 | reused_pool/4 | 76.026500 | 296.875000 |

### Process run 2

Start: 2026-10-08T19:45:51.270324+00:00

| Round | Order | Condition | Wall ms | Process CPU ms |
|---:|---:|---|---:|---:|
| 0 | 0 | reused_pool/1 | 202.167000 | 203.125000 |
| 0 | 1 | reused_pool/4 | 64.463500 | 218.750000 |
| 0 | 2 | serial | 192.900400 | 171.875000 |
| 0 | 3 | public_batch/2 | 138.441800 | 250.000000 |
| 0 | 4 | public_batch/8 | 49.747300 | 296.875000 |
| 0 | 5 | reused_pool/2 | 143.062800 | 265.625000 |
| 0 | 6 | reused_pool/8 | 45.607000 | 312.500000 |
| 0 | 7 | public_batch/1 | 206.225500 | 218.750000 |
| 0 | 8 | public_batch/4 | 72.349100 | 312.500000 |
| 1 | 0 | public_batch/4 | 75.071900 | 312.500000 |
| 1 | 1 | public_batch/1 | 213.690100 | 218.750000 |
| 1 | 2 | public_batch/2 | 138.025800 | 250.000000 |
| 1 | 3 | public_batch/8 | 44.297600 | 359.375000 |
| 1 | 4 | reused_pool/2 | 145.160100 | 281.250000 |
| 1 | 5 | reused_pool/8 | 41.239600 | 234.375000 |
| 1 | 6 | serial | 181.313700 | 187.500000 |
| 1 | 7 | reused_pool/1 | 210.896100 | 187.500000 |
| 1 | 8 | reused_pool/4 | 68.570100 | 281.250000 |
| 2 | 0 | reused_pool/2 | 138.755100 | 265.625000 |
| 2 | 1 | public_batch/2 | 140.403400 | 281.250000 |
| 2 | 2 | reused_pool/8 | 52.986200 | 281.250000 |
| 2 | 3 | public_batch/1 | 229.578800 | 218.750000 |
| 2 | 4 | reused_pool/1 | 219.960200 | 218.750000 |
| 2 | 5 | reused_pool/4 | 71.286200 | 265.625000 |
| 2 | 6 | public_batch/8 | 42.844900 | 343.750000 |
| 2 | 7 | serial | 183.267100 | 171.875000 |
| 2 | 8 | public_batch/4 | 72.349700 | 296.875000 |
| 3 | 0 | reused_pool/2 | 141.113200 | 281.250000 |
| 3 | 1 | public_batch/2 | 134.489600 | 265.625000 |
| 3 | 2 | public_batch/8 | 47.295800 | 265.625000 |
| 3 | 3 | reused_pool/8 | 41.659500 | 265.625000 |
| 3 | 4 | public_batch/4 | 73.737900 | 312.500000 |
| 3 | 5 | reused_pool/1 | 263.438300 | 265.625000 |
| 3 | 6 | reused_pool/4 | 70.664300 | 296.875000 |
| 3 | 7 | serial | 193.610300 | 203.125000 |
| 3 | 8 | public_batch/1 | 216.165800 | 234.375000 |
| 4 | 0 | reused_pool/1 | 213.030000 | 218.750000 |
| 4 | 1 | reused_pool/8 | 53.834400 | 406.250000 |
| 4 | 2 | public_batch/4 | 76.136700 | 250.000000 |
| 4 | 3 | reused_pool/4 | 73.946800 | 312.500000 |
| 4 | 4 | public_batch/8 | 49.077600 | 328.125000 |
| 4 | 5 | public_batch/2 | 145.788100 | 296.875000 |
| 4 | 6 | public_batch/1 | 213.753900 | 218.750000 |
| 4 | 7 | serial | 191.820400 | 187.500000 |
| 4 | 8 | reused_pool/2 | 129.963500 | 265.625000 |
| 5 | 0 | public_batch/4 | 75.163400 | 281.250000 |
| 5 | 1 | reused_pool/8 | 43.236700 | 234.375000 |
| 5 | 2 | reused_pool/2 | 138.383400 | 281.250000 |
| 5 | 3 | public_batch/1 | 211.742400 | 218.750000 |
| 5 | 4 | reused_pool/1 | 216.442100 | 203.125000 |
| 5 | 5 | public_batch/8 | 55.203300 | 406.250000 |
| 5 | 6 | reused_pool/4 | 74.008300 | 234.375000 |
| 5 | 7 | public_batch/2 | 140.254400 | 281.250000 |
| 5 | 8 | serial | 224.648300 | 218.750000 |
| 6 | 0 | reused_pool/4 | 76.414600 | 312.500000 |
| 6 | 1 | serial | 209.449100 | 203.125000 |
| 6 | 2 | public_batch/1 | 230.585100 | 203.125000 |
| 6 | 3 | public_batch/2 | 142.058800 | 265.625000 |
| 6 | 4 | public_batch/4 | 71.703800 | 265.625000 |
| 6 | 5 | reused_pool/8 | 44.709400 | 296.875000 |
| 6 | 6 | reused_pool/1 | 207.734600 | 187.500000 |
| 6 | 7 | reused_pool/2 | 141.549400 | 296.875000 |
| 6 | 8 | public_batch/8 | 52.199000 | 390.625000 |
| 7 | 0 | public_batch/1 | 213.955000 | 218.750000 |
| 7 | 1 | reused_pool/4 | 71.798700 | 312.500000 |
| 7 | 2 | reused_pool/8 | 45.620800 | 359.375000 |
| 7 | 3 | public_batch/2 | 140.964800 | 250.000000 |
| 7 | 4 | public_batch/8 | 47.791600 | 343.750000 |
| 7 | 5 | reused_pool/2 | 142.703600 | 296.875000 |
| 7 | 6 | public_batch/4 | 74.850300 | 187.500000 |
| 7 | 7 | reused_pool/1 | 222.627700 | 218.750000 |
| 7 | 8 | serial | 186.741800 | 187.500000 |
| 8 | 0 | reused_pool/4 | 71.613900 | 250.000000 |
| 8 | 1 | public_batch/1 | 223.858900 | 234.375000 |
| 8 | 2 | serial | 198.687600 | 156.250000 |
| 8 | 3 | reused_pool/8 | 44.425700 | 281.250000 |
| 8 | 4 | reused_pool/2 | 145.524300 | 312.500000 |
| 8 | 5 | public_batch/8 | 48.381500 | 359.375000 |
| 8 | 6 | public_batch/4 | 75.065600 | 281.250000 |
| 8 | 7 | public_batch/2 | 134.775100 | 234.375000 |
| 8 | 8 | reused_pool/1 | 224.175500 | 218.750000 |
| 9 | 0 | public_batch/1 | 222.405600 | 187.500000 |
| 9 | 1 | public_batch/4 | 74.039400 | 281.250000 |
| 9 | 2 | reused_pool/2 | 140.828300 | 250.000000 |
| 9 | 3 | public_batch/2 | 140.963500 | 265.625000 |
| 9 | 4 | public_batch/8 | 52.089900 | 281.250000 |
| 9 | 5 | reused_pool/8 | 43.392400 | 328.125000 |
| 9 | 6 | serial | 184.688000 | 187.500000 |
| 9 | 7 | reused_pool/4 | 74.750900 | 281.250000 |
| 9 | 8 | reused_pool/1 | 208.679500 | 203.125000 |
| 10 | 0 | public_batch/8 | 49.280000 | 250.000000 |
| 10 | 1 | serial | 181.325600 | 171.875000 |
| 10 | 2 | reused_pool/2 | 144.849600 | 265.625000 |
| 10 | 3 | reused_pool/1 | 210.281000 | 203.125000 |
| 10 | 4 | public_batch/2 | 139.423100 | 265.625000 |
| 10 | 5 | reused_pool/4 | 79.510700 | 250.000000 |
| 10 | 6 | public_batch/1 | 243.435800 | 250.000000 |
| 10 | 7 | reused_pool/8 | 51.542100 | 437.500000 |
| 10 | 8 | public_batch/4 | 73.481000 | 250.000000 |
| 11 | 0 | public_batch/4 | 74.960200 | 312.500000 |
| 11 | 1 | public_batch/8 | 46.050200 | 359.375000 |
| 11 | 2 | serial | 230.894500 | 234.375000 |
| 11 | 3 | reused_pool/1 | 269.786200 | 281.250000 |
| 11 | 4 | public_batch/1 | 261.050600 | 250.000000 |
| 11 | 5 | reused_pool/8 | 48.735800 | 328.125000 |
| 11 | 6 | public_batch/2 | 137.140300 | 281.250000 |
| 11 | 7 | reused_pool/4 | 73.098600 | 250.000000 |
| 11 | 8 | reused_pool/2 | 143.761700 | 296.875000 |
| 12 | 0 | public_batch/8 | 49.940600 | 359.375000 |
| 12 | 1 | serial | 222.309500 | 234.375000 |
| 12 | 2 | reused_pool/8 | 48.666900 | 296.875000 |
| 12 | 3 | public_batch/2 | 144.428100 | 312.500000 |
| 12 | 4 | reused_pool/2 | 141.397000 | 281.250000 |
| 12 | 5 | reused_pool/1 | 270.048100 | 281.250000 |
| 12 | 6 | public_batch/1 | 278.519900 | 281.250000 |
| 12 | 7 | public_batch/4 | 75.298200 | 265.625000 |
| 12 | 8 | reused_pool/4 | 75.622200 | 312.500000 |
| 13 | 0 | public_batch/1 | 308.829100 | 296.875000 |
| 13 | 1 | public_batch/8 | 43.941800 | 250.000000 |
| 13 | 2 | public_batch/4 | 78.999300 | 312.500000 |
| 13 | 3 | reused_pool/2 | 135.209300 | 281.250000 |
| 13 | 4 | reused_pool/1 | 267.936300 | 250.000000 |
| 13 | 5 | reused_pool/4 | 73.828500 | 250.000000 |
| 13 | 6 | reused_pool/8 | 45.389900 | 265.625000 |
| 13 | 7 | public_batch/2 | 151.504400 | 312.500000 |
| 13 | 8 | serial | 247.167800 | 250.000000 |
| 14 | 0 | public_batch/2 | 140.291000 | 281.250000 |
| 14 | 1 | public_batch/4 | 72.642000 | 312.500000 |
| 14 | 2 | public_batch/1 | 262.702100 | 265.625000 |
| 14 | 3 | reused_pool/1 | 272.637000 | 265.625000 |
| 14 | 4 | public_batch/8 | 47.975200 | 343.750000 |
| 14 | 5 | serial | 216.009000 | 218.750000 |
| 14 | 6 | reused_pool/8 | 47.385100 | 265.625000 |
| 14 | 7 | reused_pool/2 | 154.178900 | 281.250000 |
| 14 | 8 | reused_pool/4 | 74.550300 | 312.500000 |
