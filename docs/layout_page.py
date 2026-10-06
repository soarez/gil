#!/usr/bin/env python3
"""Generate docs/layout.html, comparing the gil (ZMK) and Sweep (QMK) keymaps.

Both keymap files are parsed and every key is reduced to a common label, so
the page shows where the two boards still differ. Re-run it after changing
either keymap:

    python3 docs/layout_page.py [path/to/qmk/keymap.c]

The QMK keymap defaults to the sibling qmk_firmware checkout.
"""
import html
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ZMK_KEYMAP = HERE.parent / 'config' / 'gil.keymap'
QMK_KEYMAP = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else (
    HERE.parent.parent / 'qmk_firmware' / 'keyboards' / 'splitkb' / 'aurora' / 'sweep' / 'keymaps' / 'sz' / 'keymap.c')
OUT = HERE / 'layout.html'

THUMBS = {30: 'left outer thumb', 31: 'left inner thumb', 32: 'right inner thumb', 33: 'right outer thumb'}

LAYER_NAMES = {
    0: 'Base', 1: 'Symbols + arrows', 2: 'Brackets', 3: 'Navigation + edit', 4: 'Numbers',
    5: 'Keypad + F-keys', 6: 'Macros', 7: 'Media + device', 8: 'System',
}

# Labels shared by both firmwares; the tables below map each firmware's
# spelling onto these.
SYMBOLS = {
    'TILDE': '~', 'EXCL': '!', 'AT': '@', 'HASH': '#', 'DOLLAR': '$', 'PERCENT': '%',
    'CARET': '^', 'AMPERSAND': '&', 'ASTERISK': '*', 'DQUOTE': '"', 'LPAREN': '(',
    'RPAREN': ')', 'QUOTE': "'", 'LBRACE': '{', 'RBRACE': '}', 'BACKSLASH': '\\',
    'UNDERSCORE': '_', 'LBRACKET': '[', 'RBRACKET': ']', 'GRAVE': '`', 'PLUS': '+',
    'EQUAL': '=', 'PIPE': '|', 'MINUS': '-', 'COMMA': ',', 'DOT': '.', 'SLASH': '/',
    'SEMICOLON': ';', 'SPACE': 'Space', 'ESC': 'Esc', 'TAB': 'Tab', 'DEL': 'Del',
    'BSPC': '⌫', 'ENTER': '⏎', 'LEFT': '←', 'DOWN': '↓', 'UP': '↑', 'RIGHT': '→',
    'CAPS_WORD': 'Caps Word', 'FFWD': '⏩', 'REW': '⏪', 'PLAY': '⏯', 'MUTE': 'Mute',
    'VOLU': 'Vol +', 'VOLD': 'Vol −', 'PAUSE': 'Pause', 'SCRLK': 'ScrLk', 'SLEEP': 'Sleep',
    'BOOT': 'Boot', 'RESET': 'Reset', 'F20': 'F20',
}

