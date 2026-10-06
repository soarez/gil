#!/usr/bin/env python3
# /// script
# dependencies = ["pyyaml"]
# ///
"""Write both keymaps' layer tables and tap-hold timing from layout.yaml.

Rewrites the sections between "BEGIN GENERATED <name>" and "END GENERATED
<name>" markers in gil's config/gil.keymap (ZMK) and the Sweep's keymap.c
(QMK). Everything outside them stays hand-written.

    uv run layout/generate.py [path/to/qmk/keymap.c]

The QMK keymap defaults to the sibling qmk_firmware checkout.
"""
import pathlib
import re
import sys

import yaml

HERE = pathlib.Path(__file__).resolve().parent
LAYOUT = HERE / 'layout.yaml'
ZMK_KEYMAP = HERE.parent / 'config' / 'gil.keymap'
QMK_KEYMAP = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else (
    HERE.parent.parent / 'qmk_firmware' / 'keyboards' / 'splitkb' / 'aurora' / 'sweep' / 'keymaps' / 'sz' / 'keymap.c')
BOARDS = ('sweep', 'gil')
KEYS, COLS = 34, 10
SOURCE = 'gil/layout/layout.yaml by layout/generate.py; edit that, not this'

# token: (QMK keycode, ZMK binding)
BASIC = {
    '~': ('KC_TILD', 'TILDE'), '!': ('KC_EXLM', 'EXCL'), '@': ('KC_AT', 'AT'), '#': ('KC_HASH', 'HASH'),
    '$': ('KC_DLR', 'DLLR'), '%': ('KC_PERC', 'PRCNT'), '^': ('KC_CIRC', 'CARET'), '&': ('KC_AMPR', 'AMPS'),
    '*': ('KC_ASTR', 'ASTRK'), '(': ('KC_LPRN', 'LPAR'), ')': ('KC_RPRN', 'RPAR'), '{': ('KC_LCBR', 'LBRC'),
    '}': ('KC_RCBR', 'RBRC'), '[': ('KC_LBRC', 'LBKT'), ']': ('KC_RBRC', 'RBKT'), '"': ('KC_DQUO', 'DQT'),
    "'": ('KC_QUOT', 'SQT'), '_': ('KC_UNDS', 'UNDER'), '-': ('KC_MINS', 'MINUS'), '=': ('KC_EQL', 'EQUAL'),
    '+': ('KC_PLUS', 'PLUS'), '|': ('KC_PIPE', 'PIPE'), '\\': ('KC_BSLS', 'BSLH'), '`': ('KC_GRV', 'GRAVE'),
    ';': ('KC_SCLN', 'SEMICOLON'), ',': ('KC_COMM', 'COMMA'), '.': ('KC_DOT', 'DOT'), '/': ('KC_SLSH', 'SLASH'),
    'Esc': ('KC_ESC', 'ESC'), 'Tab': ('KC_TAB', 'TAB'), 'Space': ('KC_SPC', 'SPACE'), 'Bspc': ('KC_BSPC', 'BSPC'),
    'Enter': ('KC_ENT', 'ENTER'), 'Del': ('KC_DEL', 'DEL'), 'Left': ('KC_LEFT', 'LEFT'), 'Down': ('KC_DOWN', 'DOWN'),
    'Up': ('KC_UP', 'UP'), 'Right': ('KC_RGHT', 'RIGHT'),
    'KP+': ('KC_PPLS', 'KP_PLUS'), 'KP-': ('KC_PMNS', 'KP_MINUS'), 'KP*': ('KC_PAST', 'KP_ASTERISK'),
    'KP/': ('KC_PSLS', 'KP_SLASH'), 'KP.': ('KC_KP_DOT', 'KP_DOT'),
    'Play': ('KC_MPLY', 'C_PP'), 'FFwd': ('KC_MFFD', 'C_FF'), 'Rew': ('KC_MRWD', 'C_RW'), 'Mute': ('KC_MUTE', 'K_MUTE'),
    'Vol+': ('KC_VOLU', 'K_VOL_UP'), 'Vol-': ('KC_VOLD', 'K_VOL_DN'), 'Pause': ('KC_PAUSE', 'PAUSE_BREAK'),
    'ScrLk': ('KC_SCROLL_LOCK', 'SLCK'), 'Sleep': ('KC_SLEP', 'SYS_SLEEP'),
}
BEHAVIORS = {
    '___': ('KC_TRNS', '&trans'), 'xxx': ('XXXXXXX', '&none'), 'CapsWord': ('CW_TOGG', '&caps_word'),
    'Boot': ('QK_BOOT', '&bootloader'), 'Reset': ('QK_RBT', '&sys_reset'),
    'MsUp': ('KC_MS_U', '&mmv MOVE_UP'), 'MsDown': ('KC_MS_D', '&mmv MOVE_DOWN'),
    'MsLeft': ('KC_MS_L', '&mmv MOVE_LEFT'), 'MsRight': ('KC_MS_R', '&mmv MOVE_RIGHT'),
    'WhUp': ('KC_WH_U', '&msc SCRL_UP'), 'WhDown': ('KC_WH_D', '&msc SCRL_DOWN'),
    'Btn1': ('KC_BTN1', '&mkp LCLK'), 'Btn2': ('KC_BTN2', '&mkp RCLK'),
}
# modifier: QMK mod-tap per half, ZMK modifier per half, ZMK hold-tap behavior
MODS = {
    'ctrl': (('LCTL_T', 'RCTL_T'), ('LCTRL', 'RCTRL'), 'hm'),
    'cmd': (('LCMD_T', 'RCMD_T'), ('LGUI', 'RGUI'), 'hm'),
    'shift': (('LSFT_T', 'RSFT_T'), ('LSHFT', 'RSHFT'), 'hm'),
    'alt': (('LOPT_T', 'ROPT_T'), ('LALT', 'RALT'), 'hma'),
    'cag': (('LCAG_T', 'RCAG_T'), ('LC(LA(LGUI))', 'RC(RA(RGUI))'), 'hy'),
    'hyper': (('HYPR_T', 'HYPR_T'), ('LS(LC(LA(LGUI)))', 'LS(LC(LA(LGUI)))'), 'hy'),
}
# ZMK hold-tap behaviors, by the modifiers they hold
ZMK_HOLD_TAPS = {
    'hy': ('hyperkey_mods', ('cag', 'hyper')),
    'hm': ('homerow_mods', ('ctrl', 'cmd', 'shift')),
    'hma': ('homerow_mods_alt', ('alt',)),
}


