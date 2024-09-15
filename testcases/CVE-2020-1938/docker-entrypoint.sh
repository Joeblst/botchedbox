#!/bin/bash

set -euo pipefail

service ssh start

exec "$@"