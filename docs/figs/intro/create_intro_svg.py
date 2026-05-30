#!/usr/bin/env python3
"""Generate predicate and intro SVG diagrams"""

# pred.svg - Predicate register (64-bit mask)
svg_pred = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="200" viewBox="0 0 800 200">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 18px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
    .bit { font-size: 10px; fill: #333; }
  </style>

  <text x="10" y="25" class="title">Predicate Register P[63:0]</text>
  <text x="10" y="45" class="label">64-bit mask register for conditional execution</text>

  <!-- Main register box -->
  <g transform="translate(10, 60)">
    <!-- Register container -->
    <rect x="0" y="0" width="760" height="80" fill="#F5F5F5" rx="3" stroke="#333" stroke-width="2"/>

    <!-- 64 bit cells -->
    <g transform="translate(5, 5)">
'''

# Create 64 individual bit cells
for i in range(64):
    col = i % 16
    row = i // 16
    x = col * 46
    y = row * 35

    # Alternate colors based on bit position
    if i % 2 == 0:
        fill = "#E8E8E8"
    else:
        fill = "#D0D0D0"

    svg_pred += f'''      <rect x="{x}" y="{y}" width="44" height="30" fill="{fill}" rx="2" stroke="#999" stroke-width="1"/>
      <text x="{x + 22}" y="{y + 12}" text-anchor="middle" class="bit">{i}</text>
      <text x="{x + 22}" y="{y + 24}" text-anchor="middle" class="bit" fill="#666">P{i}</text>
'''

svg_pred += '''    </g>

    <!-- Labels -->
    <text x="380" y="100" text-anchor="middle" class="label">P[63]</text>
    <text x="10" y="100" text-anchor="start" class="label">P[0]</text>
  </g>

  <!-- Note -->
  <text x="10" y="180" class="label">Note: P[0] is always 1 (always execute)</text>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/isa/arch/pred.svg', 'w', encoding='utf-8') as f:
    f.write(svg_pred)
print("Created: pred.svg")

# Relative-index.svg - SGPR relative indexing
svg_relative = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="200" viewBox="0 0 900 200">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 18px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
  </style>

  <text x="10" y="25" class="title">SGPR Relative Indexing</text>
  <text x="10" y="45" class="label">Register file with relative addressing support</text>

  <!-- Register file grid -->
  <g transform="translate(10, 60)">
    <rect x="0" y="0" width="500" height="120" fill="#F5F5F5" rx="5" stroke="#333" stroke-width="2"/>
    <text x="250" y="20" text-anchor="middle" class="label" font-weight="bold">Scalar General Purpose Registers (SGPR)</text>

    <!-- 16 SGPR slots -->
'''

for i in range(16):
    col = i % 8
    row = i // 8
    x = col * 60 + 10
    y = row * 50 + 30

    fill = "#B8D4E8" if i % 2 == 0 else "#A0C4D8"

    svg_relative += f'''    <rect x="{x}" y="{y}" width="50" height="40" fill="{fill}" rx="3" stroke="#333" stroke-width="1"/>
    <text x="{x + 25}" y="{y + 15}" text-anchor="middle" class="label" font-weight="bold">S{i}</text>
    <text x="{x + 25}" y="{y + 32}" text-anchor="middle" class="label">[{i}]</text>
'''

svg_relative += '''  </g>

  <!-- Arrow and explanation -->
  <g transform="translate(530, 80)">
    <text x="0" y="0" class="label" font-weight="bold">Relative Indexing:</text>
    <text x="0" y="20" class="label">• Base register + offset</text>
    <text x="0" y="40" class="label">• Dynamic register selection</text>
    <text x="0" y="60" class="label">• Used for vector register access</text>

    <!-- Example -->
    <rect x="0" y="80" width="150" height="50" fill="#FFE4B5" rx="3" stroke="#333" stroke-width="1"/>
    <text x="75" y="105" text-anchor="middle" font-family="Courier New, monospace" font-size="12">S[r10 + 8]</text>
    <text x="75" y="145" text-anchor="middle" class="label">Example: base + offset</text>
  </g>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/intro/Relative-index.svg', 'w', encoding='utf-8') as f:
    f.write(svg_relative)
print("Created: Relative-index.svg")

# vectorblock.svg - Vector data block overview
svg_vector = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="300" viewBox="0 0 800 300">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 18px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
    .box-title { font-size: 14px; font-weight: bold; fill: white; }
  </style>

  <text x="10" y="25" class="title">Vector Data Block Overview</text>
  <text x="10" y="45" class="label">Two-level execution model: scalarLane + vectorLanes</text>

  <!-- Main block -->
  <rect x="10" y="60" width="780" height="220" fill="#F5F5F5" rx="5" stroke="#333" stroke-width="2"/>

  <!-- Scalar lane (top) -->
  <g transform="translate(20, 70)">
    <rect x="0" y="0" width="180" height="80" fill="#9370DB" rx="3" stroke="#333" stroke-width="1"/>
    <text x="90" y="35" text-anchor="middle" class="box-title">Scalar Lane</text>
    <text x="90" y="55" text-anchor="middle" class="label" fill="white">scalarLane[31:0]</text>
    <text x="90" y="70" text-anchor="middle" class="label" fill="white">Single value</text>
  </g>

  <!-- Vector lanes (middle) -->
  <g transform="translate(220, 70)">
    <rect x="0" y="0" width="560" height="80" fill="#4ECDC4" rx="3" stroke="#333" stroke-width="1"/>
    <text x="280" y="25" text-anchor="middle" class="box-title">Vector Lanes</text>
    <text x="280" y="50" text-anchor="middle" class="label" fill="white">vectorLanes[0..15] × 32-bit values</text>

    <!-- Individual lane indicators -->
    <rect x="20" y="60" width="520" height="15" fill="#3DBDB4" rx="2"/>
    <text x="280" y="72" text-anchor="middle" class="label" fill="white">16 lanes × 32-bit</text>
  </g>

  <!-- VGPR / SGPR registers -->
  <g transform="translate(20, 160)">
    <rect x="0" y="0" width="200" height="50" fill="#4169E1" rx="3" stroke="#333" stroke-width="1"/>
    <text x="100" y="30" text-anchor="middle" class="box-title">VGPR</text>

    <rect x="220" y="0" width="200" height="50" fill="#808080" rx="3" stroke="#333" stroke-width="1"/>
    <text x="320" y="30" text-anchor="middle" class="box-title">SGPR</text>

    <rect x="440" y="0" width="150" height="50" fill="#FF6B6B" rx="3" stroke="#333" stroke-width="1"/>
    <text x="515" y="30" text-anchor="middle" class="box-title">PRED</text>
  </g>

  <!-- Loop control -->
  <g transform="translate(610, 160)">
    <rect x="0" y="0" width="170" height="50" fill="#FFB347" rx="3" stroke="#333" stroke-width="1"/>
    <text x="85" y="25" text-anchor="middle" class="label" fill="#333" font-weight="bold">Loop Control</text>
    <text x="85" y="42" text-anchor="middle" class="label" fill="#333">LB/LC</text>
  </g>

  <!-- Tile registers at bottom -->
  <g transform="translate(20, 220)">
    <text x="0" y="15" class="label" font-weight="bold">Tile Registers (D/Z/N Layouts):</text>

    <rect x="0" y="25" width="120" height="30" fill="#B3D9FF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="60" y="45" text-anchor="middle" class="label">D[3:0]</text>

    <rect x="130" y="25" width="120" height="30" fill="#E6D9F2" rx="2" stroke="#333" stroke-width="1"/>
    <text x="190" y="45" text-anchor="middle" class="label">Z[3:0]</text>

    <rect x="260" y="25" width="120" height="30" fill="#C8E6C9" rx="2" stroke="#333" stroke-width="1"/>
    <text x="320" y="45" text-anchor="middle" class="label">N[3:0]</text>

    <rect x="390" y="25" width="120" height="30" fill="#A5D6A7" rx="2" stroke="#333" stroke-width="1"/>
    <text x="450" y="45" text-anchor="middle" class="label">ACC[3:0]</text>
  </g>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/intro/vectorblock.svg', 'w', encoding='utf-8') as f:
    f.write(svg_vector)
print("Created: vectorblock.svg")

# memoryblock.svg - Memory access block
svg_memory = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="300" viewBox="0 0 800 300">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 18px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
    .box-title { font-size: 14px; font-weight: bold; fill: white; }
  </style>

  <text x="10" y="25" class="title">Memory Access Block Overview</text>
  <text x="10" y="45" class="label">Two variants: MPAR (parallel) and MSEQ (serial)</text>

  <!-- MPAR Block -->
  <g transform="translate(10, 60)">
    <text x="0" y="0" class="label" font-weight="bold">MPAR (Parallel):</text>
    <rect x="0" y="10" width="380" height="180" fill="#E8F4E8" rx="5" stroke="#2E7D32" stroke-width="2"/>

    <!-- Tile register -->
    <rect x="10" y="25" width="120" height="60" fill="#4169E1" rx="3" stroke="#333" stroke-width="1"/>
    <text x="70" y="55" text-anchor="middle" class="box-title">Tile Reg</text>
    <text x="70" y="72" text-anchor="middle" class="label" fill="white">D/Z/N</text>

    <!-- Arrow -->
    <path d="M 140,55 L 170,55" stroke="#333" stroke-width="2" fill="none"/>
    <polygon points="175,55 165,50 165,60" fill="#333"/>

    <!-- Memory unit -->
    <rect x="180" y="25" width="100" height="60" fill="#FFB347" rx="3" stroke="#333" stroke-width="1"/>
    <text x="230" y="55" text-anchor="middle" class="box-title" fill="#333">Memory</text>
    <text x="230" y="72" text-anchor="middle" class="label">Parallel</text>

    <!-- Group/Lane model -->
    <text x="10" y="110" class="label">Group/Lane Model:</text>
    <rect x="10" y="120" width="360" height="60" fill="#F5F5F5" rx="3"/>
    <text x="190" y="145" text-anchor="middle" class="label">Group[0..7] × Lane[0..15]</text>
    <text x="190" y="165" text-anchor="middle" class="label">8 groups × 16 lanes = 128 parallel accesses</text>
  </g>

  <!-- MSEQ Block -->
  <g transform="translate(410, 60)">
    <text x="0" y="0" class="label" font-weight="bold">MSEQ (Serial):</text>
    <rect x="0" y="10" width="380" height="180" fill="#FFF0E8" rx="5" stroke="#FF6B6B" stroke-width="2"/>

    <!-- Tile register -->
    <rect x="10" y="25" width="120" height="60" fill="#4169E1" rx="3" stroke="#333" stroke-width="1"/>
    <text x="70" y="55" text-anchor="middle" class="box-title">Tile Reg</text>
    <text x="70" y="72" text-anchor="middle" class="label" fill="white">D/Z/N</text>

    <!-- Arrow -->
    <path d="M 140,55 L 170,55" stroke="#333" stroke-width="2" fill="none"/>
    <polygon points="175,55 165,50 165,60" fill="#333"/>

    <!-- Memory unit -->
    <rect x="180" y="25" width="100" height="60" fill="#FF6B6B" rx="3" stroke="#333" stroke-width="1"/>
    <text x="230" y="55" text-anchor="middle" class="box-title">Memory</text>
    <text x="230" y="72" text-anchor="middle" class="label">Serial</text>

    <!-- Sequential model -->
    <text x="10" y="110" class="label">Sequential Access:</text>
    <rect x="10" y="120" width="360" height="60" fill="#F5F5F5" rx="3"/>
    <text x="190" y="145" text-anchor="middle" class="label">Lane[0..127]</text>
    <text x="190" y="165" text-anchor="middle" class="label">128 sequential scalar accesses</text>
  </g>

  <!-- Bottom comparison -->
  <text x="400" y="280" text-anchor="middle" class="label">MPAR: Wide parallel for throughput | MSEQ: Precise control for addresses</text>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/intro/memoryblock.svg', 'w', encoding='utf-8') as f:
    f.write(svg_memory)
print("Created: memoryblock.svg")

print("Done with predicate and intro SVGs!")
