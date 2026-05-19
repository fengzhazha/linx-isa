#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const COLORS = {
  opcode: '#c7d2fe',
  regdst: '#bbf7d0',
  src: '#bae6fd',
  src3: '#fed7aa',
  imm: '#fde68a',
  funct: '#e9d5ff',
  shamt: '#fbcfe8',
  reserved: '#e5e7eb',
  border: '#94a3b8',
  text: '#0f172a',
  muted: '#475569',
  bg: '#ffffff',
  surface: '#f8fafc',
};

const DEFAULT_SPEC = path.join('isa', 'v0.56', 'linxisa-v0.56.json');
const DEFAULT_OUT_DIR = path.join('docs', 'zh', 'isa', 'wavedrom');

const EXAMPLES = [
  { mnemonic: 'ADD', file: 'enc_add.svg', title: 'ADD · 32-bit' },
  { mnemonic: 'C.ADD', file: 'enc_c_add.svg', title: 'C.ADD · 16-bit' },
  { mnemonic: 'HL.LDI', file: 'enc_hl_ldi.svg', title: 'HL.LDI · 48-bit' },
  { mnemonic: 'V.ADD', file: 'enc_v_add_parts.svg', title: 'V.ADD · 64-bit' },
];

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    spec: DEFAULT_SPEC,
    outDir: DEFAULT_OUT_DIR,
  };

  for (let i = 0; i < args.length; i += 1) {
    if (args[i] === '--spec' && args[i + 1]) {
      opts.spec = args[i + 1];
      i += 1;
    } else if (args[i] === '--out-dir' && args[i + 1]) {
      opts.outDir = args[i + 1];
      i += 1;
    }
  }

  return opts;
}

