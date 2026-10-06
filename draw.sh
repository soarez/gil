#!/usr/bin/env bash
set -euo pipefail

CONFIG_DIR="$(realpath "$(dirname "$0")")"
DRAWER_DIR="${CONFIG_DIR}/keymap-drawer"

# Names for the keymap's layers, in order. The last three are the empty layers
# held by the mouse speed keys; they are not drawn.
layer_names=(Base Symbols Brackets Navigation Numbers Keypad Macros Media System
             "Mouse slow" "Mouse mid" "Mouse fast")
drawn_layers=("${layer_names[@]:0:9}")

echo "==> keymap-drawer: parse"
uvx --from keymap-drawer keymap -c "${DRAWER_DIR}/config.yaml" \
  parse -z "${CONFIG_DIR}/config/gil.keymap" -l "${layer_names[@]}" \
  > "${DRAWER_DIR}/gil.yaml"

# The right outer thumb (&l4f20) holds Numbers, but keymap-drawer only spots
# &mo/&lt as layer keys: mark it held on Numbers and on Macros (Numbers + the
# right inner thumb)
python3 - "${DRAWER_DIR}/gil.yaml" <<'PY'
import re, sys
path = sys.argv[1]
lines, layer, index = open(path).read().splitlines(), None, 0
for i, line in enumerate(lines):
    if m := re.fullmatch(r'  (\S.*):', line):
        layer, index = m.group(1), 0
    elif line.startswith('  - '):
        if layer in ('Numbers', 'Macros') and index == 33:
            lines[i] = "  - {type: held}"
        index += 1
open(path, 'w').write('\n'.join(lines) + '\n')
PY

echo "==> keymap-drawer: draw"
# The Urchin has the same 34-key split layout as the Cradio/Sweep
uvx --from keymap-drawer keymap -c "${DRAWER_DIR}/config.yaml" \
  draw "${DRAWER_DIR}/gil.yaml" \
  --ortho-layout '{split: true, rows: 3, columns: 5, thumbs: 2}' \
  -s "${drawn_layers[@]}" \
  > "${DRAWER_DIR}/gil.svg"
