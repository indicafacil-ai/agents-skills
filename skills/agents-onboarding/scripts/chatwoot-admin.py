#!/usr/bin/env python3
# Chatwoot admin access-token reader for the Indica Fácil Agents onboarding. The USER creates the first admin in
# the Chatwoot onboarding screen (account gate); this reads that admin (by --email, or the single admin of
# the first account when --email is omitted) and returns its API access token; it never creates an account or
# user. Runs a Rails runner INSIDE the Chatwoot container over SSH,
# base64-piped so the script's own quotes never hit a shell.
#
# Output: the admin api_access_token is written to a 0600 file; only metadata is printed. The token is what
# agents deployment_connect + the Inbox API need. Works on any tier (Coolify, Portainer or plain compose).
# Python 3 stdlib only (no pip). Network/SSH runs via Bash with dangerouslyDisableSandbox:true (00-prereqs).
import argparse
import base64
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

CONTAINER_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

# The email arrives base64-decoded in-container so accents/spaces can't break quoting (empty => derive the
# single admin). RESULT_JSON: marks the line we parse. This READS an admin the user already created (account
# gate); it never creates one.
RUBY_PROVISION = r'''
require 'base64'; require 'json'
result =
  begin
    raw = "__B64_EMAIL__"
    email = raw.empty? ? nil : Base64.strict_decode64(raw).force_encoding("UTF-8")
    u = nil; err = nil; cands = nil
    if email
      u = User.find_by(email: email)
      err = "no Chatwoot user with email #{email}: create the admin in the Chatwoot onboarding screen first, then re-run" if u.nil?
    else
      # No --email: derive the single admin (exactly one after onboarding). Prefer the administrators of
      # the first account; fall back to the first user on a single-user install. Multiple admins => ask.
      acc0 = Account.order(:id).first
      if acc0.nil?
        err = "no Chatwoot account yet (finish the Chatwoot onboarding first)"
      else
        admins = acc0.account_users.where(role: AccountUser.roles[:administrator]).map(&:user).uniq
        if admins.size == 1
          u = admins.first
        elsif admins.empty?
          u = User.order(:id).first
          err = "no administrator in account #{acc0.id} (finish the Chatwoot onboarding first)" if u.nil?
        else
          err = "multiple administrators in account #{acc0.id}; re-run with --email <one of the candidates>"
          cands = admins.map(&:email)
        end
      end
    end
    if u.nil?
      res = { "error" => (err || "could not resolve a Chatwoot admin") }
      res["candidates"] = cands if cands
      res
    else
      acc = u.accounts.order(:id).first
      if acc.nil?
        { "error" => "Chatwoot user #{u.email} belongs to no account yet (finish the Chatwoot onboarding first)" }
      else
        # The polymorphic AccessToken (owner = the user) is the stable interface across images, whether or
        # not a given image still exposes User#access_token. Idempotent: find_or_create_by! reuses the
        # user's existing token (the model's before-create hook fills a freshly minted one).
        at = AccessToken.find_or_create_by!(owner: u)
        { "account_id" => acc.id, "user_id" => u.id, "email" => u.email, "token" => at.token }
      end
    end
  rescue => e
    { "error" => "#{e.class}: #{e.message}" }
  end
puts "RESULT_JSON:" + JSON.generate(result)
'''

# Reports which edition is actually running and which accounts have the Kanban feature on. Read-only.
#
# NOTE: Pro is detected by the presence of the `kanban_boards` TABLE, not by a Ruby constant. Table
# existence is the one signal that holds across fork builds and model namespaces — a constant name is
# an implementation detail that renames out from under you.
#
# There is deliberately NO subscription/licence state here: our fork carries the Kanban CODE in the
# private Pro image, and the runtime licence gate (Keygen) is not implemented yet — see
# references/chatwoot-kanban-enable.md. Never report a licence state that does not exist.
RUBY_REFRESH = r'''
require 'json'
pro = (ActiveRecord::Base.connection.table_exists?('kanban_boards') rescue false)
accounts = Account.order(:id).limit(20).map do |a|
  { "id" => a.id, "name" => a.name, "kanban_feature_enabled" => a.feature_enabled?('kanban') }
end
puts "RESULT_JSON:" + JSON.generate({"pro_image" => pro, "accounts" => accounts})
'''

