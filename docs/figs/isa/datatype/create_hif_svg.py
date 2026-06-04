#!/usr/bin/env python3
"""Generate HiF8/HiF4 format SVG diagrams"""

# HiF8: Block floating-point format with shared exponent
svg_hif8 = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="200" viewBox="0 0 800 200">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 18px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
    .subtitle { font-size: 13px; fill: #666; font-style: italic; }
  </style>

  <text x="10" y="25" class="title">HiF8: Block-Floating-Point Format</text>
  <text x="10" y="45" class="subtitle">Variable exponent + variable mantissa, shared across group</text>

  <!-- Shared exponent column -->
  <g transform="translate(50, 60)">
    <rect x="0" y="0" width="60" height="100" fill="#9370DB" rx="3" stroke="#333" stroke-width="1"/>
    <text x="30" y="55" text-anchor="middle" fill="white">Shared</text>
    <text x="30" y="75" text-anchor="middle" fill="white">Exp</text>
    <text x="30" y="120" text-anchor="middle" class="label">8-bit</text>
  </g>

  <!-- Mantissa columns (8 values) -->
  <g transform="translate(130, 60)">
    <!-- Value boxes -->
    <rect x="0" y="0" width="50" height="100" fill="#228B22" rx="3" stroke="#333" stroke-width="1"/>
    <text x="25" y="45" text-anchor="middle" fill="white">M0</text>
    <text x="25" y="65" text-anchor="middle" fill="white">7b</text>

    <rect x="55" y="0" width="50" height="100" fill="#228B22" rx="3" stroke="#333" stroke-width="1"/>
    <text x="80" y="45" text-anchor="middle" fill="white">M1</text>
    <text x="80" y="65" text-anchor="middle" fill="white">7b</text>

    <rect x="110" y="0" width="50" height="100" fill="#228B22" rx="3" stroke="#333" stroke-width="1"/>
    <text x="135" y="45" text-anchor="middle" fill="white">M2</text>
    <text x="135" y="65" text-anchor="middle" fill="white">7b</text>

    <rect x="165" y="0" width="50" height="100" fill="#228B22" rx="3" stroke="#333" stroke-width="1"/>
    <text x="190" y="45" text-anchor="middle" fill="white">M3</text>
    <text x="190" y="65" text-anchor="middle" fill="white">7b</text>

    <rect x="220" y="0" width="50" height="100" fill="#228B22" rx="3" stroke="#333" stroke-width="1"/>
    <text x="245" y="45" text-anchor="middle" fill="white">M4</text>
    <text x="245" y="65" text-anchor="middle" fill="white">7b</text>

    <rect x="275" y="0" width="50" height="100" fill="#228B22" rx="3" stroke="#333" stroke-width="1"/>
    <text x="300" y="45" text-anchor="middle" fill="white">M5</text>
    <text x="300" y="65" text-anchor="middle" fill="white">7b</text>

    <rect x="330" y="0" width="50" height="100" fill="#228B22" rx="3" stroke="#333" stroke-width="1"/>
    <text x="355" y="45" text-anchor="middle" fill="white">M6</text>
    <text x="355" y="65" text-anchor="middle" fill="white">7b</text>

    <rect x="385" y="0" width="50" height="100" fill="#228B22" rx="3" stroke="#333" stroke-width="1"/>
    <text x="410" y="45" text-anchor="middle" fill="white">M7</text>
    <text x="410" y="65" text-anchor="middle" fill="white">7b</text>

    <text x="217" y="120" text-anchor="middle" class="label">8 × 7-bit mantissas = 56 bits</text>
  </g>

  <!-- Bracket showing shared group -->
  <g transform="translate(50, 165)">
    <path d="M 0,0 L 395,0" stroke="#333" stroke-width="1" fill="none"/>
    <path d="M 0,0 L 0,8" stroke="#333" stroke-width="1" fill="none"/>
    <path d="M 395,0 L 395,8" stroke="#333" stroke-width="1" fill="none"/>
    <text x="197" y="18" text-anchor="middle" class="label">Shared Exponent Group</text>
  </g>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/isa/datatype/hif8.svg', 'w', encoding='utf-8') as f:
    f.write(svg_hif8)
print("Created: hif8.svg")

# HiF4: Block floating-point format with 4-bit values
svg_hif4 = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="200" viewBox="0 0 800 200">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 18px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
    .subtitle { font-size: 13px; fill: #666; font-style: italic; }
  </style>

  <text x="10" y="25" class="title">HiF4: Block-Floating-Point Format</text>
  <text x="10" y="45" class="subtitle">4-bit mantissa with shared exponent across group</text>

  <!-- Shared exponent column -->
  <g transform="translate(50, 60)">
    <rect x="0" y="0" width="60" height="100" fill="#9370DB" rx="3" stroke="#333" stroke-width="1"/>
    <text x="30" y="55" text-anchor="middle" fill="white">Shared</text>
    <text x="30" y="75" text-anchor="middle" fill="white">Exp</text>
    <text x="30" y="120" text-anchor="middle" class="label">8-bit</text>
  </g>

  <!-- Mantissa columns (16 values) -->
  <g transform="translate(130, 60)">
    <!-- Value boxes (16 x 4-bit values in 4 rows of 4) -->
    <rect x="0" y="0" width="40" height="22" fill="#228B22" rx="2" stroke="#333" stroke-width="1"/>
    <text x="20" y="15" text-anchor="middle" fill="white" font-size="10">M0</text>

    <rect x="45" y="0" width="40" height="22" fill="#228B22" rx="2" stroke="#333" stroke-width="1"/>
    <text x="65" y="15" text-anchor="middle" fill="white" font-size="10">M1</text>

    <rect x="90" y="0" width="40" height="22" fill="#228B22" rx="2" stroke="#333" stroke-width="1"/>
    <text x="110" y="15" text-anchor="middle" fill="white" font-size="10">M2</text>

    <rect x="135" y="0" width="40" height="22" fill="#228B22" rx="2" stroke="#333" stroke-width="1"/>
    <text x="155" y="15" text-anchor="middle" fill="white" font-size="10">M3</text>

    <rect x="0" y="27" width="40" height="22" fill="#228B22" rx="2" stroke="#333" stroke-width="1"/>
    <text x="20" y="42" text-anchor="middle" fill="white" font-size="10">M4</text>

    <rect x="45" y="27" width="40" height="22" fill="#228B22" rx="2" stroke="#333" stroke-width="1"/>
    <text x="65" y="42" text-anchor="middle" fill="white" font-size="10">M5</text>

    <rect x="90" y="27" width="40" height="22" fill="#228B22" rx="2" stroke="#333" stroke-width="1"/>
    <text x="110" y="42" text-anchor="middle" fill="white" font-size="10">M6</text>

    <rect x="135" y="27" width="40" height="22" fill="#228B22" rx="2" stroke="#333" stroke-width="1"/>
    <text x="155" y="42" text-anchor="middle" fill="white" font-size="10">M7</text>

    <rect x="0" y="54" width="40" height="22" fill="#228B22" rx="2" stroke="#333" stroke-width="1"/>
    <text x="20" y="69" text-anchor="middle" fill="white" font-size="10">M8</text>

    <rect x="45" y="54" width="40" height="22" fill="#228B22" rx="2" stroke="#333" stroke-width="1"/>
    <text x="65" y="69" text-anchor="middle" fill="white" font-size="10">M9</text>

    <rect x="90" y="54" width="40" height="22" fill="#228B22" rx="2" stroke="#333" stroke-width="1"/>
    <text x="110" y="69" text-anchor="middle" fill="white" font-size="10">M10</text>

    <rect x="135" y="54" width="40" height="22" fill="#228B22" rx="2" stroke="#333" stroke-width="1"/>
    <text x="155" y="69" text-anchor="middle" fill="white" font-size="10">M11</text>

    <rect x="0" y="81" width="40" height="22" fill="#228B22" rx="2" stroke="#333" stroke-width="1"/>
    <text x="20" y="96" text-anchor="middle" fill="white" font-size="10">M12</text>

    <rect x="45" y="81" width="40" height="22" fill="#228B22" rx="2" stroke="#333" stroke-width="1"/>
    <text x="65" y="96" text-anchor="middle" fill="white" font-size="10">M13</text>

    <rect x="90" y="81" width="40" height="22" fill="#228B22" rx="2" stroke="#333" stroke-width="1"/>
    <text x="110" y="96" text-anchor="middle" fill="white" font-size="10">M14</text>

    <rect x="135" y="81" width="40" height="22" fill="#228B22" rx="2" stroke="#333" stroke-width="1"/>
    <text x="155" y="96" text-anchor="middle" fill="white" font-size="10">M15</text>

    <text x="87" y="120" text-anchor="middle" class="label">16 × 4-bit mantissas = 64 bits</text>
  </g>

  <!-- Bracket showing shared group -->
  <g transform="translate(50, 165)">
    <path d="M 0,0 L 125,0" stroke="#333" stroke-width="1" fill="none"/>
    <path d="M 0,0 L 0,8" stroke="#333" stroke-width="1" fill="none"/>
    <path d="M 125,0 L 125,8" stroke="#333" stroke-width="1" fill="none"/>
    <text x="62" y="18" text-anchor="middle" class="label">Shared Exponent Group</text>
  </g>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/isa/datatype/hif4.svg', 'w', encoding='utf-8') as f:
    f.write(svg_hif4)
print("Created: hif4.svg")

# HiF_scale: Scaling diagram showing shared exponent concept
svg_hif_scale = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="300" viewBox="0 0 800 300">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 18px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
    .subtitle { font-size: 13px; fill: #666; font-style: italic; }
    .formula { font-size: 14px; fill: #333; font-family: "Courier New", monospace; }
  </style>

  <text x="10" y="25" class="title">HiF8/HiF4: Shared Exponent Scaling</text>
  <text x="10" y="45" class="subtitle">A group of values share a single exponent field</text>

  <!-- HiF8 section -->
  <g transform="translate(10, 60)">
    <text x="0" y="0" class="label" font-weight="bold">HiF8: 8 values × 7-bit mantissa + 1 shared 8-bit exponent</text>

    <!-- Group box -->
    <rect x="0" y="10" width="720" height="100" fill="#F5F5F5" rx="5" stroke="#999" stroke-width="1" stroke-dasharray="5,3"/>

    <!-- Shared exponent -->
    <rect x="10" y="20" width="50" height="80" fill="#9370DB" rx="3" stroke="#333" stroke-width="1"/>
    <text x="35" y="55" text-anchor="middle" fill="white" font-size="12">Exp</text>
    <text x="35" y="115" text-anchor="middle" class="label">8-bit shared</text>

    <!-- 8 mantissa values -->
    <g transform="translate(80, 20)">
      <rect x="0" y="0" width="70" height="80" fill="#228B22" rx="3" stroke="#333" stroke-width="1"/>
      <text x="35" y="45" text-anchor="middle" fill="white">M0[6:0]</text>

      <rect x="80" y="0" width="70" height="80" fill="#228B22" rx="3" stroke="#333" stroke-width="1"/>
      <text x="115" y="45" text-anchor="middle" fill="white">M1[6:0]</text>

      <rect x="160" y="0" width="70" height="80" fill="#228B22" rx="3" stroke="#333" stroke-width="1"/>
      <text x="195" y="45" text-anchor="middle" fill="white">M2[6:0]</text>

      <rect x="240" y="0" width="70" height="80" fill="#228B22" rx="3" stroke="#333" stroke-width="1"/>
      <text x="275" y="45" text-anchor="middle" fill="white">M3[6:0]</text>

      <rect x="320" y="0" width="70" height="80" fill="#228B22" rx="3" stroke="#333" stroke-width="1"/>
      <text x="355" y="45" text-anchor="middle" fill="white">M4[6:0]</text>

      <rect x="400" y="0" width="70" height="80" fill="#228B22" rx="3" stroke="#333" stroke-width="1"/>
      <text x="435" y="45" text-anchor="middle" fill="white">M5[6:0]</text>

      <rect x="480" y="0" width="70" height="80" fill="#228B22" rx="3" stroke="#333" stroke-width="1"/>
      <text x="515" y="45" text-anchor="middle" fill="white">M6[6:0]</text>

      <rect x="560" y="0" width="70" height="80" fill="#228B22" rx="3" stroke="#333" stroke-width="1"/>
      <text x="595" y="45" text-anchor="middle" fill="white">M7[6:0]</text>
    </g>

    <text x="400" y="150" text-anchor="middle" class="formula">= 8 + 56 = 64 bits total</text>
  </g>

  <!-- HiF4 section -->
  <g transform="translate(10, 180)">
    <text x="0" y="0" class="label" font-weight="bold">HiF4: 16 values × 4-bit mantissa + 1 shared 8-bit exponent</text>

    <!-- Group box -->
    <rect x="0" y="10" width="720" height="100" fill="#F5F5F5" rx="5" stroke="#999" stroke-width="1" stroke-dasharray="5,3"/>

    <!-- Shared exponent -->
    <rect x="10" y="20" width="50" height="80" fill="#9370DB" rx="3" stroke="#333" stroke-width="1"/>
    <text x="35" y="55" text-anchor="middle" fill="white" font-size="12">Exp</text>
    <text x="35" y="115" text-anchor="middle" class="label">8-bit shared</text>

    <!-- 16 mantissa values (4x4 grid) -->
    <g transform="translate(80, 25)">
      <rect x="0" y="0" width="70" height="70" fill="#228B22" rx="3" stroke="#333" stroke-width="1"/>
      <text x="35" y="40" text-anchor="middle" fill="white" font-size="11">M[3:0]</text>
      <text x="35" y="55" text-anchor="middle" fill="white" font-size="10">× 16</text>
    </g>

    <text x="400" y="150" text-anchor="middle" class="formula">= 8 + 64 = 72 bits total</text>
  </g>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/isa/datatype/hif_scale.svg', 'w', encoding='utf-8') as f:
    f.write(svg_hif_scale)
print("Created: hif_scale.svg")

print("Done with HiF8/HiF4 format SVGs!")