QMK_KEYS = {
    'KC_TILD': 'TILDE', 'KC_EXLM': 'EXCL', 'KC_AT': 'AT', 'KC_HASH': 'HASH', 'KC_DLR': 'DOLLAR',
    'KC_PERC': 'PERCENT', 'KC_CIRC': 'CARET', 'KC_AMPR': 'AMPERSAND', 'KC_ASTR': 'ASTERISK',
    'KC_DQUO': 'DQUOTE', 'KC_LPRN': 'LPAREN', 'KC_RPRN': 'RPAREN', 'KC_QUOT': 'QUOTE',
    'KC_LCBR': 'LBRACE', 'KC_RCBR': 'RBRACE', 'KC_BSLS': 'BACKSLASH', 'KC_UNDS': 'UNDERSCORE',
    'KC_LBRC': 'LBRACKET', 'KC_RBRC': 'RBRACKET', 'KC_GRV': 'GRAVE', 'KC_PLUS': 'PLUS',
    'KC_EQL': 'EQUAL', 'KC_PIPE': 'PIPE', 'KC_MINS': 'MINUS', 'KC_COMM': 'COMMA', 'KC_DOT': 'DOT',
    'KC_SLSH': 'SLASH', 'KC_SCLN': 'SEMICOLON', 'KC_SPC': 'SPACE', 'KC_ESC': 'ESC', 'KC_TAB': 'TAB',
    'KC_DEL': 'DEL', 'KC_BSPC': 'BSPC', 'KC_ENT': 'ENTER', 'KC_LEFT': 'LEFT', 'KC_DOWN': 'DOWN',
    'KC_UP': 'UP', 'KC_RGHT': 'RIGHT', 'CW_TOGG': 'CAPS_WORD', 'KC_MFFD': 'FFWD', 'KC_MRWD': 'REW',
    'KC_MPLY': 'PLAY', 'KC_MUTE': 'MUTE', 'KC_VOLU': 'VOLU', 'KC_VOLD': 'VOLD', 'KC_PAUSE': 'PAUSE',
    'KC_SCROLL_LOCK': 'SCRLK', 'KC_SLEP': 'SLEEP', 'QK_BOOT': 'BOOT', 'QK_RBT': 'RESET', 'KC_F20': 'F20',
}
QMK_LABELS = {
    'KC_PPLS': 'KP +', 'KC_PAST': 'KP *', 'KC_PMNS': 'KP −', 'KC_PSLS': 'KP /', 'KC_KP_DOT': 'KP .',
    'QK_MAKE': 'qmk make', 'KC_WH_D': 'Wheel ↓', 'KC_WH_U': 'Wheel ↑', 'KC_MS_U': 'Mouse ↑',
    'KC_MS_D': 'Mouse ↓', 'KC_MS_L': 'Mouse ←', 'KC_MS_R': 'Mouse →', 'KC_BTN1': 'Click 1',
    'KC_BTN2': 'Click 2', 'KC_ACL0': 'Mouse slow', 'KC_ACL1': 'Mouse mid', 'KC_ACL2': 'Mouse fast',
    'RGB_TOG': 'RGB on/off', 'RGB_MOD': 'RGB next', 'RGB_RMOD': 'RGB prev', 'RGB_HUI': 'Hue +',
    'RGB_HUD': 'Hue −', 'RGB_SAI': 'Sat +', 'RGB_SAD': 'Sat −', 'RGB_VAI': 'Bright +',
    'RGB_VAD': 'Bright −', 'RGB_SPI': 'Anim +', 'RGB_SPD': 'Anim −', 'LCGRIND': 'Macro: lcgrind',
}
QMK_MODS = {
    'LCTL': 'Ctrl', 'RCTL': 'Ctrl', 'LOPT': 'Alt', 'ROPT': 'Alt', 'LALT': 'Alt', 'RALT': 'Alt',
    'LCMD': 'Cmd', 'RCMD': 'Cmd', 'LGUI': 'Cmd', 'RGUI': 'Cmd', 'LSFT': 'Shift', 'RSFT': 'Shift',
    'HYPR': 'Hyper', 'LCAG': '⌃⌥⌘', 'RCAG': '⌃⌥⌘',
}

