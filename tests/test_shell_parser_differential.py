"""Differential tests: the hook's own shell scanners against the real shells.

The hook never runs a command; it reads the text with hand-written scanners. A
judgment is only as good as that reading, so these tests ask the real ``bash`` and
the real PowerShell parser how they split the same text into words and compare.

Nothing under test is executed. bash only assigns the words to ``$@`` and prints
them; PowerShell only parses the text to a syntax tree. The cases hold quoting,
escapes and comments, and no character that would run or expand anything.

Skipped when the shell is not installed.
"""

from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from jangseung.evidence.claude_code_tool_call_mapping import powershell_argvs
from jangseung.evidence.shell_command_risk import BASH_TRAILING_ESCAPE_REASON, scan_bash_command

SEED = 20261110
RANDOM_CASES = 400

# No ``$``, backtick, ``;|&<>(){}``, glob characters, ``!`` or ``~``: none of these
# may reach ``eval``, and expansions are out of scope for a word-splitting check.
_BASH_ALPHABET = ("a", "b", "c", "1", " ", " ", "\t", "'", '"', "\\", "-", ".", "/", "=", "#", ":")
BASH_FIXED_CASES = (
    "git status",
    "cat 'a b' c",
    'cat "a b" c',
    "cat a\\ b",
    "echo 'it'\"'\"'s'",
    'echo "a\\"b"',
    'echo "a\\\\b"',
    'echo "a\\nb"',
    "echo a'b'c\"d\"e",
    "echo '' x",
    'echo "" x',
    "echo a #comment",
    "echo a#b",
    "echo 'a #b'",
    "echo \\#a",
    "FOO=1 cmd arg",
    "cmd --flag=value -x",
    "cmd a\\'b",
    "cmd 'unterminated",
    'cmd "unterminated',
    "cmd trailing\\",
    "  leading and trailing  ",
    "cmd\ttab\tseparated",
    "cmd 'a\tb'",
    "cmd c:/x/y.txt",
    "cmd \\\\server\\share",
)

_POWERSHELL_WORD_CHARACTERS = ("a", "b", "c", "1", "-", ".", "/", "\\", "_", ":")
POWERSHELL_FIXED_CASES = (
    "Get-Content README.md",
    "Get-Content 'a b.txt' -Raw",
    'Get-Content "a b.txt" -Raw',
    "Get-Content '.env'-Raw",
    "Remove-Item 'it''s' -Force",
    "Get-ChildItem src | Select-Object -First 3",
    "Get-Content a.txt; Get-Content b.txt",
    "cmd a'b c'd",
    "cmd 'a;b' c",
    "cmd 'a|b' c",
    'cmd "a;b" c',
    "cmd a # comment",
    "cmd 'unterminated",
    "cmd -Path x -LiteralPath y",
    "cmd C:\\Users\\x\\file.txt",
)