function normalizeLabel(segment) {
  const token = segment.token || segment.name || 'field';
  return token
    .replace(/^(\d+)'b/, '')
    .replace(/^(\d+)'h/i, '')
    .replace(/^(\d+)'d/i, '')
    .replace(/\[\d+:\d+\]/g, '')
    .replace(/\[(\d+)\]/g, '$1')
    .replace(/_/g, '·');
}

function isConst(segment) {
  return segment.const !== undefined || /^[0-9]+'[bhd]/i.test(segment.token || '') || /^[01]+$/.test(segment.token || '');
}

function colorFor(segment) {
  const token = (segment.token || segment.name || '').toLowerCase();

  if (isConst(segment)) {
    const constValue = segment.const && segment.const.value;
    if (constValue === 0 || token === '0' || token === "1'b0" || token === "2'b00" || token === "3'b000") {
      return COLORS.reserved;
    }
    return COLORS.funct;
  }

  if (token.includes('regdst') || token === 'rd') return COLORS.regdst;
  if (token.includes('srcd') || token.includes('rs3')) return COLORS.src3;
  if (token.includes('srcl') || token.includes('src1') || token.includes('rs1')) return COLORS.src;
  if (token.includes('srcr') || token.includes('src2') || token.includes('rs2')) return COLORS.src;
  if (token.includes('shamt')) return COLORS.shamt;
  if (token.includes('imm')) return COLORS.imm;
  if (token.includes('opcode') || token === 'op') return COLORS.opcode;
  if (token.includes('func') || token.includes('type')) return COLORS.funct;
  return COLORS.opcode;
}

function instructionByMnemonic(spec, mnemonic) {
  return (spec.instructions || []).find((inst) => inst.mnemonic === mnemonic);
}

function dimsFor(bits) {
  if (bits === 16) return { width: 560, height: 120, rowBits: 16, rows: 1 };
  if (bits === 32) return { width: 860, height: 128, rowBits: 32, rows: 1 };
  if (bits === 48) return { width: 1080, height: 136, rowBits: 48, rows: 1 };
  if (bits === 64) return { width: 860, height: 208, rowBits: 32, rows: 2 };
  return { width: 860, height: 128, rowBits: 32, rows: 1 };
}

function segmentSvg({ segment, x, y, width, height }) {
  const label = normalizeLabel(segment);
  const textX = x + width / 2;
  const textY = y + height / 2 + 4;
  const labelFont = width < 34 ? 10 : 12;
  const safeLabel = label
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  let parts = '';
  parts += `<rect x="${x}" y="${y}" width="${width}" height="${height}" rx="6" fill="${colorFor(segment)}" stroke="${COLORS.border}" stroke-width="1.25"/>`;
  if (width >= 22) {
    parts += `<text x="${textX}" y="${textY}" text-anchor="middle" font-size="${labelFont}" font-weight="600" fill="${COLORS.text}">${safeLabel}</text>`;
  }
  return parts;
}

function rowSvg({ segments, bits, x0, y0, rowWidth, title }) {
  const cell = rowWidth / bits;
  const boxY = y0 + 22;
  const boxH = 40;
  let svg = '';

  svg += `<text x="${x0 - 12}" y="${boxY + 25}" text-anchor="end" font-size="12" font-weight="700" fill="${COLORS.muted}">${title}</text>`;

  const tickStep = bits <= 16 ? 2 : 4;
  for (let bit = bits - 1; bit >= 0; bit -= tickStep) {
    const left = x0 + (bits - 1 - bit) * cell;
    svg += `<text x="${left + cell / 2}" y="${boxY - 8}" text-anchor="middle" font-size="10" fill="${COLORS.muted}">${bit}</text>`;
  }

  svg += `<rect x="${x0}" y="${boxY}" width="${rowWidth}" height="${boxH}" rx="8" fill="${COLORS.surface}" stroke="${COLORS.border}" stroke-width="1.25"/>`;

  for (const segment of segments) {
    const msb = segment.msb;
    const lsb = segment.lsb;
    const left = x0 + (bits - 1 - msb) * cell;
    const width = (msb - lsb + 1) * cell;
    svg += segmentSvg({
      segment,
      x: left,
      y: boxY,
      width,
      height: boxH,
    });
  }

  return svg;
}

function renderInstructionExample(example, inst) {
  const bits = inst.length_bits || 32;
  const dims = dimsFor(bits);
  const marginX = 92;
  const rowWidth = dims.width - marginX - 28;
  const rows = [];

  if (bits === 64) {
    const hi = inst.parts[0].segments || [];
    const lo = inst.parts[1].segments || [];
    rows.push(rowSvg({ segments: hi, bits: 32, x0: marginX, y0: 34, rowWidth, title: '高 32 位' }));
    rows.push(rowSvg({ segments: lo, bits: 32, x0: marginX, y0: 110, rowWidth, title: '低 32 位' }));
  } else {
    const segments = (inst.parts[0] && inst.parts[0].segments) || [];
    rows.push(rowSvg({ segments, bits, x0: marginX, y0: 40, rowWidth, title: `${bits} 位` }));
  }

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${dims.width} ${dims.height}" width="${dims.width}" height="${dims.height}">
  <rect width="${dims.width}" height="${dims.height}" fill="${COLORS.bg}"/>
  <text x="20" y="28" font-size="18" font-weight="700" fill="${COLORS.text}">${example.title}</text>
  <text x="20" y="${dims.height - 12}" font-size="11" fill="${COLORS.muted}">Generated from isa/v0.56/linxisa-v0.56.json</text>
  ${rows.join('\n  ')}
</svg>
`;
}

function renderLegend() {
  const items = [
    ['RegDst / 目的寄存器', COLORS.regdst],
    ['SrcL / SrcR', COLORS.src],
    ['SrcD / 第三源', COLORS.src3],
    ['Immediate / Offset', COLORS.imm],
    ['Funct / Decode 常量', COLORS.funct],
    ['Shamt', COLORS.shamt],
    ['Reserved / 0', COLORS.reserved],
  ];
  const width = 860;
  const height = 180;

  let blocks = '';
  items.forEach(([label, color], idx) => {
    const x = 28 + (idx % 2) * 390;
    const y = 54 + Math.floor(idx / 2) * 34;
    blocks += `<rect x="${x}" y="${y}" width="28" height="18" rx="5" fill="${color}" stroke="${COLORS.border}" stroke-width="1.1"/>`;
    blocks += `<text x="${x + 42}" y="${y + 13}" font-size="12" fill="${COLORS.text}">${label}</text>`;
  });

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}">
  <rect width="${width}" height="${height}" fill="${COLORS.bg}"/>
  <text x="24" y="30" font-size="18" font-weight="700" fill="${COLORS.text}">编码字段颜色图例</text>
  <text x="24" y="48" font-size="11" fill="${COLORS.muted}">颜色按字段语义分类，便于快速识别寄存器、立即数、常量和保留位。</text>
  ${blocks}
</svg>
`;
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function main() {
  const { spec: specPath, outDir } = parseArgs();
  const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
  ensureDir(outDir);

  for (const example of EXAMPLES) {
    const inst = instructionByMnemonic(spec, example.mnemonic);
    if (!inst) {
      throw new Error(`Missing mnemonic in spec: ${example.mnemonic}`);
    }
    const svg = renderInstructionExample(example, inst);
    fs.writeFileSync(path.join(outDir, example.file), svg);
  }

  fs.writeFileSync(path.join(outDir, 'encoding_legend.svg'), renderLegend());
  console.log(`Generated ${EXAMPLES.length + 1} SVG files in ${outDir}`);
}

main();