def fail(msg):
    sys.exit(f'ERROR: {msg}')


def basic(token):
    """(QMK, ZMK &kp argument) for a plain key, or None."""
    if token in BASIC:
        return BASIC[token]
    if re.fullmatch(r'[A-Z]', token):
        return f'KC_{token}', token
    if re.fullmatch(r'[0-9]', token):
        return f'KC_{token}', f'N{token}'
    if m := re.fullmatch(r'F([1-9]|1[0-9]|2[0-4])', token):
        return f'KC_F{m.group(1)}', f'F{m.group(1)}'
    if m := re.fullmatch(r'KP([0-9])', token):
        return f'KC_P{m.group(1)}', f'KP_N{m.group(1)}'
    return None


class Layout:
    def __init__(self, path):
        spec = yaml.safe_load(path.read_text())
        self.timing = spec['timing']
        self.custom = spec.get('custom', {})
        self.layers = spec['layers']
        # Layer numbers per board: board-only layers go after the shared ones
        self.number = {}
        for board in BOARDS:
            on_board = [L for L in self.layers if board in L.get('boards', BOARDS)]
            self.number[board] = {L['id']: n for n, L in enumerate(on_board)}
        for L in self.layers:
            shared = 'boards' not in L
            for board in BOARDS:
                if shared and self.number[board][L['id']] != self.layers.index(L):
                    fail(f'layer {L["id"]} must come before the board-only layers')

    def grid(self, layer, board):
        keys = layer['keys']
        text = keys[board] if isinstance(keys, dict) else keys
        tokens = text.split()
        if len(tokens) != KEYS:
            fail(f'layer {layer["id"]} ({board}) has {len(tokens)} keys, expected {KEYS}')
        return tokens

    def layer_number(self, board, name, token):
        if name not in self.number[board]:
            fail(f'unknown layer "{name}" in "{token}" for {board}')
        return self.number[board][name]

    def key(self, token, board, pos):
        """(QMK keycode, ZMK binding, hold-tap class or None) for one key."""
        qmk = board == 'sweep'
        if token in self.custom:
            binding = self.custom[token].get(board)
            if binding is None:
                fail(f'"{token}" is not defined for {board}')
            binding = re.sub(r'\{(\w+)\}', lambda m: str(self.layer_number(board, m.group(1), token)), binding)
            return binding, None
        if token in BEHAVIORS:
            return BEHAVIORS[token][0 if qmk else 1], None
        if token.startswith('@') and len(token) > 1:
            n = self.layer_number(board, token[1:], token)
            return (f'MO({n})' if qmk else f'&mo {n}'), None
        if m := re.fullmatch(r'Cmd\+(.+)', token):
            b = basic(m.group(1)) or fail(f'unknown key "{m.group(1)}" in "{token}"')
            return (f'LGUI({b[0]})' if qmk else f'&kp LG({b[1]})'), None
        if ':' in token and token != ':':
            hold, tap = token.split(':', 1)
            b = basic(tap) or fail(f'unknown key "{tap}" in "{token}"')
            if hold in MODS:
                side = 0 if pos % COLS < 5 else 1
                mod_taps, zmk_mods, behavior = MODS[hold]
                if qmk:
                    return f'{mod_taps[side]}({b[0]})', hold
                return f'&{behavior} {zmk_mods[side]} {b[1]}', hold
            n = self.layer_number(board, hold, token)
            return (f'LT({n},{b[0]})' if qmk else f'&lt {n} {b[1]}'), 'layer'
        b = basic(token) or fail(f'unknown key "{token}"')
        return (b[0] if qmk else f'&kp {b[1]}'), None