ZMK_KEYS = {
    'TILDE': 'TILDE', 'EXCL': 'EXCL', 'AT': 'AT', 'HASH': 'HASH', 'DLLR': 'DOLLAR', 'PRCNT': 'PERCENT',
    'CARET': 'CARET', 'AMPS': 'AMPERSAND', 'ASTRK': 'ASTERISK', 'DQT': 'DQUOTE', 'LPAR': 'LPAREN',
    'RPAR': 'RPAREN', 'SQT': 'QUOTE', 'LBRC': 'LBRACE', 'RBRC': 'RBRACE', 'BSLH': 'BACKSLASH',
    'UNDER': 'UNDERSCORE', 'LBKT': 'LBRACKET', 'RBKT': 'RBRACKET', 'GRAVE': 'GRAVE', 'PLUS': 'PLUS',
    'EQUAL': 'EQUAL', 'PIPE': 'PIPE', 'MINUS': 'MINUS', 'COMMA': 'COMMA', 'DOT': 'DOT',
    'SLASH': 'SLASH', 'SEMICOLON': 'SEMICOLON', 'SPACE': 'SPACE', 'ESC': 'ESC', 'TAB': 'TAB',
    'DEL': 'DEL', 'BSPC': 'BSPC', 'ENTER': 'ENTER', 'LEFT': 'LEFT', 'DOWN': 'DOWN', 'UP': 'UP',
    'RIGHT': 'RIGHT', 'C_FF': 'FFWD', 'C_RW': 'REW', 'C_PP': 'PLAY', 'K_MUTE': 'MUTE',
    'K_VOL_UP': 'VOLU', 'K_VOL_DN': 'VOLD', 'PAUSE_BREAK': 'PAUSE', 'SLCK': 'SCRLK', 'F20': 'F20',
    'SYS_SLEEP': 'SLEEP',
}
ZMK_LABELS = {
    'KP_PLUS': 'KP +', 'KP_ASTERISK': 'KP *', 'KP_MINUS': 'KP −', 'KP_SLASH': 'KP /', 'KP_DOT': 'KP .',
}
ZMK_MODS = {
    'LCTRL': 'Ctrl', 'RCTRL': 'Ctrl', 'LALT': 'Alt', 'RALT': 'Alt', 'LGUI': 'Cmd', 'RGUI': 'Cmd',
    'LSHFT': 'Shift', 'RSHFT': 'Shift', 'LC(LA(LGUI))': '⌃⌥⌘', 'RC(RA(RGUI))': '⌃⌥⌘',
    'LS(LC(LA(LGUI)))': 'Hyper',
}
ZMK_BEHAVIORS = {
    '&sys_reset': SYMBOLS['RESET'], '&bootloader': SYMBOLS['BOOT'], '&caps_word': SYMBOLS['CAPS_WORD'],
    '&soft_off': 'Soft off', '&out OUT_TOG': 'USB ⇄ BT', '&ext_power EP_TOG': 'Ext power',
    '&bt BT_CLR': 'BT clear', '&lcgrind': 'Macro: lcgrind',
    '&msc SCRL_DOWN': 'Wheel ↓', '&msc SCRL_UP': 'Wheel ↑', '&mmv MOVE_UP': 'Mouse ↑',
    '&mmv MOVE_DOWN': 'Mouse ↓', '&mmv MOVE_LEFT': 'Mouse ←', '&mmv MOVE_RIGHT': 'Mouse →',
    '&mkp LCLK': 'Click 1', '&mkp RCLK': 'Click 2',
}
# gil's mouse speed keys hold an empty layer that scales movement
ZMK_SPEED_LAYERS = {9: 'Mouse slow', 10: 'Mouse mid', 11: 'Mouse fast'}

# The right outer thumb is custom code on both boards
THUMB_F20 = {'tap': 'F20', 'hold': 'L4'}


def key(tap='', hold=''):
    return {'tap': tap, 'hold': hold}


def plain(name):
    """Label for a letter, digit, F-key or keypad digit; None if not one."""
    m = re.fullmatch(r'(?:KC_)?(?:N)?([A-Z0-9])', name)
    if m:
        return m.group(1)
    m = re.fullmatch(r'(?:KC_)?F(\d+)', name)
    if m:
        return f'F{m.group(1)}'
    m = re.fullmatch(r'(?:KC_P|KP_N)(\d)', name)
    if m:
        return f'KP {m.group(1)}'
    return None


# --- QMK ---------------------------------------------------------------------

def qmk_split(args):
    out, depth, cur = [], 0, ''
    for ch in args:
        if ch == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
            continue
        depth += ch == '('
        depth -= ch == ')'
        cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def qmk_basic(code):
    if code in QMK_KEYS:
        return SYMBOLS[QMK_KEYS[code]]
    if code in QMK_LABELS:
        return QMK_LABELS[code]
    if (p := plain(code)) is not None:
        return p
    m = re.fullmatch(r'LGUI\((\w+)\)', code)
    if m:
        return f'Cmd+{qmk_basic(m.group(1))}'
    return code


def qmk_key(code, aliases):
    while code in aliases:
        code = aliases[code]
    if code == 'KC_TRNS':
        return key('▽')
    if code in ('XXXXXXX', 'KC_NO'):
        return key()
    if code == 'L4_F20':
        return dict(THUMB_F20)
    m = re.fullmatch(r'MO\((\d+)\)', code)
    if m:
        return key(hold=f'L{m.group(1)}')
    m = re.fullmatch(r'LT\((\d+),\s*(\w+)\)', code)
    if m:
        return key(qmk_basic(m.group(2)), f'L{m.group(1)}')
    m = re.fullmatch(r'(\w+)_T\((\w+)\)', code)
    if m and m.group(1) in QMK_MODS:
        return key(qmk_basic(m.group(2)), QMK_MODS[m.group(1)])
    return key(qmk_basic(code))


