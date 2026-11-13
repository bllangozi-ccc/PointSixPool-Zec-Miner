#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# SSE2-only x86_64 baseline; no host-specific AVX requirement or new packages.
g++ -std=c++17 -O3 -static -pthread -DATOMIC -march=x86-64 -mtune=generic \
 -fno-strict-aliasing -fstack-protector-strong -D_FORTIFY_SOURCE=2 \
 -Wl,-z,relro,-z,now -Wall -Wno-unused-function -Wno-unused-variable \
 "$root/solver-fast.cpp" "$root/reviewed/blake/blake2b.cpp" \
 -o "$root/artifacts/point6miner-equihash-fast"
