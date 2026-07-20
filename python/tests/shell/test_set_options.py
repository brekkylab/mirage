# ========= Copyright 2026 @ Strukto.AI All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2026 @ Strukto.AI All Rights Reserved. =========


def test_nounset_unset_var_is_fatal(shell):
    code, out, err = shell.mirage_result("set -u; echo $zq1; echo after")
    assert code == 127
    assert out == ""
    assert "zq1: unbound variable" in err


def test_nounset_braced_lookup_is_fatal(shell):
    code, _, err = shell.mirage_result("set -u; echo ${zq2}")
    assert code == 127
    assert "zq2: unbound variable" in err


def test_nounset_default_operator_is_safe(shell):
    assert shell.mirage("set -u; echo ${zq3:-d}") == "d\n"


def test_nounset_empty_set_var_is_safe(shell):
    assert shell.mirage("set -u; ze1=; echo x${ze1}y") == "xy\n"


def test_nounset_positional_is_fatal(shell):
    code, _, err = shell.mirage_result("set -u; echo $1")
    assert code == 127
    assert "1: unbound variable" in err


def test_nounset_specials_are_safe(shell):
    assert shell.mirage("set -u; echo ok $# $?") == "ok 0 0\n"


def test_nounset_off_again(shell):
    assert shell.mirage("set -u; set +u; echo x${zq4}y") == "xy\n"


def test_noglob_keeps_glob_literal(shell):
    shell.create_file("g1.txt", b"a\n")
    assert shell.mirage("set -f; echo /data/*.txt") == "/data/*.txt\n"


def test_noglob_toggle_restores_globbing(shell):
    shell.create_file("g2.txt", b"a\n")
    out = shell.mirage("set -f; set +f; echo /data/g2*.txt")
    assert out == "/data/g2.txt\n"


def test_noglob_for_loop_words_literal(shell):
    shell.create_file("g3.txt", b"a\n")
    out = shell.mirage("set -f; for f in /data/*.txt; do echo $f; done")
    assert out == "/data/*.txt\n"


def test_xtrace_traces_command_to_stderr(shell):
    code, out, err = shell.mirage_result("set -x; echo hi")
    assert code == 0
    assert out == "hi\n"
    assert err == "+ echo hi\n"


def test_xtrace_shows_expanded_words_and_assignments(shell):
    _, out, err = shell.mirage_result("set -x; xv1=5; echo $xv1")
    assert out == "5\n"
    assert err == "+ xv1=5\n+ echo 5\n"


def test_xtrace_quotes_words_with_spaces(shell):
    _, _, err = shell.mirage_result("set -x; echo 'a b'")
    assert err == "+ echo 'a b'\n"


def test_xtrace_does_not_trace_the_set_itself(shell):
    _, _, err = shell.mirage_result("set -x; set +x; echo hi")
    assert "+ set +x" in err
    assert "+ echo" not in err
