#!/usr/bin/env python3
"""Generate remaining arch and inst SVG diagrams"""

# reducedim.svg - Reduced-dimension mapping
svg_reducedim = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="300" viewBox="0 0 600 300">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 18px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
    .dim-label { font-size: 14px; font-weight: bold; fill: #333; }
  </style>

  <text x="10" y="25" class="title">Reduced-Dimension Mapping</text>
  <text x="10" y="45" class="label">Memory access blocks with reduced dimensionality</text>

  <!-- 4D tile (source) -->
  <g transform="translate(20, 60)">
    <text x="0" y="0" class="dim-label">4D Tensor Tile</text>
    <rect x="0" y="10" width="150" height="120" fill="#E8E8E8" rx="3" stroke="#333" stroke-width="2"/>
    <text x="75" y="70" text-anchor="middle" class="label">[D3, D2, D1, D0]</text>
    <text x="75" y="90" text-anchor="middle" class="label">Full 4D address</text>
  </g>

  <!-- Arrow -->
  <path d="M 185,90 L 235,90" stroke="#333" stroke-width="2" fill="none"/>
  <polygon points="240,90 230,85 230,95" fill="#333"/>

  <!-- Reduced to 2D -->
  <g transform="translate(250, 60)">
    <text x="0" y="0" class="dim-label">2D Tile Register</text>
    <rect x="0" y="10" width="150" height="120" fill="#B3D9FF" rx="3" stroke="#333" stroke-width="2"/>
    <text x="75" y="60" text-anchor="middle" class="label">[D1, D0]</text>
    <text x="75" y="80" text-anchor="middle" class="label">2D layout</text>
    <text x="75" y="100" text-anchor="middle" class="label">Reduced</text>
    <text x="75" y="115" text-anchor="middle" class="label">dimension</text>
  </g>

  <!-- Arrow -->
  <path d="M 415,90 L 465,90" stroke="#333" stroke-width="2" fill="none"/>
  <polygon points="470,90 460,85 460,95" fill="#333"/>

  <!-- Linear memory -->
  <g transform="translate(480, 60)">
    <text x="0" y="0" class="dim-label">Linear Memory</text>
    <rect x="0" y="10" width="100" height="120" fill="#C8E6C9" rx="3" stroke="#333" stroke-width="2"/>
    <text x="50" y="70" text-anchor="middle" class="label">[offset]</text>
    <text x="50" y="90" text-anchor="middle" class="label">1D address</text>
  </g>

  <!-- Dimension labels at bottom -->
  <g transform="translate(20, 210)">
    <rect x="0" y="0" width="560" height="70" fill="#F5F5F5" rx="3" stroke="#999" stroke-width="1"/>
    <text x="280" y="20" text-anchor="middle" class="label" font-weight="bold">Dimension Mapping Rules:</text>
    <text x="20" y="40" class="label">• D3, D2: Iterated externally (loop overhead)</text>
    <text x="20" y="55" class="label">• D1, D0: Iterated internally (vector lanes)</text>
  </g>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/isa/arch/reducedim.svg', 'w', encoding='utf-8') as f:
    f.write(svg_reducedim)
print("Created: reducedim.svg")

# multidim.svg - Multi-dimensional tile mapping
svg_multidim = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="300" viewBox="0 0 600 300">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 18px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
  </style>

  <text x="10" y="25" class="title">Multi-Dimensional Tile Mapping</text>
  <text x="10" y="45" class="label">Complex tensor to tile register address translation</text>

  <!-- Tensor representation -->
  <g transform="translate(20, 60)">
    <text x="0" y="0" class="label" font-weight="bold">Tensor Element</text>

    <rect x="0" y="10" width="80" height="40" fill="#E8E8E8" rx="2" stroke="#333" stroke-width="1"/>
    <text x="40" y="35" text-anchor="middle" class="label">[b,h,w,c]</text>

    <!-- Grid showing multiple tiles -->
    <rect x="0" y="60" width="200" height="140" fill="#F5F5F5" rx="3" stroke="#999" stroke-width="1"/>

    <text x="100" y="80" text-anchor="middle" class="label">Tile Grid</text>

    <!-- Tile blocks -->
    <rect x="20" y="95" width="40" height="30" fill="#B3D9FF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="40" y="115" text-anchor="middle" class="label" font-size="9">T0</text>

    <rect x="70" y="95" width="40" height="30" fill="#B3D9FF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="90" y="115" text-anchor="middle" class="label" font-size="9">T1</text>

    <rect x="120" y="95" width="40" height="30" fill="#B3D9FF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="140" y="115" text-anchor="middle" class="label" font-size="9">T2</text>

    <rect x="20" y="135" width="40" height="30" fill="#B3D9FF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="40" y="155" text-anchor="middle" class="label" font-size="9">T3</text>

    <rect x="70" y="135" width="40" height="30" fill="#B3D9FF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="90" y="155" text-anchor="middle" class="label" font-size="9">T4</text>
  </g>

  <!-- Arrow -->
  <path d="M 250,130 L 290,130" stroke="#333" stroke-width="2" fill="none"/>
  <polygon points="295,130 285,125 285,135" fill="#333"/>

  <!-- Tile register mapping -->
  <g transform="translate(310, 60)">
    <text x="0" y="0" class="label" font-weight="bold">Tile Register Address</text>

    <!-- Address formula -->
    <rect x="0" y="10" width="260" height="100" fill="#FFE4B5" rx="3" stroke="#333" stroke-width="1"/>
    <text x="130" y="40" text-anchor="middle" font-family="Courier New, monospace" font-size="13">
      addr = ((b*tH + h)*tW + w)*tC + c
    </text>
    <text x="130" y="70" text-anchor="middle" class="label" font-size="11">where tile size = tH × tW × tC</text>
    <text x="130" y="95" text-anchor="middle" class="label">4D → 1D linearization</text>

    <!-- Register file representation -->
    <rect x="0" y="120" width="260" height="80" fill="#F5F5F5" rx="3" stroke="#999" stroke-width="1"/>
    <text x="130" y="145" text-anchor="middle" class="label">Register File</text>
    <rect x="20" y="155" width="220" height="35" fill="#E8E8E8" rx="2"/>
    <text x="130" y="178" text-anchor="middle" class="label">R[0..N-1]</text>
  </g>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/isa/arch/multidim.svg', 'w', encoding='utf-8') as f:
    f.write(svg_multidim)
print("Created: multidim.svg")

# multidim1.svg - Detailed multi-dimensional tile mapping
svg_multidim1 = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="300" viewBox="0 0 600 300">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 18px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
  </style>

  <text x="10" y="25" class="title">Multi-Dimensional Tile Mapping (Detailed)</text>
  <text x="10" y="45" class="label">Tile register layout with dimensional indices</text>

  <!-- Tile grid visualization -->
  <g transform="translate(20, 60)">
    <text x="0" y="0" class="label" font-weight="bold">Tile Register Grid</text>

    <rect x="0" y="10" width="280" height="200" fill="#F5F5F5" rx="3" stroke="#999" stroke-width="1"/>

    <!-- 4x4 tile grid -->
    <text x="140" y="30" text-anchor="middle" class="label">D1 dimension (rows)</text>
    <text x="-10" y="120" text-anchor="middle" class="label" transform="rotate(-90, -10, 120)">D0 dimension (cols)</text>

    <!-- Row 0 -->
    <rect x="20" y="40" width="50" height="40" fill="#B3D9FF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="45" y="65" text-anchor="middle" class="label" font-size="10">[0,0]</text>

    <rect x="80" y="40" width="50" height="40" fill="#B3D9FF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="105" y="65" text-anchor="middle" class="label" font-size="10">[0,1]</text>

    <rect x="140" y="40" width="50" height="40" fill="#B3D9FF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="165" y="65" text-anchor="middle" class="label" font-size="10">[0,2]</text>

    <rect x="200" y="40" width="50" height="40" fill="#B3D9FF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="225" y="65" text-anchor="middle" class="label" font-size="10">[0,3]</text>

    <!-- Row 1 -->
    <rect x="20" y="90" width="50" height="40" fill="#80C1FF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="45" y="115" text-anchor="middle" class="label" font-size="10">[1,0]</text>

    <rect x="80" y="90" width="50" height="40" fill="#80C1FF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="105" y="115" text-anchor="middle" class="label" font-size="10">[1,1]</text>

    <rect x="140" y="90" width="50" height="40" fill="#80C1FF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="165" y="115" text-anchor="middle" class="label" font-size="10">[1,2]</text>

    <rect x="200" y="90" width="50" height="40" fill="#80C1FF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="225" y="115" text-anchor="middle" class="label" font-size="10">[1,3]</text>

    <!-- Row 2 -->
    <rect x="20" y="140" width="50" height="40" fill="#4DA6FF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="45" y="165" text-anchor="middle" class="label" font-size="10">[2,0]</text>

    <rect x="80" y="140" width="50" height="40" fill="#4DA6FF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="105" y="165" text-anchor="middle" class="label" font-size="10">[2,1]</text>

    <rect x="140" y="140" width="50" height="40" fill="#4DA6FF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="165" y="165" text-anchor="middle" class="label" font-size="10">[2,2]</text>

    <rect x="200" y="140" width="50" height="40" fill="#4DA6FF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="225" y="165" text-anchor="middle" class="label" font-size="10">[2,3]</text>

    <!-- Row 3 -->
    <rect x="20" y="190" width="50" height="40" fill="#1A8CFF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="45" y="215" text-anchor="middle" class="label" font-size="10">[3,0]</text>

    <rect x="80" y="190" width="50" height="40" fill="#1A8CFF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="105" y="215" text-anchor="middle" class="label" font-size="10">[3,1]</text>

    <rect x="140" y="190" width="50" height="40" fill="#1A8CFF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="165" y="215" text-anchor="middle" class="label" font-size="10">[3,2]</text>

    <rect x="200" y="190" width="50" height="40" fill="#1A8CFF" rx="2" stroke="#333" stroke-width="1"/>
    <text x="225" y="215" text-anchor="middle" class="label" font-size="10">[3,3]</text>
  </g>

  <!-- Address formula -->
  <g transform="translate(320, 60)">
    <text x="0" y="0" class="label" font-weight="bold">Address Calculation</text>

    <rect x="0" y="10" width="250" height="120" fill="#FFE4B5" rx="3" stroke="#333" stroke-width="1"/>
    <text x="125" y="40" text-anchor="middle" font-family="Courier New, monospace" font-size="12">
      addr(D1, D0) = D1 * 4 + D0
    </text>
    <text x="125" y="70" text-anchor="middle" class="label" font-size="11">General: D1 * stride1 + D0 * stride0</text>
    <text x="125" y="100" text-anchor="middle" class="label" font-size="11">For 4×4: stride = 4</text>

    <!-- Register indices -->
    <text x="0" y="150" class="label" font-weight="bold">Resulting Registers:</text>
    <rect x="0" y="160" width="250" height="60" fill="#F5F5F5" rx="3"/>
    <text x="125" y="185" text-anchor="middle" class="label">R[0] = [0,0]</text>
    <text x="125" y="205" text-anchor="middle" class="label">R[1] = [0,1], R[2] = [0,2], ...</text>
  </g>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/isa/arch/multidim1.svg', 'w', encoding='utf-8') as f:
    f.write(svg_multidim1)
print("Created: multidim1.svg")

# acc.svg - ACC register (accumulator for CUBE)
svg_acc = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="300" viewBox="0 0 600 300">
  <style>
    text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; }
    .title { font-size: 18px; font-weight: bold; fill: #333; }
    .label { font-size: 12px; fill: #555; }
  </style>

  <text x="10" y="25" class="title">ACC Register (Accumulator for CUBE)</text>
  <text x="10" y="45" class="label">Large accumulator register with connections to Tile registers and CUBE unit</text>

  <!-- ACC register -->
  <g transform="translate(50, 60)">
    <rect x="0" y="0" width="200" height="150" fill="#A5D6A7" rx="5" stroke="#2E7D32" stroke-width="2"/>
    <text x="100" y="40" text-anchor="middle" class="label" fill="#2E7D32" font-weight="bold" font-size="18">ACC</text>
    <text x="100" y="65" text-anchor="middle" class="label">Accumulator</text>
    <text x="100" y="90" text-anchor="middle" class="label">4 × Tile size</text>
    <text x="100" y="115" text-anchor="middle" class="label">Accumulation register</text>
    <text x="100" y="135" text-anchor="middle" class="label">for matrix multiply</text>
  </g>

  <!-- Tile registers (inputs) -->
  <g transform="translate(280, 60)">
    <text x="0" y="0" class="label" font-weight="bold">Tile Registers</text>

    <rect x="0" y="15" width="80" height="40" fill="#B3D9FF" rx="3" stroke="#333" stroke-width="1"/>
    <text x="40" y="40" text-anchor="middle" class="label">D</text>

    <rect x="90" y="15" width="80" height="40" fill="#E6D9F2" rx="3" stroke="#333" stroke-width="1"/>
    <text x="130" y="40" text-anchor="middle" class="label">Z</text>

    <rect x="180" y="15" width="80" height="40" fill="#C8E6C9" rx="3" stroke="#333" stroke-width="1"/>
    <text x="220" y="40" text-anchor="middle" class="label">N</text>

    <text x="130" y="75" text-anchor="middle" class="label">Input matrices</text>
  </g>

  <!-- CUBE unit -->
  <g transform="translate(280, 150)">
    <text x="0" y="0" class="label" font-weight="bold">CUBE Unit</text>

    <rect x="0" y="10" width="260" height="80" fill="#9370DB" rx="3" stroke="#333" stroke-width="1"/>
    <text x="130" y="40" text-anchor="middle" class="label" fill="white" font-weight="bold">CUBE Multiply</text>
    <text x="130" y="60" text-anchor="middle" class="label" fill="white">D × Z → partial sums</text>
    <text x="130" y="80" text-anchor="middle" class="label" fill="white">Accumulate into ACC</text>
  </g>

  <!-- Arrows showing data flow -->
  <path d="M 270,90 L 280,90" stroke="#333" stroke-width="2" fill="none"/>
  <polygon points="285,90 275,85 275,95" fill="#333"/>

  <path d="M 270,120 L 280,130" stroke="#333" stroke-width="2" fill="none"/>
  <polygon points="285,135 275,130 283,128" fill="#333"/>

  <path d="M 350,150 L 350,130" stroke="#333" stroke-width="2" fill="none"/>
  <polygon points="350,125 345,135 355,135" fill="#333"/>

  <path d="M 250,135 L 130,135" stroke="#333" stroke-width="2" fill="none"/>
  <polygon points="125,135 135,130 135,140" fill="#333"/>

  <text x="400" y="280" text-anchor="middle" class="label">ACC = D × Z + ACC (fused multiply-accumulate)</text>
</svg>'''

with open('/Users/zhoubot/linx-isa/docs/figs/isa/arch/acc.svg', 'w', encoding='utf-8') as f:
    f.write(svg_acc)
print("Created: acc.svg")

print("Done with first batch of arch SVGs!")
