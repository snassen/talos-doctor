"""The doctor on made-up Macs: a ready one passes, and each broken part is found with its next step."""

import json
import re
from pathlib import Path

import pytest
from fakes import HOME, REPO, FakeMac, ready_mac

from talos_doctor import checks, cli
from talos_doctor.checks import Context, run_all
from talos_doctor.probe import NotAllowed, Probe


def results(mac, **kw):
    return {r.id: r for r in run_all(Context.find(mac, **kw))}


def test_a_ready_mac_passes_every_check_and_exits_zero(capsys):
    mac = ready_mac()
    got = results(mac)
    assert {r.status for r in got.values()} <= {"ok", "info"}, {k: (r.status, r.detail) for k, r in got.items() if r.status not in ("ok", "info")}
    assert got["account:club"].status == "info"            # not enabled: nothing to check
    assert cli.main([], probe=mac) == 0
    assert "Nothing to fix." in capsys.readouterr().out


def test_not_a_mac_fails_first_and_says_why():
    got = results(ready_mac(os="Linux"))
    assert got["macos"].status == "fail" and "macOS only" in got["macos"].fix
    assert got["homebrew"].status == "skip" and "macos" in got["homebrew"].detail


def test_postgresql_down_points_at_the_guide_and_skips_what_needs_it(capsys):
    mac = ready_mac(pg_up=False)
    got = results(mac)
    assert got["postgresql-running"].status == "fail" and got["postgresql-running"].guide == "postgresql"
    assert got["pgvector"].status == "skip" and got["database"].status == "skip"
    assert cli.main([], probe=mac) == 1
    out = capsys.readouterr().out
    first = out.split("Next steps")[1].splitlines()[1]
    assert "PostgreSQL answers" in first                       # the first thing to fix comes first


def test_a_database_behind_the_code_asks_for_setup():
    got = results(ready_mac(migrations=30))
    assert got["database"].status == "warn" and "30 of 32" in got["database"].detail
    assert "talos setup" in got["database"].fix
    assert results(ready_mac(migrations=None))["database"].status == "fail"


def test_the_code_is_found_in_the_usual_places_or_where_told():
    mac = ready_mac()
    assert Context.find(mac).repo == REPO
    other = FakeMac()
    other.put(Path("/elsewhere/talos/src/talos/__init__.py"), '__version__ = "1.0"')
    assert Context.find(other).repo is None
    assert Context.find(other, repo="/elsewhere/talos").repo == Path("/elsewhere/talos")
    assert results(other)["repo"].status == "fail" and results(other)["venv"].status == "skip"


def test_a_personal_part_still_the_examples_is_a_warning_with_where_to_edit():
    mac = ready_mac()
    mac.put(HOME / "TalosData/config/owner.json", {"id": "owner"})
    mac.put(HOME / "TalosData/config/accounts.json", {"accounts": [{"id": "gmail"}], "my_addresses": {}})
    got = results(mac)
    assert got["personal-filled"].status == "warn"
    assert "owner.json" in got["personal-filled"].detail and "accounts.json" in got["personal-filled"].detail


def test_broken_json_in_the_personal_part_is_named():
    mac = ready_mac()
    mac.put(HOME / "TalosData/config/accounts.json", '{"accounts": [}')
    got = results(mac)
    assert got["personal-part"].status == "fail" and "accounts.json" in got["personal-part"].detail
    assert got["accounts"].status == "skip"


def test_each_account_says_what_is_missing_and_the_exact_command():
    mac = ready_mac()
    mac.keychain -= {"gmail:alex@gmail.com", "graph-token-cache:work"}
    got = results(mac)
    assert got["account:gmail"].status == "fail"
    assert got["account:gmail"].fix.startswith("security add-generic-password -U -s talos -a gmail:alex@gmail.com -w")
    assert got["account:work"].status == "fail" and got["account:work"].fix == "uv run talos auth graph work"
    assert got["account:work"].guide == "microsoft-365"


