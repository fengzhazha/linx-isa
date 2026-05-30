#!/usr/bin/env python3
"""Generate remaining encoding space SVG diagrams"""

# space-48bit.svg - HL48 Encoding Space
svg_space_48bit = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="300" viewBox="0 0 900 300">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 18px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
    .bit-label { font-size: 11px; fill: #333; }
  </style>

  <text x="10" y="25" class="title">HL48 Encoding Space (48-bit)</text>
  <text x="10" y="45" class="label">16-bit prefix + 32-bit main instruction</text>

  <!-- Full instruction structure -->
  <g transform="translate(50, 60)">
    <text x="0" y="0" class="label" font-weight="bold">Instruction Layout:</text>

    <!-- Prefix box (16 bits) -->
    <rect x="0" y="10" width="200" height="80" fill="#45B7D1" rx="3" stroke="#333" stroke-width="2"/>
    <text x="100" y="40" text-anchor="middle" class="label" fill="white" font-weight="bold">Prefix</text>
    <text x="100" y="60" text-anchor="middle" class="bit-label" fill="white">[47:32]</text>
    <text x="100" y="100" text-anchor="middle" class="label">16-bit half-load</text>

    <!-- Main box (32 bits) -->
    <rect x="210" y="10" width="300" height="80" fill="#4ECDC4" rx="3" stroke="#333" stroke-width="2"/>
    <text x="360" y="40" text-anchor="middle" class="label" fill="white" font-weight="bold">Main</text>
    <text x="360" y="60" text-anchor="middle" class="bit-label" fill="white">[31:0]</text>
    <text x="360" y="100" text-anchor="middle" class="label">32-bit standard</text>
  </g>

  <!-- Prefix breakdown -->
  <g transform="translate(50, 170)">
    <text x="0" y="0" class="label" font-weight="bold">Prefix [47:32] Fields:</text>

    <rect x="0" y="10" width="80" height="50" fill="#FF6B6B" rx="2" stroke="#333" stroke-width="1"/>
    <text x="40" y="35" text-anchor="middle" class="label" fill="white">HL</text>
    <text x="40" y="75" text-anchor="middle" class="bit-label">[15:14]</text>

    <rect x="90" y="10" width="60" height="50" fill="#FFE4B5" rx="2" stroke="#333" stroke-width="1"/>
    <text x="120" y="35" text-anchor="middle" class="label">ext</text>
    <text x="120" y="75" text-anchor="middle" class="bit-label">[13:8]</text>

    <rect x="160" y="10" width="120" height="50" fill="#E8E8E8" rx="2" stroke="#333" stroke-width="1"/>
    <text x="220" y="35" text-anchor="middle" class="label">imm16</text>
    <text x="220" y="75" text-anchor="middle" class="bit-label">[7:0]</text>
  </g>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/isa/space/space-48bit.svg', 'w', encoding='utf-8') as f:
    f.write(svg_space_48bit)
print("Created: space-48bit.svg")

# space-64bit.svg - V64 Encoding Space
svg_space_64bit = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="300" viewBox="0 0 900 300">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 18px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
    .bit-label { font-size: 11px; fill: #333; }
  </style>

  <text x="10" y="25" class="title">V64 Encoding Space (64-bit)</text>
  <text x="10" y="45" class="label">32-bit prefix + 32-bit main instruction</text>

  <!-- Full instruction structure -->
  <g transform="translate(50, 60)">
    <text x="0" y="0" class="label" font-weight="bold">Instruction Layout:</text>

    <!-- Prefix box (32 bits) -->
    <rect x="0" y="10" width="250" height="80" fill="#45B7D1" rx="3" stroke="#333" stroke-width="2"/>
    <text x="125" y="40" text-anchor="middle" class="label" fill="white" font-weight="bold">Prefix</text>
    <text x="125" y="60" text-anchor="middle" class="bit-label" fill="white">[63:32]</text>
    <text x="125" y="100" text-anchor="middle" class="label">32-bit vector</text>

    <!-- Main box (32 bits) -->
    <rect x="260" y="10" width="250" height="80" fill="#4ECDC4" rx="3" stroke="#333" stroke-width="2"/>
    <text x="385" y="40" text-anchor="middle" class="label" fill="white" font-weight="bold">Main</text>
    <text x="385" y="60" text-anchor="middle" class="bit-label" fill="white">[31:0]</text>
    <text x="385" y="100" text-anchor="middle" class="label">32-bit standard</text>
  </g>

  <!-- Prefix breakdown -->
  <g transform="translate(50, 170)">
    <text x="0" y="0" class="label" font-weight="bold">Prefix [63:32] Fields:</text>

    <rect x="0" y="10" width="80" height="50" fill="#FF6B6B" rx="2" stroke="#333" stroke-width="1"/>
    <text x="40" y="35" text-anchor="middle" class="label" fill="white">V</text>
    <text x="40" y="75" text-anchor="middle" class="bit-label">[31:30]</text>

    <rect x="90" y="10" width="80" height="50" fill="#9370DB" rx="2" stroke="#333" stroke-width="1"/>
    <text x="130" y="35" text-anchor="middle" class="label" fill="white">vsz</text>
    <text x="130" y="75" text-anchor="middle" class="bit-label">[29:27]</text>

    <rect x="180" y="10" width="60" height="50" fill="#FFE4B5" rx="2" stroke="#333" stroke-width="1"/>
    <text x="210" y="35" text-anchor="middle" class="label">ext</text>
    <text x="210" y="75" text-anchor="middle" class="bit-label">[26:24]</text>

    <rect x="250" y="10" width="180" height="50" fill="#E8E8E8" rx="2" stroke="#333" stroke-width="1"/>
    <text x="340" y="35" text-anchor="middle" class="label">imm32</text>
    <text x="340" y="75" text-anchor="middle" class="bit-label">[23:0]</text>
  </g>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/isa/space/space-64bit.svg', 'w', encoding='utf-8') as f:
    f.write(svg_space_64bit)
print("Created: space-64bit.svg")

# encoding-layer1.svg - Width bit determination
svg_layer1 = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="500" height="200" viewBox="0 0 500 200">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 18px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
  </style>

  <text x="10" y="25" class="title">Encoding Layer 1: Width Determination</text>

  <g transform="translate(10, 50)">
    <!-- Width bit indicator -->
    <rect x="0" y="0" width="100" height="40" fill="#9370DB" rx="3" stroke="#333" stroke-width="1"/>
    <text x="50" y="25" text-anchor="middle" fill="white" font-weight="bold">W bit[0]</text>

    <!-- Arrow -->
    <path d="M 110,20 L 150,20" stroke="#333" stroke-width="2" fill="none"/>
    <polygon points="155,20 145,15 145,25" fill="#333"/>

    <!-- Decision diamond -->
    <polygon points="200,20 240,50 200,80 160,50" fill="#FFE4B5" stroke="#333" stroke-width="1"/>
    <text x="200" y="48" text-anchor="middle" class="label">W=0</text>
    <text x="200" y="62" text-anchor="middle" class="label">W=1</text>

    <!-- 16-bit path -->
    <path d="M 160,50 L 120,50" stroke="#333" stroke-width="1" fill="none"/>
    <path d="M 120,50 L 120,110" stroke="#333" stroke-width="1" fill="none"/>
    <path d="M 120,110 L 250,110" stroke="#333" stroke-width="1" fill="none"/>
    <rect x="260" y="90" width="100" height="40" fill="#FF6B6B" rx="3" stroke="#333" stroke-width="1"/>
    <text x="310" y="115" text-anchor="middle" fill="white" font-weight="bold">16-bit</text>
    <text x="310" y="150" text-anchor="middle" class="label">C16 Format</text>

    <!-- 32-bit path -->
    <path d="M 240,50 L 280,50" stroke="#333" stroke-width="1" fill="none"/>
    <path d="M 280,50 L 280,110" stroke="#333" stroke-width="1" fill="none"/>
    <path d="M 280,110 L 360,110" stroke="#333" stroke-width="1" fill="none"/>
    <rect x="370" y="90" width="100" height="40" fill="#4ECDC4" rx="3" stroke="#333" stroke-width="1"/>
    <text x="420" y="115" text-anchor="middle" fill="white" font-weight="bold">32-bit</text>
    <text x="420" y="150" text-anchor="middle" class="label">LX32 Format</text>
  </g>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/isa/space/encoding-layer1.svg', 'w', encoding='utf-8') as f:
    f.write(svg_layer1)
print("Created: encoding-layer1.svg")

# encoding-layer2.svg - Opcode field division
svg_layer2 = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="700" height="300" viewBox="0 0 700 300">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 18px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
    .section-label { font-size: 11px; fill: #333; }
  </style>

  <text x="10" y="25" class="title">Encoding Layer 2: Opcode Field Division</text>

  <!-- 16-bit path -->
  <g transform="translate(10, 50)">
    <text x="0" y="0" class="label" font-weight="bold">16-bit (C16):</text>

    <rect x="0" y="10" width="60" height="50" fill="#FF6B6B" rx="2" stroke="#333" stroke-width="1"/>
    <text x="30" y="40" text-anchor="middle" fill="white">opcode</text>
    <text x="30" y="75" text-anchor="middle" class="section-label">[15:13]</text>

    <rect x="70" y="10" width="250" height="50" fill="#E8E8E8" rx="2" stroke="#333" stroke-width="1"/>
    <text x="195" y="40" text-anchor="middle">operands/imm</text>
    <text x="195" y="75" text-anchor="middle" class="section-label">[12:0]</text>

    <text x="0" y="110" class="label">Opcode[15:13] = 000-110: Main instruction space (7 slots)</text>
    <text x="0" y="130" class="label">Opcode[15:13] = 111: Prefix instruction space</text>
  </g>

  <!-- 32-bit path -->
  <g transform="translate(10, 180)">
    <text x="0" y="0" class="label" font-weight="bold">32-bit (LX32):</text>

    <rect x="0" y="10" width="80" height="50" fill="#FF6B6B" rx="2" stroke="#333" stroke-width="1"/>
    <text x="40" y="40" text-anchor="middle" fill="white">opcode</text>
    <text x="40" y="75" text-anchor="middle" class="section-label">[31:26]</text>

    <rect x="90" y="10" width="250" height="50" fill="#E8E8E8" rx="2" stroke="#333" stroke-width="1"/>
    <text x="215" y="40" text-anchor="middle">operands/imm</text>
    <text x="215" y="75" text-anchor="middle" class="section-label">[25:0]</text>

    <text x="0" y="110" class="label">Opcode[31:26] = 000000-111101: Main instruction space (62 slots)</text>
    <text x="0" y="130" class="label">Opcode[31:26] = 111110: Prefix instruction space</text>
    <text x="0" y="150" class="label">Opcode[31:26] = 111111: Suffix instruction space</text>
  </g>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/isa/space/encoding-layer2.svg', 'w', encoding='utf-8') as f:
    f.write(svg_layer2)
print("Created: encoding-layer2.svg")

print("Done with encoding space SVGs!")
