#!/usr/bin/env bash
# Bisection helper: find which test creates an unwanted file or directory.
#
# Usage:   ./find-polluter.sh <path_to_check> <test_runner> <test_pattern> Example:
# ./find-polluter.sh '.git' 'pytest'           'tests/**/test_*.py' Example: ./find-polluter.sh
# 'tmp/' 'cargo test --test' 'tests/*.rs' Example: ./find-polluter.sh '.lock' 'go test' './...'
#
# Runs each matching test file in isolation and stops at the first one whose execution causes
# <path_to_check> to appear.

set -euo pipefail

if [[ $# -ne 3 ]]; then
	echo "Usage: $0 <path_to_check> <test_runner> <test_pattern>" >&2
	echo "Example: $0 '.git' 'pytest' 'tests/**/test_*.py'" >&2
	exit 1
fi

pollution_check="$1"
test_runner="$2"
test_pattern="$3"

echo "Searching for test that creates: ${pollution_check}"
echo "Runner:  ${test_runner}"
echo "Pattern: ${test_pattern}"
echo ""

# Expand the glob in this shell so brace and globstar patterns work.
shopt -s globstar nullglob
# The pattern is intentionally word-split + globbed below; quoting would disable expansion.
# shellcheck disable=SC2206
pattern_expanded=(${test_pattern})
mapfile -t test_files < <(printf '%s\n' "${pattern_expanded[@]}" | sort)
total=${#test_files[@]}

if [[ ${total} -eq 0 ]]; then
	echo "No test files matched pattern: ${test_pattern}" >&2
	exit 1
fi

echo "Found ${total} test file(s)"
echo ""

# Split the runner string into argv so multi-word runners like 'cargo test --test' work without
# re-introducing word-splitting risks.
read -r -a runner_argv <<<"${test_runner}"

count=0
for test_file in "${test_files[@]}"; do
	count=$((count + 1))

	if [[ -e "${pollution_check}" ]]; then
		echo "Pollution already exists before test ${count}/${total} - skipping: ${test_file}"
		continue
	fi

	echo "[${count}/${total}] Running: ${test_runner} ${test_file}"
	"${runner_argv[@]}" "${test_file}" >/dev/null 2>&1 || true

	if [[ -e "${pollution_check}" ]]; then
		echo ""
		echo "FOUND POLLUTER:"
		echo "   Test:    ${test_file}"
		echo "   Created: ${pollution_check}"
		echo ""
		echo "Pollution details:"
		ls -la "${pollution_check}"
		echo ""
		echo "To investigate:"
		echo "  ${test_runner} ${test_file}"
		exit 1
	fi
done

echo ""
echo "No polluter found - all tests clean."
exit 0