def test_an_unregistered_microsoft_app_points_at_entra():
    mac = ready_mac()
    acc = json.loads(mac.files[str(HOME / "TalosData/config/accounts.json")])
    acc["accounts"][1]["settings"] = {"tenant_id": checks.ZERO_ID, "client_id": checks.ZERO_ID}
    acc["accounts"][2]["settings"] = {"token_account": "nowhere"}
    mac.put(HOME / "TalosData/config/accounts.json", acc)
    got = results(mac)
    assert got["account:work"].status == "fail" and "Entra" in got["account:work"].fix
    assert got["account:teams"].status == "fail"


def test_the_database_decides_which_accounts_are_on_not_the_seed_file():
    mac = ready_mac(db_enabled={"gmail": True, "work": True, "teams": True, "club": True})
    got = results(mac)
    assert got["account:club"].status == "fail" and "Keychain" in got["account:club"].detail   # on in the database
    mac = ready_mac(db_enabled={"gmail": False, "work": True, "teams": True, "club": False})
    assert results(mac)["account:gmail"].status == "info"


def test_without_jev_the_model_is_information_not_a_failure():
    mac = ready_mac()
    mac.keychain.discard("typesafe-api-key")
    assert results(mac)["jev"].status == "info"


def test_services_use_the_owners_prefix_and_say_how_to_load_them():
    mac = ready_mac()
    mac.loaded = {"com.alex.talos.web"}
    got = results(mac)
    assert got["service:sync"].status == "warn" and got["service:sync"].title.endswith("com.alex.talos.sync")
    assert got["service:web"].status == "ok"


def test_the_door_not_set_up_is_a_failure():
    mac = ready_mac()
    mac.keychain.discard("web:totp")
    got = results(mac)
    assert got["door"].status == "fail" and "talos web setup" in got["door"].fix


def test_one_phase_still_runs_the_checks_it_needs_from_the_others():
    got = {r.id: r for r in run_all(Context.find(ready_mac()), {"accounts"})}
    assert set(r.phase for r in got.values()) == {"accounts"} and got["account:gmail"].status == "ok"


def test_json_output_is_one_object_per_result(capsys):
    cli.main(["--json", "--only", "machine"], probe=ready_mac())
    data = json.loads(capsys.readouterr().out)
    assert {d["phase"] for d in data} == {"machine"} and all("status" in d for d in data)


def test_every_guide_named_by_a_check_exists_and_starts_with_a_heading(capsys):
    names = set(cli.guides())
    named = set(re.findall(r'"(\w[\w-]*)"\)\s*$|, "([\w-]+)"\)', Path(checks.__file__).read_text()))
    named = {g for pair in named for g in pair if g} & {"postgresql", "personal-part", "gmail", "imap", "microsoft-365",
                                                        "jev", "services", "tailscale", "install"}
    assert named <= names
    for n in names:
        assert cli.guide(n).startswith("# ")
    assert cli.main(["--guide", "nothing-like-it"]) == 2


# ---------------------------------------------------------------- the promises

def test_the_doctor_refuses_any_command_that_is_not_read_only():
    p = Probe(env={"PATH": "/usr/bin", "HOME": "/tmp"})
    for args in (["security", "add-generic-password", "-s", "talos"], ["security", "delete-generic-password"],
                 ["launchctl", "load", "x.plist"], ["brew", "install", "x"], ["rm", "-rf", "/"],
                 ["security", "find-generic-password", "-w"][:1]):
        with pytest.raises(NotAllowed):
            p.run(args)
    with pytest.raises(NotAllowed):
        p.http_status("https://example.com/")


def test_keychain_lookups_never_ask_for_the_secret():
    mac = ready_mac()
    run_all(Context.find(mac))
    lookups = [a for a in mac.ran if a[0] == "security"]
    assert lookups and all("-w" not in a and "-g" not in a for a in lookups)


def test_database_questions_are_asked_in_a_read_only_transaction():
    mac = ready_mac()
    run_all(Context.find(mac))          # the fake asserts PGOPTIONS on every psql call
    assert any(a[0] == "psql" for a in mac.ran)


def test_the_source_never_writes_a_file_or_starts_a_shell():
    src = "\n".join(p.read_text() for p in Path(checks.__file__).parent.glob("*.py"))
    for bad in (r"write_text", r"write_bytes", r"(?<![\w.])open\(", r"shell=True", r"os\.system", r"os\.remove",
                r"unlink\(", r"rmtree"):
        assert not re.search(bad, src), bad