def _find_bash() -> str | None:
    candidates = [os.environ.get("JANGSEUNG_TEST_BASH"), shutil.which("bash")]
    if os.name == "nt":
        # ``bash`` on PATH may be the WSL launcher, which is a different thing.
        candidates[1:1] = [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files\Git\usr\bin\bash.exe",
        ]
    for candidate in candidates:
        if not candidate or not Path(candidate).is_file():
            continue
        try:
            probe = subprocess.run(
                [candidate, "-c", "printf ok"], capture_output=True, timeout=30, check=False
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if probe.returncode == 0 and probe.stdout == b"ok":
            return candidate
    return None


def _find_powershell() -> str | None:
    for name in ("pwsh", "powershell"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _random_bash_cases() -> list[str]:
    generator = random.Random(SEED)
    cases = []
    for _ in range(RANDOM_CASES):
        length = generator.randint(1, 18)
        cases.append("cmd " + "".join(generator.choice(_BASH_ALPHABET) for _ in range(length)))
    return cases


def _random_powershell_cases() -> list[str]:
    generator = random.Random(SEED)
    cases = []
    for _ in range(RANDOM_CASES):
        words = []
        for _ in range(generator.randint(1, 4)):
            body = "".join(
                generator.choice(_POWERSHELL_WORD_CHARACTERS) for _ in range(generator.randint(1, 5))
            )
            shape = generator.randint(0, 5)
            if shape == 0:
                words.append(f"'{body} {body}'")
            elif shape == 1:
                words.append(f'"{body} {body}"')
            elif shape == 2:
                words.append(f"'{body}''{body}'")
            else:
                # A bare word must not start like a number or an operator.
                words.append("x" + body)
        separator = generator.choice((" ", " ", " ", " ; cmd ", " | cmd "))
        cases.append("cmd " + separator.join(words))
    return cases


def _bash_words(bash: str, cases: list[str]) -> list[list[str] | None]:
    """Ask bash how it splits each case; ``None`` where bash rejects the text."""

    script = (
        "set -f\n"
        "while IFS= read -r line || [ -n \"$line\" ]; do\n"
        "  if eval \"set -- $line\" 2>/dev/null; then\n"
        "    printf 'OK\\0'; [ $# -gt 0 ] && printf '%s\\0' \"$@\"\n"
        "  else\n"
        "    printf 'ERR\\0'\n"
        "  fi\n"
        "  printf '\\1'\n"
        "done\n"
    )
    done = subprocess.run(
        [bash, "-c", script],
        input="\n".join(cases).encode("utf-8"),
        capture_output=True,
        timeout=300,
        check=True,
    )
    results: list[list[str] | None] = []
    for chunk in done.stdout.split(b"\x01")[:-1]:
        fields = chunk.split(b"\x00")[:-1]
        if not fields or fields[0] != b"OK":
            results.append(None)
        else:
            results.append([field.decode("utf-8") for field in fields[1:]])
    return results


_POWERSHELL_SCRIPT = r"""
param([string]$CasesPath)
$ErrorActionPreference = 'Stop'
foreach ($line in [System.IO.File]::ReadAllLines($CasesPath, [System.Text.Encoding]::UTF8)) {
    $tokens = $null
    $errors = $null
    $ast = [System.Management.Automation.Language.Parser]::ParseInput($line, [ref]$tokens, [ref]$errors)
    if ($errors.Count -gt 0) {
        [Console]::Out.WriteLine('null')
        continue
    }
    $commands = $ast.FindAll({ param($node) $node -is [System.Management.Automation.Language.CommandAst] }, $true)
    $result = New-Object System.Collections.ArrayList
    foreach ($command in $commands) {
        $words = New-Object System.Collections.ArrayList
        foreach ($element in $command.CommandElements) {
            if ($element -is [System.Management.Automation.Language.StringConstantExpressionAst]) {
                [void]$words.Add($element.Value)
            } elseif ($element -is [System.Management.Automation.Language.ExpandableStringExpressionAst]) {
                [void]$words.Add($element.Value)
            } else {
                [void]$words.Add($element.Extent.Text)
            }
        }
        [void]$result.Add($words.ToArray())
    }
    [Console]::Out.WriteLine((ConvertTo-Json -InputObject $result.ToArray() -Compress -Depth 4))
}
"""


def _powershell_words(powershell: str, cases: list[str]) -> list[list[list[str]] | None]:
    with tempfile.TemporaryDirectory() as folder:
        script = Path(folder) / "parse.ps1"
        cases_path = Path(folder) / "cases.txt"
        script.write_text(_POWERSHELL_SCRIPT, encoding="utf-8")
        cases_path.write_text("\n".join(cases) + "\n", encoding="utf-8")
        done = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", str(script), str(cases_path)],
            capture_output=True,
            timeout=300,
            check=True,
        )
    results: list[list[list[str]] | None] = []
    for line in done.stdout.decode("utf-8", "replace").splitlines():
        parsed = json.loads(line)
        if parsed is None:
            results.append(None)
            continue
        # ConvertTo-Json flattens a single command with a single word.
        commands = [[parsed]] if isinstance(parsed, str) else parsed
        if commands and all(isinstance(item, str) for item in commands):
            commands = [commands]
        results.append([[str(word) for word in command] for command in commands])
    return results


class BashWordSplittingDifferentialTests(unittest.TestCase):
    def test_scanner_splits_words_like_bash(self):
        bash = _find_bash()
        if bash is None:
            self.skipTest("bash is not installed")
        cases = [*BASH_FIXED_CASES, *_random_bash_cases()]
        expected = _bash_words(bash, cases)
        self.assertEqual(len(expected), len(cases))
        mismatches = []
        ambiguous_endings = 0
        for case, real in zip(cases, expected):
            scan = scan_bash_command(case)
            if scan.error == BASH_TRAILING_ESCAPE_REASON:
                ambiguous_endings += 1
                self.assertTrue(case.endswith("\\"))
                # The same bytes have two real meanings across Bash versions.
                # Check both readings explicitly; the production risk gate
                # rejects this syntax instead of choosing the host we test on.
                alternatives = [scan_bash_command(case[:-1]), scan_bash_command(case + "\\")]
                self.assertTrue(all(item.error is None for item in alternatives))
                self.assertIn(real, [[word for argv in item.argvs() for word in argv] for item in alternatives])
                continue
            ours = None if scan.error is not None else [word for argv in scan.argvs() for word in argv]
            self.assertFalse(scan.dynamic and scan.error is None, f"static text read as dynamic: {case!r}")
            if ours != real:
                mismatches.append((case, ours, real))
        self.assertEqual(mismatches, [], f"{len(mismatches)} of {len(cases)} cases differ from bash")
        self.assertEqual(ambiguous_endings, 14)


class PowerShellWordSplittingDifferentialTests(unittest.TestCase):
    def test_tokenizer_splits_words_like_powershell(self):
        powershell = _find_powershell()
        if powershell is None:
            self.skipTest("PowerShell is not installed")
        cases = [*POWERSHELL_FIXED_CASES, *_random_powershell_cases()]
        expected = _powershell_words(powershell, cases)
        self.assertEqual(len(expected), len(cases))
        mismatches = []
        for case, real in zip(cases, expected):
            ours = [list(argv) for argv in powershell_argvs(case)]
            if real is None:
                # PowerShell rejects the text. The hook may still read words from it:
                # a lower bound that can only add deny reasons, never an allow.
                continue
            if ours != real:
                mismatches.append((case, ours, real))
        self.assertEqual(mismatches, [], f"{len(mismatches)} of {len(cases)} cases differ from PowerShell")


if __name__ == "__main__":
    unittest.main()
