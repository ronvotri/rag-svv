#!/usr/bin/env python3
"""Inject only isolated review hooks into the pinned native client.

Remember the actual class passed to enter_town, and bind the offline MVP
card at the same show_teleporter(class_id) entry used by nearQ's _talk.
Never guess a class or change the original card-building code.
"""
import re

HOOK = '\tSVVOfflineEvents._bind_native_mvp_card.call_deferred(self, class_id)\n'
TOWN_ANCHOR = '\tset_meta("svv_offline_town_place", str(place))\n'
CLASS_STAMP = '\tset_meta("svv_offline_town_class", class_id)\n'

def inject(source):
    headers = list(re.finditer(r"(?m)^func show_teleporter\([ \t]*class_id[ \t]*:[ \t]*String[ \t]*\)(?:[ \t]*->[ \t]*void)?[ \t]*:[ \t]*\n", source))
    if len(headers) != 1 or HOOK.strip() in source:
        raise ValueError("Native teleporter hook anchor not unique or already patched")
    at = headers[0].end()
    if not source[at:].startswith("\t"):
        raise ValueError("Unexpected native teleporter indentation")
    return source[:at] + HOOK + source[at:]

def inject_town_class(source):
    headers = list(re.finditer(r"(?m)^func enter_town\([ \t]*class_id[ \t]*:[ \t]*String\b[^\n]*\)[ \t]*->[ \t]*void[ \t]*:[ \t]*\n", source))
    if len(headers) != 1 or source.count(TOWN_ANCHOR) != 1 or CLASS_STAMP.strip() in source:
        raise ValueError("Native town class anchor not unique or already patched")
    if not source[headers[0].end():].startswith(TOWN_ANCHOR):
        raise ValueError("Town stamp not at native entry")
    return source.replace(TOWN_ANCHOR, TOWN_ANCHOR + CLASS_STAMP, 1)

def self_test():
    original = 'func show_teleporter(class_id: String) -> void:\n\tbuild_cards()\n\nfunc other():\n\tpass\n'
    changed = inject(original)
    assert changed.replace(HOOK, "") == original
    town = 'func enter_town(class_id: String, place := "prontera") -> void:\n' + TOWN_ANCHOR + '\tpass\n'
    stamped = inject_town_class(town)
    assert stamped.replace(CLASS_STAMP, "") == town
    for transform, invalid in ((inject, changed), (inject, original.replace("class_id: String", "index: int")),
                               (inject, original + original), (inject_town_class, stamped),
                               (inject_town_class, town.replace("class_id: String", "wrong: String"))):
        try:
            transform(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Unexpected hook accepted")
    print("NATIVE_DESTINATION_HOOK_SELFTEST PASS")

if __name__ == "__main__":
    self_test()
