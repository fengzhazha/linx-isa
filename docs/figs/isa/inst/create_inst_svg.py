#!/usr/bin/env python3
"""Generate matmul, matmadd, bridgetable, and fp_format0 SVGs"""

# matmul.svg - Matrix multiplication storage layout
svg_matmul = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 18px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
    .matrix-label { font-size: 11px; fill: white; }
  </style>

  <text x="10" y="25" class="title">Matrix Multiplication Storage Layout</text>
  <text x="10" y="45" class="label">How matrices A, B are stored in tile registers and CUBE result</text>

  <!-- Matrix A (D layout) -->
  <g transform="translate(20, 60)">
    <text x="0" y="0" class="label" font-weight="bold" fill="#1A8CFF">Matrix A (D Layout)</text>

    <rect x="0" y="10" width="120" height="100" fill="#B3D9FF" rx="3" stroke="#333" stroke-width="1"/>

    <!-- 4x4 matrix visualization -->
    <rect x="10" y="20" width="20" height="20" fill="#1A8CFF" rx="1"/>
    <rect x="35" y="20" width="20" height="20" fill="#1A8CFF" rx="1"/>
    <rect x="60" y="20" width="20" height="20" fill="#1A8CFF" rx="1"/>
    <rect x="85" y="20" width="20" height="20" fill="#1A8CFF" rx="1"/>

    <rect x="10" y="45" width="20" height="20" fill="#4DA6FF" rx="1"/>
    <rect x="35" y="45" width="20" height="20" fill="#4DA6FF" rx="1"/>
    <rect x="60" y="45" width="20" height="20" fill="#4DA6FF" rx="1"/>
    <rect x="85" y="45" width="20" height="20" fill="#4DA6FF" rx="1"/>

    <rect x="10" y="70" width="20" height="20" fill="#80C1FF" rx="1"/>
    <rect x="35" y="70" width="20" height="20" fill="#80C1FF" rx="1"/>
    <rect x="60" y="70" width="20" height="20" fill="#80C1FF" rx="1"/>
    <rect x="85" y="70" width="20" height="20" fill="#80C1FF" rx="1"/>

    <text x="60" y="125" text-anchor="middle" class="label">Row-major (D)</text>

    <!-- Arrow down to tile register -->
    <text x="60" y="150" text-anchor="middle" class="label">↓</text>
    <rect x="10" y="155" width="100" height="40" fill="#B3D9FF" rx="3" stroke="#333" stroke-width="1"/>
    <text x="60" y="180" text-anchor="middle" class="matrix-label">Tile D[0..15]</text>
  </g>

  <!-- Matrix B (Z layout) -->
  <g transform="translate(170, 60)">
    <text x="0" y="0" class="label" font-weight="bold" fill="#663399">Matrix B (Z Layout)</text>

    <rect x="0" y="10" width="100" height="120" fill="#E6D9F2" rx="3" stroke="#333" stroke-width="1"/>

    <!-- 4x4 matrix visualization (column-major) -->
    <rect x="10" y="20" width="20" height="20" fill="#663399" rx="1"/>
    <rect x="35" y="20" width="20" height="20" fill="#80C1FF" rx="1"/>
    <rect x="60" y="20" width="20" height="20" fill="#B3D9FF" rx="1"/>

    <rect x="10" y="45" width="20" height="20" fill="#663399" rx="1"/>
    <rect x="35" y="45" width="20" height="20" fill="#80C1FF" rx="1"/>
    <rect x="60" y="45" width="20" height="20" fill="#B3D9FF" rx="1"/>

    <rect x="10" y="70" width="20" height="20" fill="#663399" rx="1"/>
    <rect x="35" y="70" width="20" height="20" fill="#80C1FF" rx="1"/>
    <rect x="60" y="70" width="20" height="20" fill="#B3D9FF" rx="1"/>

    <text x="50" y="125" text-anchor="middle" class="label">Col-major (Z)</text>

    <!-- Arrow down to tile register -->
    <text x="50" y="150" text-anchor="middle" class="label">↓</text>
    <rect x="0" y="155" width="100" height="40" fill="#E6D9F2" rx="3" stroke="#333" stroke-width="1"/>
    <text x="50" y="180" text-anchor="middle" class="matrix-label">Tile Z[0..15]</text>
  </g>

  <!-- CUBE multiply -->
  <g transform="translate(320, 80)">
    <rect x="0" y="0" width="120" height="80" fill="#9370DB" rx="5" stroke="#333" stroke-width="2"/>
    <text x="60" y="35" text-anchor="middle" class="label" fill="white" font-weight="bold">CUBE</text>
    <text x="60" y="55" text-anchor="middle" class="label" fill="white">Multiply</text>
    <text x="60" y="70" text-anchor="middle" class="label" fill="white">D × Z</text>

    <!-- Arrows to CUBE -->
    <path d="M 130,50 L 140,50" stroke="#333" stroke-width="2"/>
    <path d="M 130,70 L 140,60" stroke="#333" stroke-width="2"/>
  </g>

  <!-- Result to ACC -->
  <g transform="translate(320, 180)">
    <text x="60" y="0" text-anchor="middle" class="label">↓</text>
    <text x="60" y="15" text-anchor="middle" class="label">Partial sums</text>

    <rect x="0" y="25" width="120" height="80" fill="#A5D6A7" rx="5" stroke="#2E7D32" stroke-width="2"/>
    <text x="60" y="60" text-anchor="middle" class="label" fill="#2E7D32" font-weight="bold">ACC</text>
    <text x="60" y="80" text-anchor="middle" class="label">4 × Tile size</text>
  </g>

  <!-- Bottom: Matrix C representation -->
  <g transform="translate(20, 290)">
    <text x="0" y="0" class="label" font-weight="bold">Matrix C (Result)</text>

    <rect x="0" y="10" width="120" height="100" fill="#C8E6C9" rx="3" stroke="#333" stroke-width="1"/>

    <!-- 4x4 result matrix placeholder -->
    <text x="60" y="60" text-anchor="middle" class="label">D Layout</text>
    <text x="60" y="80" text-anchor="middle" class="label">Accumulated</text>
    <text x="60" y="95" text-anchor="middle" class="label">Result</text>

    <rect x="10" y="115" width="100" height="40" fill="#A5D6A7" rx="3" stroke="#333" stroke-width="1"/>
    <text x="60" y="140" text-anchor="middle" class="matrix-label">ACC[0..63]</text>
  </g>

  <!-- Formula at bottom -->
  <text x="300" y="380" text-anchor="middle" class="label" font-family="Courier New, monospace">C[D,D] += A[D,Z] * B[Z,D]</text>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/isa/inst/matmul.svg', 'w', encoding='utf-8') as f:
    f.write(svg_matmul)