def align(rows, sep, end, last_end):
    """Rows of 10 keys plus a thumb row of 4, columns aligned."""
    widths = [max(len(r[c]) for r in rows[:3]) for c in range(COLS)]
    thumb_widths = widths[3:7]
    for i, t in enumerate(rows[3]):
        thumb_widths[i] = max(thumb_widths[i], len(t))
    out = []
    for r in rows[:3]:
        out.append(sep.join(k.ljust(w) for k, w in zip(r, widths)) + end)
    indent = ' ' * (sum(widths[:3]) + len(sep) * 3)
    out.append(indent + sep.join(k.ljust(w) for k, w in zip(rows[3], thumb_widths)).rstrip() + last_end)
    return [line.rstrip() for line in out]


def rows_of(keys):
    return [keys[0:10], keys[10:20], keys[20:30], keys[30:34]]


def description(layer):
    return ' '.join(layer.get('description', '').split())


def qmk_sections(layout):
    layers, classes = [], {}
    for layer in layout.layers:
        if 'sweep' not in layer.get('boards', BOARDS):
            continue
        n = layout.number['sweep'][layer['id']]
        keys = []
        for pos, token in enumerate(layout.grid(layer, 'sweep')):
            code, cls = layout.key(token, 'sweep', pos)
            keys.append(code)
            if cls:
                classes.setdefault(layout.timing[cls], []).append(code)
        body = align(rows_of(keys), ' , ', ' ,', '')
        comment = f'// {description(layer)}\n' if description(layer) else ''
        layers.append(f'{comment}[{n}] = LAYOUT(\n' + '\n'.join('    ' + line for line in body) + '\n)')
    keymaps = ('const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {\n'
               + ',\n'.join(layers) + '\n};')

    default = layout.default_qmk_term
    cases = []
    for term in sorted(t for t in classes if t != default):
        cases += [f'        case {code}:' for code in classes[term]]
        cases.append(f'            return {term};')
    timing = ('uint16_t get_tapping_term(uint16_t keycode, keyrecord_t *record) {\n'
              '    switch (keycode) {\n' + '\n'.join(cases) + '\n'
              '        default:\n            return TAPPING_TERM;\n    }\n}')
    return {'layers': keymaps, 'timing': timing}


