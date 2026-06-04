#!/usr/bin/env python3
"""Generate tile register layout SVG diagrams"""

def create_layout_svg(filepath, title, label, colors, width=700, height=500):
    """Create a 4x4 tile register layout diagram"""

    # Colors for 4x4 grid (light to dark)
    blue_shades = ["#B3D9FF", "#80C1FF", "#4DA6FF", "#1A8CFF"]
    purple_shades = ["#E6D9F2", "#CCB8E6", "#9966CC", "#663399"]
    green_shades = ["#C8E6C9", "#A5D6A7", "#66BB6A", "#2E7D32"]

    shade_colors = colors

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <style>
    text {{ font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }}
    .title {{ font-size: 18px; font-weight: bold; fill: #333; }}
    .label {{ font-size: 12px; fill: #555; }}
    .cell-label {{ font-size: 24px; font-weight: bold; fill: white; }}
  </style>

  <text x="10" y="25" class="title">{title}</text>

  <!-- 4x4 Grid of fractal blocks -->
  <g transform="translate(150, 60)">
'''

    cell_size = 100
    gap = 8

    for row in range(4):
        for col in range(4):
            color = shade_colors[(row + col) % 4]
            x = col * (cell_size + gap)
            y = row * (cell_size + gap)
            cell_label = label

            svg += f'''    <rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}"
          fill="{color}" rx="5" stroke="#333" stroke-width="2"/>
    <text x="{x + cell_size//2}" y="{y + cell_size//2 + 8}"
          text-anchor="middle" class="cell-label">{cell_label}</text>
'''

    # Column labels
    svg += '''
  </g>

  <!-- Legend -->
  <g transform="translate(500, 100)">
    <text x="0" y="0" class="label" font-weight="bold">Legend:</text>
'''

    for i, shade in enumerate(shade_colors):
        svg += f'''    <rect x="0" y="{20 + i*25}" width="20" height="20" fill="{shade}" rx="2"/>
    <text x="30" y="{35 + i*25}" class="label">Fractal {i}</text>
'''

    svg += '''  </g>

  <!-- Description -->
  <text x="10" y="480" class="label">Each block represents a fractal unit that can contain multiple elements</text>
</svg>'''

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(svg)
    print(f"Created: {filepath}")

# D Layout (大N小z) - Blue shades
create_layout_svg(
    '/Users/zhoubot/linx-isa/docs/figs/isa/arch/d-layout.svg',
    "D Layout (大N小z)",
    "D",
    ["#B3D9FF", "#80C1FF", "#4DA6FF", "#1A8CFF"]
)

# Z Layout (大Z小n) - Purple shades
create_layout_svg(
    '/Users/zhoubot/linx-isa/docs/figs/isa/arch/z-layout.svg',
    "Z Layout (大Z小n)",
    "Z",
    ["#E6D9F2", "#CCB8E6", "#9966CC", "#663399"]
)

# N Layout (小N大z) - Green shades
create_layout_svg(
    '/Users/zhoubot/linx-isa/docs/figs/isa/arch/n-layout.svg',
    "N Layout (小N大z)",
    "N",
    ["#C8E6C9", "#A5D6A7", "#66BB6A", "#2E7D32"]
)

# Combined layout - all three side by side
svg_combined = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="600" viewBox="0 0 900 600">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 20px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
    .subtitle { font-size: 14px; font-weight: bold; fill: #333; }
    .cell-label { font-size: 20px; font-weight: bold; fill: white; }
  </style>

  <text x="10" y="25" class="title">Tile Register Layouts</text>

  <!-- D Layout -->
  <g transform="translate(30, 50)">
    <text x="0" y="0" class="subtitle" fill="#1A8CFF">D Layout (大N小z)</text>

    <g transform="translate(0, 15)">
'''
blue_shades = ["#B3D9FF", "#80C1FF", "#4DA6FF", "#1A8CFF"]
for row in range(4):
    for col in range(4):
        color = blue_shades[(row + col) % 4]
        x = col * 70
        y = row * 70
        svg_combined += f'''      <rect x="{x}" y="{y}" width="65" height="65" fill="{color}" rx="3" stroke="#333" stroke-width="1"/>
      <text x="{x + 32}" y="{y + 40}" text-anchor="middle" class="cell-label" font-size="18">D</text>
'''

svg_combined += '''    </g>
  </g>

  <!-- Z Layout -->
  <g transform="translate(320, 50)">
    <text x="0" y="0" class="subtitle" fill="#663399">Z Layout (大Z小n)</text>

    <g transform="translate(0, 15)">
'''
purple_shades = ["#E6D9F2", "#CCB8E6", "#9966CC", "#663399"]
for row in range(4):
    for col in range(4):
        color = purple_shades[(row + col) % 4]
        x = col * 70
        y = row * 70
        svg_combined += f'''      <rect x="{x}" y="{y}" width="65" height="65" fill="{color}" rx="3" stroke="#333" stroke-width="1"/>
      <text x="{x + 32}" y="{y + 40}" text-anchor="middle" class="cell-label" font-size="18">Z</text>
'''

svg_combined += '''    </g>
  </g>

  <!-- N Layout -->
  <g transform="translate(610, 50)">
    <text x="0" y="0" class="subtitle" fill="#2E7D32">N Layout (小N大z)</text>

    <g transform="translate(0, 15)">
'''
green_shades = ["#C8E6C9", "#A5D6A7", "#66BB6A", "#2E7D32"]
for row in range(4):
    for col in range(4):
        color = green_shades[(row + col) % 4]
        x = col * 70
        y = row * 70
        svg_combined += f'''      <rect x="{x}" y="{y}" width="65" height="65" fill="{color}" rx="3" stroke="#333" stroke-width="1"/>
      <text x="{x + 32}" y="{y + 40}" text-anchor="middle" class="cell-label" font-size="18">N</text>
'''

svg_combined += '''    </g>
  </g>

  <!-- Description box -->
  <g transform="translate(30, 370)">
    <rect x="0" y="0" width="840" height="200" fill="#F5F5F5" rx="5" stroke="#999" stroke-width="1"/>

    <text x="10" y="25" class="label" font-weight="bold">Layout Semantics:</text>
    <text x="10" y="50" class="label">• D Layout (D = Row-major, 大N小z): Elements organized by row dimension</text>
    <text x="10" y="70" class="label">• Z Layout (Z = Column-major, 大Z小n): Elements organized by column dimension</text>
    <text x="10" y="90" class="label">• N Layout (N = Nested, 小N大z): Nested iteration over dimensions</text>

    <text x="10" y="120" class="label" font-weight="bold">Usage:</text>
    <text x="10" y="140" class="label">• D layout: Matrix A storage in GEMM operations</text>
    <text x="10" y="160" class="label">• Z layout: Matrix B storage in GEMM operations</text>
    <text x="10" y="180" class="label">• N layout: Matrix C (accumulator) storage</text>
  </g>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/isa/arch/layout.svg', 'w', encoding='utf-8') as f:
    f.write(svg_combined)
print("Created: layout.svg")

print("Done with tile register layout SVGs!")