print("Created: matmul.svg")

# matmadd.svg - Matrix multiply-accumulate
svg_matmadd = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 18px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
    .matrix-label { font-size: 11px; fill: white; }
    .formula { font-family: "Courier New", monospace; font-size: 14px; fill: #333; }
  </style>

  <text x="10" y="25" class="title">Matrix Multiply-Accumulate (MATMADD)</text>
  <text x="10" y="45" class="label">C = A × B + C where A is D layout, B is Z layout, C is D layout</text>

  <!-- Matrix A -->
  <g transform="translate(20, 60)">
    <text x="0" y="0" class="label" font-weight="bold" fill="#1A8CFF">A (D Layout)</text>
    <rect x="0" y="10" width="100" height="80" fill="#B3D9FF" rx="3" stroke="#333" stroke-width="1"/>
    <text x="50" y="55" text-anchor="middle" class="label">4×4</text>
    <text x="50" y="110" text-anchor="middle" class="label">Row-major</text>
  </g>

  <!-- × symbol -->
  <g transform="translate(140, 90)">
    <text x="0" y="20" font-size="36" fill="#333">×</text>
  </g>

  <!-- Matrix B -->
  <g transform="translate(180, 60)">
    <text x="0" y="0" class="label" font-weight="bold" fill="#663399">B (Z Layout)</text>
    <rect x="0" y="10" width="80" height="100" fill="#E6D9F2" rx="3" stroke="#333" stroke-width="1"/>
    <text x="40" y="65" text-anchor="middle" class="label">4×4</text>
    <text x="40" y="130" text-anchor="middle" class="label">Col-major</text>
  </g>

  <!-- + symbol -->
  <g transform="translate(280, 100)">
    <text x="0" y="20" font-size="36" fill="#333">+</text>
  </g>

  <!-- Matrix C -->
  <g transform="translate(320, 60)">
    <text x="0" y="0" class="label" font-weight="bold" fill="#2E7D32">C (D Layout)</text>
    <rect x="0" y="10" width="100" height="80" fill="#C8E6C9" rx="3" stroke="#333" stroke-width="1"/>
    <text x="50" y="55" text-anchor="middle" class="label">4×4</text>
    <text x="50" y="110" text-anchor="middle" class="label">Accumulator</text>
  </g>

  <!-- = symbol -->
  <g transform="translate(440, 100)">
    <text x="0" y="20" font-size="36" fill="#333">=</text>
  </g>

  <!-- Result -->
  <g transform="translate(480, 60)">
    <text x="0" y="0" class="label" font-weight="bold" fill="#2E7D32">Result</text>
    <rect x="0" y="10" width="100" height="80" fill="#A5D6A7" rx="3" stroke="#2E7D32" stroke-width="2"/>
    <text x="50" y="55" text-anchor="middle" class="label">C'</text>
    <text x="50" y="110" text-anchor="middle" class="label">Updated</text>
  </g>

  <!-- Tile register view -->
  <g transform="translate(20, 220)">
    <rect x="0" y="0" width="560" height="150" fill="#F5F5F5" rx="5" stroke="#999" stroke-width="1"/>
    <text x="10" y="20" class="label" font-weight="bold">Tile Register Organization:</text>

    <!-- A tile -->
    <rect x="20" y="35" width="100" height="100" fill="#B3D9FF" rx="3" stroke="#333" stroke-width="1"/>
    <text x="70" y="70" text-anchor="middle" class="matrix-label">D[15:0]</text>
    <text x="70" y="90" text-anchor="middle" class="label">Matrix A</text>

    <!-- B tile -->
    <rect x="140" y="35" width="100" height="100" fill="#E6D9F2" rx="3" stroke="#333" stroke-width="1"/>
    <text x="190" y="70" text-anchor="middle" class="matrix-label">Z[15:0]</text>
    <text x="190" y="90" text-anchor="middle" class="label">Matrix B</text>

    <!-- C tile -->
    <rect x="260" y="35" width="100" height="100" fill="#C8E6C9" rx="3" stroke="#333" stroke-width="1"/>
    <text x="310" y="70" text-anchor="middle" class="matrix-label">N[15:0]</text>
    <text x="310" y="90" text-anchor="middle" class="label">Matrix C</text>

    <!-- CUBE unit -->
    <rect x="380" y="35" width="80" height="100" fill="#9370DB" rx="3" stroke="#333" stroke-width="1"/>
    <text x="420" y="70" text-anchor="middle" class="label" fill="white" font-weight="bold">CUBE</text>
    <text x="420" y="90" text-anchor="middle" class="label" fill="white">FMA</text>

    <!-- Arrow -->
    <path d="M 470,85 L 480,85" stroke="#333" stroke-width="2"/>
    <polygon points="485,85 475,80 475,90" fill="#333"/>

    <!-- Result -->
    <rect x="490" y="35" width="70" height="100" fill="#A5D6A7" rx="3" stroke="#2E7D32" stroke-width="2"/>
    <text x="525" y="70" text-anchor="middle" class="matrix-label">ACC</text>
    <text x="525" y="90" text-anchor="middle" class="label">Result</text>
  </g>

  <!-- Formula -->
  <text x="300" y="390" text-anchor="middle" class="formula">C[D,D] = A[D,Z] × B[Z,D] + C[D,D]</text>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/isa/inst/matmadd.svg', 'w', encoding='utf-8') as f:
    f.write(svg_matmadd)
print("Created: matmadd.svg")

# bridgetable.svg - Load-Bridge instruction classification
svg_bridge = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="500" height="400" viewBox="0 0 500 400">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 18px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
    .cell { font-size: 11px; fill: #333; }
  </style>

  <text x="10" y="25" class="title">Load-Bridge Instruction Classification</text>

  <!-- Table -->
  <g transform="translate(20, 50)">
    <!-- Header row -->
    <rect x="0" y="0" width="460" height="30" fill="#333" rx="3"/>
    <text x="115" y="20" text-anchor="middle" class="cell" fill="white" font-weight="bold">Variant</text>
    <text x="230" y="20" text-anchor="middle" class="cell" fill="white" font-weight="bold">Addressing</text>
    <text x="380" y="20" text-anchor="middle" class="cell" fill="white" font-weight="bold">Description</text>

    <!-- Row 1: Register-Register -->
    <rect x="0" y="35" width="460" height="40" fill="#E8F4E8" rx="2"/>
    <text x="115" y="58" text-anchor="middle" class="cell" font-weight="bold">Reg-Reg</text>
    <text x="230" y="58" text-anchor="middle" class="cell">[base + reg]</text>
    <text x="380" y="58" text-anchor="middle" class="cell">Base + register offset</text>

    <!-- Row 2: Register-Immediate -->
    <rect x="0" y="80" width="460" height="40" fill="#FFF0E8" rx="2"/>
    <text x="115" y="103" text-anchor="middle" class="cell" font-weight="bold">Reg-Imm</text>
    <text x="230" y="103" text-anchor="middle" class="cell">[base + imm16]</text>
    <text x="380" y="103" text-anchor="middle" class="cell">Base + 16-bit immediate</text>

    <!-- Row 3: Unscaled -->
    <rect x="0" y="125" width="460" height="40" fill="#E8E8F4" rx="2"/>
    <text x="115" y="148" text-anchor="middle" class="cell" font-weight="bold">Unscaled</text>
    <text x="230" y="148" text-anchor="middle" class="cell">[base + reg × scale]</text>
    <text x="380" y="148" text-anchor="middle" class="cell">Scaled index register</text>

    <!-- Row 4: PC-Relative -->
    <rect x="0" y="170" width="460" height="40" fill="#F4E8F4" rx="2"/>
    <text x="115" y="193" text-anchor="middle" class="cell" font-weight="bold">PC-Rel</text>
    <text x="230" y="193" text-anchor="middle" class="cell">[PC + imm26]</text>
    <text x="380" y="193" text-anchor="middle" class="cell">PC-relative load</text>

    <!-- Row 5: Tile -->
    <rect x="0" y="215" width="460" height="40" fill="#F4F4E8" rx="2"/>
    <text x="115" y="238" text-anchor="middle" class="cell" font-weight="bold">Tile</text>
    <text x="230" y="238" text-anchor="middle" class="cell">[tile + D1,D0]</text>
    <text x="380" y="238" text-anchor="middle" class="cell">Tile register indexed</text>
  </g>

  <!-- Additional info box -->
  <g transform="translate(20, 290)">
    <rect x="0" y="0" width="460" height="90" fill="#F5F5F5" rx="3" stroke="#999" stroke-width="1"/>
    <text x="10" y="20" class="label" font-weight="bold">Bridge Instructions:</text>
    <text x="10" y="40" class="label">• LDBR: Load with bridge addressing</text>
    <text x="10" y="60" class="label">• STBR: Store with bridge addressing</text>
    <text x="10" y="80" class="label">• Used for cross-tile memory operations</text>
  </g>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/isa/arch/bridgetable.svg', 'w', encoding='utf-8') as f:
    f.write(svg_bridge)
print("Created: bridgetable.svg")

# fp_format0.svg - Floating-point format overview
svg_fp_overview = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="700" height="300" viewBox="0 0 700 300">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 18px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
    .format-label { font-size: 11px; fill: #333; }
    .bits-label { font-size: 10px; fill: #666; }
  </style>

  <text x="10" y="25" class="title">Floating-Point Format Overview</text>
  <text x="10" y="45" class="label">All supported FP formats with relative bit widths</text>

  <!-- Format bars -->
  <g transform="translate(20, 60)">
'''

formats = [
    ("FP64", 64, "#4169E1", "#1E3A6E"),
    ("TF32", 32, "#9370DB", "#5C4D7D"),
    ("FP32", 32, "#4169E1", "#1E3A6E"),
    ("BF16", 16, "#FFB347", "#CC8030"),
    ("FP16", 16, "#FF6B6B", "#CC4545"),
    ("FP8", 8, "#A5D6A7", "#6B9B6E"),
    ("FP6", 6, "#E8E8E8", "#AAAAAA"),
    ("FP4", 4, "#D0D0D0", "#999999"),
]

bar_height = 22
gap = 4
max_width = 640

for i, (name, bits, color, dark_color) in enumerate(formats):
    y = i * (bar_height + gap)
    width = int((bits / 64) * max_width)

    # Main bar
    svg_fp_overview += f'''    <rect x="0" y="{y}" width="{width}" height="{bar_height}" fill="{color}" rx="2" stroke="#333" stroke-width="1"/>
    <text x="{width + 10}" y="{y + 16}" class="format-label">{name}</text>
    <text x="5" y="{y + 15}" class="format-label" fill="white">{bits}bit</text>
'''

svg_fp_overview += '''  </g>

  <!-- Legend at bottom -->
  <g transform="translate(20, 270)">
    <rect x="0" y="0" width="15" height="15" fill="#808080" rx="2"/>
    <text x="20" y="12" class="label">Sign (S)</text>

    <rect x="80" y="0" width="15" height="15" fill="#4169E1" rx="2"/>
    <text x="100" y="12" class="label">Exponent (E)</text>

    <rect x="180" y="0" width="15" height="15" fill="#228B22" rx="2"/>
    <text x="200" y="12" class="label">Mantissa (M)</text>

    <text x="350" y="12" class="label">Total bits = 1 + E + M</text>
  </g>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/isa/datatype/fp_format0.svg', 'w', encoding='utf-8') as f:
    f.write(svg_fp_overview)
print("Created: fp_format0.svg")

print("Done with remaining SVGs!")