# Enables the Kanban feature FLAG on the account (`enable_features!('kanban')`). The Pro image carries the
# Kanban CODE, but the flag is off until enabled here and the board stays invisible — that is the classic
# trap. Idempotent (no-op if already enabled). Reports the real end state, never a secret.
#
# NOTE: Pro is detected by the presence of the `kanban_boards` TABLE, not by a Ruby constant — table
# existence survives fork builds and model renames. Upstream gated this on its hub-licensing module and
# additionally proved the licence chain here; our fork has no such gate yet (Keygen is pending, see
# references/chatwoot-kanban-enable.md), so enabling the flag is the whole operation. If the fork later
# grows a licence validation on the model, `enable_features!` will raise and land in `enable_error`.
RUBY_ENABLE_KANBAN = r'''
require 'json'
result =
  begin
    unless (ActiveRecord::Base.connection.table_exists?('kanban_boards') rescue false)
      { "error" => "not a Pro image (no kanban_boards table): Kanban needs the chatwoot-pro image" }
    else
      acc_id = "__ACCOUNT_ID__"
      acc = acc_id.empty? ? Account.order(:id).first : Account.find_by(id: acc_id.to_i)
      if acc.nil?
        { "error" => "no Chatwoot account (id=#{acc_id.empty? ? 'first' : acc_id}); finish the Chatwoot onboarding first" }
      else
        enable_error = nil
        unless acc.feature_enabled?('kanban')
          begin
            acc.enable_features!('kanban')
          rescue ActiveRecord::RecordInvalid => e
            enable_error = e.record.errors.full_messages.join('; ')
          rescue => e
            enable_error = "#{e.class}: #{e.message}"
          end
        end
        acc.reload
        {
          "account_id" => acc.id,
          "kanban_feature_enabled" => acc.feature_enabled?('kanban'),
          "enable_error" => enable_error
        }
      end
    end
  rescue => e
    { "error" => "#{e.class}: #{e.message}" }
  end
puts "RESULT_JSON:" + JSON.generate(result)
'''

# Lê a identidade de instalação do Chatwoot (UUID + host). Guardada pra quando o licenciamento pelo
# `installation_identifier` (o UUID de instalação do Chatwoot, config INSTALLATION_IDENTIFIER); o host
# (FRONTEND_URL) é só metadado que o ping preenche depois. Logo o `installation_identifier` (UUID) é o
# Keygen existir (Fase 3 do Kanban); hoje é só informativo. Read-only.
RUBY_INSTALLATION_ID = r'''
require 'json'
ident = (InstallationConfig.find_by(name: 'INSTALLATION_IDENTIFIER')&.value rescue nil)
host = ENV['FRONTEND_URL']
host = (InstallationConfig.find_by(name: 'FRONTEND_URL')&.value rescue nil) if host.nil? || host.to_s.strip.empty?
puts "RESULT_JSON:" + JSON.generate({"installation_identifier" => ident, "frontend_url" => host})
'''


def out(obj, code=0):
    print(json.dumps(obj))
    sys.exit(code)


def fail(msg, **extra):
    out({"ok": False, "error": msg, **extra}, code=1)


def b64_pipe(payload, target):
    blob = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    return f"echo '{blob}' | base64 -d | {target}"


