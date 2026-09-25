#!/usr/bin/env bash
# three.js (CG 장면용) 를 npm 레지스트리에서 받아 vendor/three 에 풀기
set -euo pipefail
cd "$(dirname "$0")"
rm -rf vendor && mkdir -p vendor/three && cd vendor
npm pack three@0.186.1 -q >/dev/null
tar xzf three-0.186.1.tgz
cp package/build/three.module.js package/build/three.core.js three/
cp -r package/examples/jsm three/addons
rm -rf package three-0.186.1.tgz