def parse_qmk(path):
    src = path.read_text()
    code = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    code = re.sub(r'//[^\n]*', '', code)
    aliases = {}
    for name, value in re.findall(r'^\s*#define\s+(\w+)\s+(\S.*?)\s*$', code, flags=re.M):
        aliases[name] = value
    layers = {}
    for n, body in re.findall(r'\[(\d+)\]\s*=\s*LAYOUT\((.*?)\)\s*,?\s*(?=\[\d+\]|\};)', code, flags=re.S):
        raw = qmk_split(body)
        layers[int(n)] = {'raw': raw, 'keys': [qmk_key(c, aliases) for c in raw]}
    return layers, src


def qmk_timing(src, layers):
    term = int(re.search(r'#define\s+TAPPING_TERM\s+(\d+)', (QMK_KEYMAP.parent / 'config.h').read_text()).group(1))
    per_key, pending = {}, []
    body = re.search(r'get_tapping_term\(.*?\{(.*?)\n\}', src, flags=re.S).group(1)
    for line in body.splitlines():
        if m := re.match(r'\s*case\s+(\w+):', line):
            pending.append(m.group(1))
        elif m := re.match(r'\s*return\s+(.*);', line):
            value = eval(m.group(1).replace('TAPPING_TERM', str(term)))
            for name in pending:
                per_key[name] = value
            pending = []
    out = {}
    for pos, raw in enumerate(layers[0]['raw']):
        k = layers[0]['keys'][pos]
        if not k['hold']:
            continue
        if raw == 'L4_F20':
            out[pos] = f'{re.search(r"F20_TAP_WINDOW\s+(\d+)", src).group(1)} ms window'
        elif raw.startswith('MO('):
            out[pos] = 'instant'
        else:
            out[pos] = f'{per_key.get(raw, term)} ms'
    return out, f'{term} ms (QUICK_TAP_TERM defaults to TAPPING_TERM)'


# --- ZMK ---------------------------------------------------------------------

def zmk_key(b):
    b = ' '.join(b.split())
    if b == '&trans':
        return key('▽')
    if b == '&none':
        return key()
    if b == '&l4f20':
        return dict(THUMB_F20)
    if b in ZMK_BEHAVIORS:
        return key(ZMK_BEHAVIORS[b])
    if m := re.fullmatch(r'&mo (\d+)', b):
        if int(m.group(1)) in ZMK_SPEED_LAYERS:
            return key(ZMK_SPEED_LAYERS[int(m.group(1))])
        return key(hold=f'L{m.group(1)}')
    if m := re.fullmatch(r'&lt (\d+) (\S+)', b):
        return key(zmk_basic(m.group(2)), f'L{m.group(1)}')
    if m := re.fullmatch(r'&(hm|hma|hy) (\S+) (\S+)', b):
        return key(zmk_basic(m.group(3)), ZMK_MODS.get(m.group(2), m.group(2)))
    if m := re.fullmatch(r'&kp (\S+)', b):
        return key(zmk_basic(m.group(1)))
    if m := re.fullmatch(r'&bt BT_SEL (\d)', b):
        return key(f'BT {m.group(1)}')
    if m := re.fullmatch(r'&bt BT_DISC (\d)', b):
        return key(f'BT {m.group(1)} drop')
    return key(b)


def zmk_basic(name):
    if name in ZMK_KEYS:
        return SYMBOLS[ZMK_KEYS[name]]
    if name in ZMK_LABELS:
        return ZMK_LABELS[name]
    if (p := plain(name)) is not None:
        return p
    m = re.fullmatch(r'LG\((\w+)\)', name)
    if m:
        return f'Cmd+{zmk_basic(m.group(1))}'
    return name


