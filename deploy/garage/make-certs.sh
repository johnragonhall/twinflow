#!/bin/sh
# Issue the internal CA and one key pair per identity for the garage tier.
#
# Rule 5 of ARCHITECTURE.md section 7 says devices authenticate to the broker
# with mTLS client certificates from the internal CA, and the broker ACL is
# keyed on the common name each certificate carries. This script is the garage
# tier's internal CA: one laptop, one compose file, no PKI to stand up first.
#
# Nothing this writes is committed. *.pem and *.key are already gitignored, and
# a private key in a repository is a compromised private key. Rerun the script
# on any machine that needs the stack.
#
# Usage:
#
#   sh deploy/garage/make-certs.sh
#
# Needs openssl on PATH.

set -eu

here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) # docs-lint-ok DASH-02 the POSIX end-of-options marker, not a transliterated dash
out="$here/certs"

if ! command -v openssl >/dev/null 2>&1; then
  echo "BLOCKED: openssl is not on PATH, and this script is the internal CA" >&2
  exit 1
fi

# 30 days. A garage-tier certificate that outlives the demo it was made for is a
# credential nobody is tracking.
days=30

mkdir -p "$out/ca"

if [ ! -f "$out/ca/ca.key" ]; then
  openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes \
    -keyout "$out/ca/ca.key" \
    -out "$out/ca/ca.crt" \
    -subj "/O=twinflow/OU=internal-ca/CN=twinflow internal CA"
  echo "issued the internal CA at $out/ca/ca.crt"
fi

# The broker, plus every identity the ACL file names. The common name here is
# the username the ACL is keyed on, so these strings and deploy/garage/mosquitto/acl
# have to agree.
issue() {
  name=$1
  role=$2
  dir="$out/$name"
  mkdir -p "$dir"

  openssl req -newkey rsa:2048 -sha256 -nodes \
    -keyout "$dir/$role.key" \
    -out "$dir/$role.csr" \
    -subj "/O=twinflow/OU=$role/CN=$name"

  # The broker needs a subjectAltName, because a client verifies the hostname it
  # dialed. A client certificate does not: the ACL reads the common name.
  if [ "$role" = "broker" ]; then
    printf 'subjectAltName=DNS:broker,DNS:localhost\nextendedKeyUsage=serverAuth\n' > "$dir/ext.cnf"
  else
    printf 'extendedKeyUsage=clientAuth\n' > "$dir/ext.cnf"
  fi

  openssl x509 -req -sha256 -days "$days" \
    -in "$dir/$role.csr" \
    -CA "$out/ca/ca.crt" -CAkey "$out/ca/ca.key" -CAcreateserial \
    -extfile "$dir/ext.cnf" \
    -out "$dir/$role.crt"

  cp "$out/ca/ca.crt" "$dir/ca.crt"
  rm -f "$dir/$role.csr" "$dir/ext.cnf"
  echo "issued $name as $role"
}

issue broker broker
issue portal-03 client
issue temp-01 client
issue inbound-line-01 client
issue historian client
issue twin-sync client
issue twinflow-host client

echo
echo "certificates are under $out and are not tracked by git."
echo "next: docker compose -f deploy/garage/docker-compose.yaml up"
