#!/usr/bin/env python3
"""Private QA injection only, at the known native nearQ menu builder.

Do not export the modified publisher source or activate this hook in release.
The hook schedules a local addon callback; the original builder remains intact.
"""
import re

HOOK = '\tSVVOfflineEvents._bind_native_mvp_card.call_deferred(self)\n'

def inject(source):
    # Require the exact top-level method and an indented function body.
    headers = list(re.finditer(r"(?m)^func show_teleporter\(\s*\)(?:\s*->\s*void)?\s*:[ \t]*\n", source))
    if len(headers) != 1 or HOOK.strip() in source:
        raise ValueError("Native teleporter hook anchor not unique or already patched")
    at = headers[0].end()
    if not source[at:].startswith("\t"):
        raise ValueError("Unexpected native teleporter indentation")
    return source[:at] + HOOK + source[at:]

def self_test():
    original = 'func show_teleporter() -> void:\n\tbuild_cards()\n\nfunc other():\n\tpass\n'
    changed = inject(original)
    assert changed.replace(HOOK, "") == original
    for invalid in (changed, original.replace("show_teleporter()", "show_teleporter(index: int)"),
                    original + original):
        try:
            inject(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Unexpected hook accepted")
    print("NATIVE_DESTINATION_HOOK_SELFTEST PASS")

if __name__ == "__main__":
    self_test()
