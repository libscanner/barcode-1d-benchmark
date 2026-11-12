"""Code comparison shared by bench.py, speed.py and prepare_truth.py.

A reader's answer counts as a read when it equals a ground-truth code after
normalisation: UPC-A is compared as EAN-13 with a leading zero, UPC-E both as
is and expanded to UPC-A; for Code 128 the GS1 group separators (<GS>, 0x1D),
the ]C1 symbology identifier and brackets around application identifiers are
dropped.
"""
import re


def ean_check(digits):
    """EAN/UPC check digit for the digits without it."""
    s = sum(int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(reversed(digits)))
    return str((10 - s % 10) % 10)


def upce_to_upca(s):
    """UPC-E (8 digits: number system, 6 data digits, check digit) -> UPC-A (12 digits)."""
    ns, d, ck = s[0], s[1:7], s[7]
    if d[5] in '012':
        m = d[0:2] + d[5] + '0000' + d[2:5]
    elif d[5] == '3':
        m = d[0:3] + '00000' + d[3:5]
    elif d[5] == '4':
        m = d[0:4] + '00000' + d[4]
    else:
        m = d[0:5] + '0000' + d[5]
    return ns + m + ck


def clean(text):
    """Code text without GS1 separators, symbology identifier and AI brackets."""
    t = text.replace('<GS>', '').replace('\x1d', '')
    if t.startswith(']C1') or t.startswith(']C0'):
        t = t[3:]
    if re.match(r'^\(\d{2,4}\)', t):
        t = re.sub(r'\((\d{2,4})\)', r'\1', t)
    return t


def canon(text):
    """The set of equivalent spellings of a code (for comparison)."""
    t = clean(text)
    out = {t}
    if t.isdigit():
        if len(t) == 12:
            out.add('0' + t)
        elif len(t) == 13 and t[0] == '0':
            out.add(t[1:])
        elif len(t) == 8 and t[0] in '01':
            out.add('0' + upce_to_upca(t))
    return out


def family(text):
    """'ean' for EAN-8/13 and UPC-A/E digits with a valid check digit, otherwise 'c128'."""
    t = clean(text)
    if t.isdigit():
        if len(t) in (8, 12, 13) and ean_check(t[:-1]) == t[-1]:
            return 'ean'
        if len(t) == 8 and t[0] in '01' and ean_check(upce_to_upca(t)[:-1]) == t[-1]:
            return 'ean'
    return 'c128'
