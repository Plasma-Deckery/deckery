#!/bin/bash
# test-installer-guards.sh — self-check for get.sh release-tag selection and
# the packaged-install guard (package-guard.sh). Installs nothing: runs get.sh
# against a throwaway HOME and a local fake origin whose install.sh is a stub,
# with rpm, rpm-ostree and distrobox-host-exec stubbed on PATH.
#
#   bash testing/test-installer-guards.sh

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
FAIL=0

ok()   { echo "  ok    $1"; }
fail() { echo "  FAIL  $1"; FAIL=1; }

# ── Stubs ────────────────────────────────────────────────────────────────────
mkdir -p "$T/bin"
cat > "$T/bin/rpm" <<'EOF'
#!/bin/bash
# STUB_RPM: "name version" lines of installed packages. Mimics rpm -q output.
shift 3   # -q --qf <fmt>
for p in "$@"; do
    line="$(printf '%s\n' "${STUB_RPM:-}" | awk -v p="$p" '$1 == p')"
    if [ -n "$line" ]; then echo "$line"; else echo "package $p is not installed"; fi
done
EOF
cat > "$T/bin/rpm-ostree" <<'EOF'
#!/bin/bash
[ -n "${STUB_OSTREE_JSON:-}" ] || exit 1
echo "$STUB_OSTREE_JSON"
EOF
cat > "$T/bin/distrobox-host-exec" <<'EOF'
#!/bin/bash
exec "$@"
EOF
chmod +x "$T/bin/"*
export PATH="$T/bin:$PATH"
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t

# ── Fake origin: get.sh's guard file plus an install.sh that only reports ────
mkdir -p "$T/src"
git -C "$T/src" init -q -b main
cp "$REPO/package-guard.sh" "$T/src/"
cat > "$T/src/install.sh" <<'EOF'
#!/bin/bash
echo "INSTALL tag=${DECKERY_RELEASE_TAG:-} force=${DECKERY_FORCE_SOURCE:-0}"
EOF
git -C "$T/src" add -A && git -C "$T/src" commit -qm base
for tag in v0.4.1 v0.5.0 v2.0.0-beta1 backup-pre-trailer-strip-20260919; do
    git -C "$T/src" commit -q --allow-empty -m "$tag" && git -C "$T/src" tag "$tag"
done
git clone -q --bare "$T/src" "$T/origin.git"

export HOME="$T/home"
DDIR="$HOME/.local/share/deckery/deckery"
mkdir -p "$(dirname "$DDIR")"
git clone -q "$T/origin.git" "$DDIR"

run_get() { bash "$REPO/get.sh" "$@" 2>&1; }

# ── 1. Tag selection ─────────────────────────────────────────────────────────
echo "Tag selection"
out="$(STUB_RPM= run_get)"
echo "$out" | grep -q "INSTALL tag=v2.0.0-beta1 " \
    && ok "v2.0.0-beta1 wins over v0.5.0" || { fail "beta over v0.5.0"; echo "$out"; }

git -C "$T/src" commit -q --allow-empty -m v2.0.0 && git -C "$T/src" tag v2.0.0
git -C "$T/src" push -q "$T/origin.git" main --tags
out="$(STUB_RPM= run_get)"
echo "$out" | grep -q "INSTALL tag=v2.0.0 " \
    && ok "v2.0.0 wins over v2.0.0-beta1" || { fail "release over beta"; echo "$out"; }

echo "  order for a sample tag list (get.sh's sort):"
sample="$T/sample"; git init -q "$sample"; git -C "$sample" commit -q --allow-empty -m x
for tag in v0.4.1 v0.5.0 v2.0.0-beta1 v2.0.0-beta2 v2.0.0-rc1 v2.0.0 v2.0.1 v2.1.0-beta1 backup-x; do
    git -C "$sample" tag "$tag"
done
order="$(git -C "$sample" -c versionsort.suffix=-alpha -c versionsort.suffix=-beta \
    -c versionsort.suffix=-rc tag --list 'v[0-9]*' --sort=-version:refname | tr '\n' ' ')"
echo "    $order"
[ "$order" = "v2.1.0-beta1 v2.0.1 v2.0.0 v2.0.0-rc1 v2.0.0-beta2 v2.0.0-beta1 v0.5.0 v0.4.1 " ] \
    && ok "pre-releases sort below their release" || fail "sample order"

# ── 2. Packaged-install guard ────────────────────────────────────────────────
echo "Package guard"
out="$(STUB_RPM="deckery 2.0.0~beta1-9.fc43" run_get)"; rc=$?
[ $rc -ne 0 ] && echo "$out" | grep -q "installed as a system package" \
    && echo "$out" | grep -q "deckery 2.0.0~beta1-9.fc43" \
    && ! echo "$out" | grep -q INSTALL \
    && ok "get.sh refuses when rpm -q finds deckery (exit $rc)" \
    || { fail "get.sh rpm guard"; echo "$out"; }

out="$(STUB_RPM="makima-deckery 2.0.0~beta1-12.fc43" run_get)"; rc=$?
[ $rc -ne 0 ] && ! echo "$out" | grep -q INSTALL \
    && ok "get.sh refuses for makima-deckery alone" || fail "makima-deckery guard"

json='{"deployments":[{"booted":false,"requested-packages":["deckery","htop"],"packages":["htop"]}]}'
out="$(STUB_RPM= STUB_OSTREE_JSON="$json" run_get)"; rc=$?
[ $rc -ne 0 ] && echo "$out" | grep -q "deckery (layered, version unknown)" \
    && ok "get.sh refuses for a staged rpm-ostree layer" || { fail "rpm-ostree guard"; echo "$out"; }

out="$(STUB_RPM="deckery 2.0.0~beta1-9.fc43" run_get --force-source)"
echo "$out" | grep -q "INSTALL tag=v2.0.0 force=1" \
    && ok "--force-source overrides and reaches install.sh" || { fail "--force-source"; echo "$out"; }

out="$(STUB_RPM="deckery 2.0.0~beta1-9.fc43" DECKERY_FORCE_SOURCE=1 run_get)"
echo "$out" | grep -q "INSTALL tag=v2.0.0 force=1" \
    && ok "DECKERY_FORCE_SOURCE=1 overrides" || fail "DECKERY_FORCE_SOURCE"

out="$(STUB_RPM= STUB_OSTREE_JSON='{"deployments":[{"requested-packages":["htop"]}]}' run_get)"
echo "$out" | grep -q "INSTALL tag=v2.0.0 " \
    && ok "no Deckery package: installs" || fail "unrelated packages"

# install.sh refuses on its own (the guard runs before anything else in it).
out="$(STUB_RPM="deckery-tray 2.0.0~beta1-4.fc43" bash "$REPO/install.sh" 2>&1)"; rc=$?
[ $rc -ne 0 ] && echo "$out" | grep -q "installed as a system package" \
    && ! echo "$out" | grep -q "Deckery Installer" \
    && ok "install.sh refuses before the installer starts" || { fail "install.sh guard"; echo "$out"; }

echo ""
[ $FAIL -eq 0 ] && echo "All checks passed." || echo "Some checks FAILED."
exit $FAIL