def split_ssh_opts(opts, _nt=None):
    # POSIX shlex eats backslashes, mangling a Windows key path ("-i C:\Users\me\.ssh\key" ->
    # "C:Usersme.sshkey"). On Windows, tokenize without escape processing and strip our own quotes so the
    # backslashes survive. _nt is injectable for tests.
    nt = (os.name == "nt") if _nt is None else _nt
    if not opts:
        return []
    if nt:
        toks = shlex.split(opts, posix=False)
        return [t[1:-1] if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'" else t for t in toks]
    return shlex.split(opts)


def run_ssh(dest, ssh_opts, remote_cmd, timeout):
    argv = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", *split_ssh_opts(ssh_opts), dest, remote_cmd]
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        fail("ssh not found on PATH")
    except subprocess.TimeoutExpired:
        fail(f"ssh timed out after {timeout}s", dest=dest)


def cmd_provision(args):
    if not CONTAINER_RE.match(args.container):
        fail(f"invalid --container {args.container!r} (expected [A-Za-z0-9_.-]+)")
    # --email is optional: omit it and the runner resolves the single admin of the first account (there is
    # exactly one after onboarding). Pass it only to disambiguate a multi-admin brownfield.
    if args.email is not None and "@" not in args.email:
        fail("--email must be an email address")
    b64_email = base64.b64encode((args.email or "").encode("utf-8")).decode("ascii")
    ruby = RUBY_PROVISION.replace("__B64_EMAIL__", b64_email)
    target = f"docker exec -i {args.container} bundle exec rails runner -"
    proc = run_ssh(args.ssh, args.ssh_opts, b64_pipe(ruby, target), args.timeout)
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    match = re.search(r"RESULT_JSON:(\{.*\})", combined)
    if not match:
        fail(
            "Rails runner returned no result (is --container the Chatwoot rails container?)",
            exit_code=proc.returncode,
            stdout=(proc.stdout or "")[-600:],
            stderr=(proc.stderr or "")[-600:],
        )
    try:
        data = json.loads(match.group(1))
    except ValueError:
        fail("could not parse RESULT_JSON", raw=match.group(1)[:200])
    # The runner emits a deliberate {"error": …} when the admin does not exist yet (the user must create
    # it in the Chatwoot UI first). Surface THAT, not the generic "no result": it tells the agent to wait.
    if data.get("error"):
        # Surface the candidate list on a multi-admin brownfield so the agent can ask (never open-field).
        fail(data["error"], **({"candidates": data["candidates"]} if data.get("candidates") else {}))
    dest = Path(args.out)
    dest.write_text(
        json.dumps(
            {
                "account_id": data["account_id"],
                "user_id": data["user_id"],
                "email": data["email"],
                "api_access_token": data["token"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        dest.chmod(0o600)
    except OSError:
        pass
    out(
        {
            "ok": True,
            "out_file": str(dest),
            "account_id": data["account_id"],
            "user_id": data["user_id"],
            "email": data["email"],
            "note": "api_access_token written to file (chmod 600), not printed",
        }
    )


def cmd_refresh_subscription(args):
    if not CONTAINER_RE.match(args.container):
        fail(f"invalid --container {args.container!r} (expected [A-Za-z0-9_.-]+)")
    target = f"docker exec -i {args.container} bundle exec rails runner -"
    proc = run_ssh(args.ssh, args.ssh_opts, b64_pipe(RUBY_REFRESH, target), args.timeout)
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    match = re.search(r"RESULT_JSON:(\{.*\})", combined)
    if not match:
        fail(
            "Rails runner returned no result (is --container the Chatwoot rails container?)",
            exit_code=proc.returncode,
            stdout=(proc.stdout or "")[-600:],
            stderr=(proc.stderr or "")[-600:],
        )
    try:
        data = json.loads(match.group(1))
    except ValueError:
        fail("could not parse RESULT_JSON", raw=match.group(1)[:200])
    out({"ok": True, **data})


def cmd_installation_id(args):
    if not CONTAINER_RE.match(args.container):
        fail(f"invalid --container {args.container!r} (expected [A-Za-z0-9_.-]+)")
    target = f"docker exec -i {args.container} bundle exec rails runner -"
    proc = run_ssh(args.ssh, args.ssh_opts, b64_pipe(RUBY_INSTALLATION_ID, target), args.timeout)
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    match = re.search(r"RESULT_JSON:(\{.*\})", combined)
    if not match:
        fail(
            "Rails runner returned no result (is --container the Chatwoot rails container?)",
            exit_code=proc.returncode,
            stdout=(proc.stdout or "")[-600:],
            stderr=(proc.stderr or "")[-600:],
        )
    try:
        data = json.loads(match.group(1))
    except ValueError:
        fail("could not parse RESULT_JSON", raw=match.group(1)[:200])
    out({"ok": True, **data})


def cmd_enable_kanban(args):
    if not CONTAINER_RE.match(args.container):
        fail(f"invalid --container {args.container!r} (expected [A-Za-z0-9_.-]+)")
    acc_id = args.account_id or ""
    # Digit-only guard: the value is inlined into the Ruby runner, so refuse anything but an int (no injection).
    if acc_id and not acc_id.isdigit():
        fail(f"--account-id must be an integer, got {acc_id!r}")
    ruby = RUBY_ENABLE_KANBAN.replace("__ACCOUNT_ID__", acc_id)
    target = f"docker exec -i {args.container} bundle exec rails runner -"
    proc = run_ssh(args.ssh, args.ssh_opts, b64_pipe(ruby, target), args.timeout)
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    match = re.search(r"RESULT_JSON:(\{.*\})", combined)
    if not match:
        fail(
            "Rails runner returned no result (is --container the Chatwoot rails container?)",
            exit_code=proc.returncode,
            stdout=(proc.stdout or "")[-600:],
            stderr=(proc.stderr or "")[-600:],
        )
    try:
        data = json.loads(match.group(1))
    except ValueError:
        fail("could not parse RESULT_JSON", raw=match.group(1)[:200])
    # Hard errors (no account / not a Pro image) → non-zero so the agent can't miss them.
    if data.get("error"):
        fail(data["error"])
    # The op ran; `kanban_feature_enabled` is the authoritative success. Surface a soft failure (e.g. the
    # subscription doesn't grant Kanban) with exit 1 so a broken license/instance match is never green.
    if not data.get("kanban_feature_enabled"):
        fail(
            data.get("enable_error") or "Kanban not enabled (subscription not granting it; check the license/instance match)",
            **data,
        )
    out({"ok": True, **data})


def build_parser():
    parser = argparse.ArgumentParser(
        prog="chatwoot-admin.py",
        description="Chatwoot admin/account/token + subscription refresh via a Rails runner over SSH.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    ssh = argparse.ArgumentParser(add_help=False)
    ssh.add_argument("--ssh", required=True, metavar="USER@HOST", help="SSH destination, e.g. root@1.2.3.4")
    ssh.add_argument("--container", required=True, help="Chatwoot rails container (from docker ps)")
    ssh.add_argument("--ssh-opts", default="", help="extra ssh options, e.g. '-i ~/.ssh/key -p 2222'")
    ssh.add_argument("--timeout", type=int, default=180)

    prov = sub.add_parser("provision", parents=[ssh], help="read the single admin the user created + return its API token (auto-resolves without --email)")
    prov.add_argument("--email", default=None, help="admin email; OPTIONAL — omit to auto-resolve the single admin, pass only to disambiguate a multi-admin brownfield")
    prov.add_argument("--out", required=True, help="file to write the api_access_token to (chmod 600)")
    prov.set_defaults(fn=cmd_provision)

    refresh = sub.add_parser(
        "refresh-subscription", parents=[ssh], help="run the Refresh job + report subscription config"
    )
    refresh.set_defaults(fn=cmd_refresh_subscription)

    idcmd = sub.add_parser(
        "installation-id", parents=[ssh], help="read the Chatwoot installation identity (host + uuid)"
    )
    idcmd.set_defaults(fn=cmd_installation_id)

    kanban = sub.add_parser(
        "enable-kanban",
        parents=[ssh],
        help="enable the Kanban feature on the account (account-level activation) + report the real end state",
    )
    kanban.add_argument(
        "--account-id",
        default=None,
        help="Chatwoot account id; OPTIONAL, omit to target the first account (the onboarding account)",
    )
    kanban.set_defaults(fn=cmd_enable_kanban)

    return parser


def main():
    args = build_parser().parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