def parse_zmk(path):
    src = path.read_text()
    code = re.sub(r'//[^\n]*', '', src)
    keymap = code[code.index('compatible = "zmk,keymap"'):]
    layers = {}
    for n, body in enumerate(re.findall(r'bindings\s*=\s*<(.*?)>;', keymap, flags=re.S)):
        raw = [b.strip() for b in re.findall(r'&[^&]+', body)]
        layers[n] = {'raw': raw, 'keys': [zmk_key(b) for b in raw]}
    return layers, code


def zmk_timing(code, layers):
    terms = {}
    for name, block in re.findall(r'(\w+):\s*\w+\s*\{([^{}]*?zmk,behavior-(?:hold-tap|tap-dance)[^{}]*?)\}', code, flags=re.S):
        t = re.search(r'tapping-term-ms\s*=\s*<(\d+)>', block)
        idle = re.search(r'require-prior-idle-ms\s*=\s*<(\d+)>', block)
        terms[name] = (int(t.group(1)) if t else None, int(idle.group(1)) if idle else None)
    m = re.search(r'&lt\s*\{(.*?)\};', code, flags=re.S)
    terms['lt'] = (int(re.search(r'tapping-term-ms\s*=\s*<(\d+)>', m.group(1)).group(1)), None)
    quick = sorted(set(re.findall(r'quick-tap-ms\s*=\s*<(\d+)>', code)))
    out = {}
    for pos, raw in enumerate(layers[0]['raw']):
        if not layers[0]['keys'][pos]['hold']:
            continue
        name = raw.split()[0][1:]
        if name == 'mo':
            out[pos] = 'instant'
        elif name == 'l4f20':
            out[pos] = f'{terms[name][0]} ms window'
        else:
            t, idle = terms[name]
            out[pos] = f'{t} ms' + (f', only after {idle} ms idle' if idle else '')
    return out, ' / '.join(f'{q} ms' for q in quick)


# --- Layer access ------------------------------------------------------------

def access_paths(layers):
    paths = {0: []}
    queue = [0]
    while queue:
        cur = queue.pop(0)
        for pos, name in THUMBS.items():
            hold = layers[cur]['keys'][pos]['hold']
            if hold.startswith('L'):
                n = int(hold[1:])
                if n not in paths:
                    paths[n] = paths[cur] + [name]
                    queue.append(n)
    return paths


# --- Page --------------------------------------------------------------------

def main():
    qmk, qmk_src = parse_qmk(QMK_KEYMAP)
    zmk, zmk_code = parse_zmk(ZMK_KEYMAP)
    for name, layers in (('QMK', qmk), ('ZMK', zmk)):
        for n, layer in layers.items():
            if len(layer['keys']) != 34:
                sys.exit(f'ERROR: {name} layer {n} has {len(layer["keys"])} keys, expected 34')
    q_timing, q_quick = qmk_timing(qmk_src, qmk)
    z_timing, z_quick = zmk_timing(zmk_code, zmk)
    data = {
        'layers': [
            {
                'n': n,
                'name': LAYER_NAMES.get(n, f'Layer {n}'),
                'sweep': qmk[n]['keys'],
                'gil': zmk[n]['keys'],
                'sweepRaw': qmk[n]['raw'],
                'gilRaw': zmk[n]['raw'],
            }
            for n in sorted(set(qmk) & set(zmk))
        ],
        'gilOnly': [f'L{n} ({ZMK_SPEED_LAYERS.get(n, "?")})' for n in sorted(set(zmk) - set(qmk))],
        'access': {
            'sweep': {str(k): v for k, v in access_paths(qmk).items()},
            'gil': {str(k): v for k, v in access_paths(zmk).items()},
        },
        'timing': [
            {
                'key': (qmk[0]['keys'][pos]['tap'] or '—') + ' / ' + qmk[0]['keys'][pos]['hold'],
                'sweep': q_timing.get(pos, ''),
                'gil': z_timing.get(pos, ''),
            }
            for pos in sorted(set(q_timing) | set(z_timing))
        ],
        'quick': {'sweep': q_quick, 'gil': z_quick},
    }
    template = (HERE / 'layout_template.html').read_text()
    OUT.write_text(template.replace('/*DATA*/null', json.dumps(data, ensure_ascii=False)))
    print(f'Wrote {OUT}')


if __name__ == '__main__':
    main()