def zmk_sections(layout):
    t = layout.timing
    lines = [
        '&lt {',
        f'    tapping-term-ms = <{t["layer"]}>;',
        f'    quick-tap-ms = <{t["quick_tap"]}>;',
        '    flavor = "tap-preferred";',
        '};',
        '',
        '/ {',
        '    behaviors {',
    ]
    for name, (node, mods) in ZMK_HOLD_TAPS.items():
        terms = {t[m] for m in mods}
        if len(terms) != 1:
            fail(f'{", ".join(mods)} share the ZMK behavior &{name} but have different timings')
        lines += [
            f'        {name}: {node} {{',
            '            compatible = "zmk,behavior-hold-tap";',
            '            #binding-cells = <2>;',
            f'            tapping-term-ms = <{terms.pop()}>;',
            f'            quick-tap-ms = <{t["quick_tap"]}>;',
            '            flavor = "tap-preferred";',
            '            bindings = <&kp>, <&kp>;',
            '        };',
        ]
    lines += ['    };', '};']

    nodes = []
    for layer in layout.layers:
        if 'gil' not in layer.get('boards', BOARDS):
            continue
        n = layout.number['gil'][layer['id']]
        keys = [layout.key(token, 'gil', pos)[0] for pos, token in enumerate(layout.grid(layer, 'gil'))]
        node = 'default_layer' if n == 0 else f'layer_{n}'
        label = layer.get('zmk_label', f'L{n}')
        comment = f'        // {description(layer)}\n' if description(layer) else ''
        nodes.append(f'{comment}        {node} {{\n            label = "{label}";\n            bindings = <\n'
                     + '\n'.join(align(rows_of(keys), '  ', '', '')) + '\n            >;\n        };')
    keymap = '    keymap {\n        compatible = "zmk,keymap";\n' + '\n'.join(nodes) + '\n    };'
    return {'timing': '\n'.join(lines), 'layers': keymap}


def replace_sections(path, sections, comment):
    text = path.read_text()
    for name, body in sections.items():
        begin = f'{comment} BEGIN GENERATED {name} from {SOURCE}'
        pattern = re.compile(rf'^([ \t]*){re.escape(comment)} BEGIN GENERATED {name}\b.*?^[ \t]*{re.escape(comment)} END GENERATED {name}$',
                             re.S | re.M)
        if not pattern.search(text):
            fail(f'no "{comment} BEGIN/END GENERATED {name}" markers in {path}')
        indent = pattern.search(text).group(1)
        text = pattern.sub(lambda m: f'{indent}{begin}\n{body}\n{indent}{comment} END GENERATED {name}', text)
    path.write_text(text)


def check_qmk_config(layout):
    """The QMK default tapping term and quick tap live in config.h."""
    config = (QMK_KEYMAP.parent / 'config.h').read_text()
    term = int(re.search(r'#define\s+TAPPING_TERM\s+(\d+)', config).group(1))
    quick = re.search(r'#define\s+QUICK_TAP_TERM\s+(\d+)', config)
    if (int(quick.group(1)) if quick else term) != layout.timing['quick_tap']:
        fail(f'quick_tap is {layout.timing["quick_tap"]} but QMK config.h gives {quick.group(1) if quick else term}; '
             'set QUICK_TAP_TERM there')
    if 'IGNORE_MOD_TAP_INTERRUPT' not in re.sub(r'//[^\n]*', '', config):
        fail('QMK config.h no longer defines IGNORE_MOD_TAP_INTERRUPT, so it no longer matches ZMK tap-preferred')
    layout.default_qmk_term = term


def main():
    layout = Layout(LAYOUT)
    check_qmk_config(layout)
    replace_sections(QMK_KEYMAP, qmk_sections(layout), '//')
    replace_sections(ZMK_KEYMAP, zmk_sections(layout), '//')
    print(f'Wrote {ZMK_KEYMAP}\nWrote {QMK_KEYMAP}')


if __name__ == '__main__':
    main()
