#!/bin/sh
# P3 gate: the documents describe the helpers as they behave (R12), the
# profile's verify and the release gate are root-anchored (R7), the cycle's
# scope held, and every deferral has its record.
#
#   sh spec/verify-helpers-harden/verify/gate_docs.sh [all|phase|pre-push]
#
#   all       (default) gate_temp_db.sh and gate_temp_pg_local.sh first, then `phase`
#   phase     this phase's own checks: scope, private-path scan, documents, ledger
#   pre-push  scope and private-path scan only: the checks an outward step needs
#
# Reads the index (what the phase staged). The scope base is the plan commit.
# Footprint: `phase` and `pre-push` are a few git, grep and Python processes,
# under 5 s with a warm gate environment. `all` adds the two helper gates
# (about 3 min 20 s warm, measured at planning).
. "$(dirname -- "$0")/lib.sh"

mode=${1:-all}
case $mode in all|phase|pre-push) ;; *) vhh_fail "usage: gate_docs.sh [all|phase|pre-push]" ;; esac
if [ "$mode" = all ]; then
    sh "$vhh_dir/gate_temp_db.sh" index || exit 1
    sh "$vhh_dir/gate_temp_pg_local.sh" index || exit 1
fi

cd "$vhh_wt" || exit 1
show() { git show ":$1" 2>/dev/null; }   # a file as staged

# Scope: nothing under py/ or .github/, and uv.lock byte-identical, since the plan commit.
base=$(git log --format=%H -1 --grep="^\[test\] Plan $vhh_slug")
[ -n "$base" ] || vhh_fail "scope: no plan commit found"
bad=$(git diff --cached --name-only "$base" -- py .github uv.lock)
[ -z "$bad" ] || vhh_fail "scope: changed since the plan commit: $(printf '%s' "$bad" | tr '\n' ' ')"
vhh_ok "scope: py/, .github/ and uv.lock untouched since $(printf '%s' "$base" | cut -c1-7)"

# Private paths: no line this cycle adds names a home directory or a temp path.
leaks=$(git diff --cached "$base" -- . ":(exclude)spec/$vhh_slug/verify" | grep '^+' | grep -v '^+++' \
        | grep -nE '/Users/|/home/[a-z]|/private/(tmp|var)|/var/folders/|\$KB\b' || true)
[ -z "$leaks" ] || vhh_fail "private paths in added lines: $(printf '%s' "$leaks" | head -n 3)"
vhh_ok "no private paths in the cycle's added lines"
[ "$mode" = pre-push ] && { printf 'PASS gate_docs pre-push\n'; exit 0; }

# R12: AGENTS.md § Factory -> Throwaway environment, as staged.
section=$(show AGENTS.md | sed -n '/^### Throwaway environment$/,/^### /p' | sed '$d')
[ -n "$section" ] || vhh_fail "R12: no Throwaway environment section in AGENTS.md"
if printf '%s' "$section" | grep -Eiq 'fall(s)? short|verify-helpers-harden|first cut'; then
    vhh_fail "R12: the Throwaway environment section still carries a caveat pointing at this cycle"
fi
for fact in REPO_ROOT HOME TMPDIR UV_NO_SYNC REFITT_API_ROOTKEY PGTZ America/Indiana/Indianapolis \
            127.0.0.1 REFITT_TEST_PG=1 REFITT_TEMP_WITH_SERVER=1 stderr TERM 'refitt database init'; do
    printf '%s' "$section" | grep -qF -- "$fact" || vhh_fail "R12: the Throwaway environment section never mentions $fact"
done
vhh_ok "R12 AGENTS.md Throwaway environment: no caveat; states the hardened behaviour"

# R12: each helper's header comments.
for h in tools/temp_db.sh tools/temp_pg.sh; do
    head=$(show "$h" | sed -n '2,/^[^#]/p')
    if printf '%s' "$head" | grep -Eiq 'CAVEAT|first cut|verify-helpers-harden|fall(s)? short'; then
        vhh_fail "R12: $h header still carries a caveat"
    fi
    for fact in REPO_ROOT UV_NO_SYNC REFITT_API_ROOTKEY stderr TERM; do
        printf '%s' "$head" | grep -qF -- "$fact" || vhh_fail "R12: $h header never mentions $fact"
    done
done
show tools/temp_pg.sh | sed -n '2,/^[^#]/p' | grep -qF 127.0.0.1 || vhh_fail "R12: temp_pg.sh header never mentions 127.0.0.1"
show tools/temp_pg.sh | sed -n '2,/^[^#]/p' | grep -qF PGTZ || vhh_fail "R12: temp_pg.sh header never mentions PGTZ"
vhh_ok "R12 helper headers: no caveat; state the hardened behaviour"

# R7: the profile's verify and the release recipe's gate are root-anchored.
anchored="tools/temp_pg.sh sh -c 'uv run pytest -v \"\$REPO_ROOT\"'"
show AGENTS.md | grep -E '^\| verify \|' | grep -qF -- "$anchored" \
    || vhh_fail "R7: the profile's verify does not run: $anchored"
recipe=$(show AGENTS.md | sed -n '/^### Release recipe$/,/^### /p' | sed -n '/^```yaml$/,/^```$/p' | sed '1d;$d')
vhh_env
printf '%s\n' "$recipe" | "$vhh_py" -I -c '
import sys, yaml
gate = yaml.safe_load(sys.stdin)["release"]["gate"]
want = sys.argv[1]
assert any(want in step for step in gate), "no gate step runs the anchored pytest"
assert not any("temp_pg.sh uv run pytest" in step for step in gate), "an unanchored pytest step remains"
' "$anchored" || vhh_fail "R7: the release recipe's gate is not root-anchored (or the YAML no longer parses)"
vhh_ok "R7 profile verify and release gate run pytest at \"\$REPO_ROOT\""

# Deferral ledger: the seed this cycle filed, and every deferral TECH.md names.
seed=issues/init-sqlite-prompt.md
show "$seed" | grep -qx 'status: unshaped' || vhh_fail "ledger: $seed missing or not status: unshaped"
show "$seed" | grep -qx 'lane: public' || vhh_fail "ledger: $seed is not lane: public"
show ROADMAP.md | grep -qF "**Seed:** [\`$seed\`]($seed)" || vhh_fail "ledger: ROADMAP.md has no entry seeding $seed"
show "spec/$vhh_slug/GOAL.md" | grep -qF "$seed" || vhh_fail "ledger: the GOAL's non-goal does not point at $seed"
show "spec/$vhh_slug/TECH.md" | sed '1,/^---$/d' | grep -v '^#' \
    | grep -Ei "do not fix here|known limitation|left as a follow-up|deferred to|defer it|out of scope" \
    | while IFS= read -r line; do
        ref=$(printf '%s' "$line" | grep -oE 'issues/[a-z0-9-]+\.md' | head -n 1)
        [ -n "$ref" ] || vhh_fail "ledger: a deferral names no issues/ record: $line"
        show "$ref" >/dev/null || vhh_fail "ledger: $ref does not exist"
        show ROADMAP.md | grep -qF "$ref" || vhh_fail "ledger: ROADMAP.md does not index $ref"
    done || exit 1
vhh_ok "ledger: $seed filed, indexed and linked; every TECH.md deferral has its record"
printf 'PASS gate_docs %s\n' "$mode"
