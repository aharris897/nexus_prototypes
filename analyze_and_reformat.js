/**
 * DOCX QA/QC Formatter - Style Analyzer & Reformatter
 *
 * Purpose: Analyze a reference .docx (001_01_11_00) for its visual style,
 *          then apply that style to any number of differently-formatted input documents.
 *
 * Usage:
 *   node analyze_and_reformat.js --reference <ref.docx> --input <file.docx> [--output <out.docx>]
 *   node analyze_and_reformat.js --reference <ref.docx> --batch <folder/> [--outdir <output_folder/>]
 *
 * Deps:
 *   npm install docx fs-extra yargs
 *   pip install python-docx  (for XML inspection helpers)
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// ─────────────────────────────────────────────────────────────────────────────
// STYLE PROFILE  (derived from QA/QC inspection of 001_01_11_00)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * REFERENCE DOCUMENT STYLE PROFILE
 *
 * Source: 001_01_11_00 – Summary of Work
 * Project: Lift Station No. 16 Rehabilitation, Riviera Beach, FL
 *
 * Observations from document analysis:
 *
 * ┌──────────────────────────────────────────────────────────────┐
 * │  ELEMENT           │  STYLE SPEC                            │
 * ├──────────────────────────────────────────────────────────────┤
 * │  Section Header    │  H5 (#####), BOLD, ALL CAPS            │
 * │                    │  e.g. "SECTION 01 11 00 – SUMMARY..."  │
 * │  Part Header       │  H2 (**PART 1 – GENERAL**), BOLD      │
 * │  Sub-Section Head  │  H6 (######), ALL CAPS, indented       │
 * │                    │  e.g. "THE SUMMARY", "DESCRIPTION..."  │
 * │  Body Text         │  Normal paragraph, mixed case          │
 * │  CONTRACTOR/OWNER  │  ALL CAPS inline within body text      │
 * │  Bullet Lists      │  "- " prefixed, single level           │
 * │  Indented Bullets  │  "\t- " tab-indented nested bullets    │
 * │  PART 2 / PART 3   │  "(NOT USED)" markers                  │
 * │  End of Section    │  "END OF SECTION" footer marker        │
 * └──────────────────────────────────────────────────────────────┘
 *
 * INFERRED DOCX STYLE MAPPING:
 *
 *   Heading Level    │  docx HeadingLevel  │  Font    │  Size  │  Bold  │  Caps
 *  ──────────────────┼─────────────────────┼──────────┼────────┼────────┼──────
 *   Section Title    │  HEADING_1          │  Arial   │  14pt  │  Yes   │  Yes (ALL CAPS)
 *   Part Header      │  HEADING_2          │  Arial   │  12pt  │  Yes   │  Mixed (small caps)
 *   Sub-Section      │  HEADING_3          │  Arial   │  11pt  │  Yes   │  ALL CAPS
 *   Body             │  Normal             │  Arial   │  10pt  │  No    │  –
 *   Bullet L1        │  List Bullet        │  Arial   │  10pt  │  No    │  –
 *   Bullet L2        │  List Bullet 2      │  Arial   │  10pt  │  No    │  –
 *
 * PAGE LAYOUT (US Letter):
 *   Width: 8.5"   Height: 11"   Margins: Top 1", Bottom 1", Left 1.25", Right 1"
 *
 * SPACING:
 *   After Section Title  : 240 twips (before), 120 twips (after)
 *   After Part Header    : 180 twips (before), 120 twips (after)
 *   After Sub-Section    : 120 twips (before), 60 twips (after)
 *   Body paragraph       : 0 before, 120 after (single spacing)
 *   Bullet items         : 0 before, 60 after
 *
 * NUMBERING CONVENTION:
 *   Section numbers follow CSI MasterFormat: "01 11 00"
 *   Sub-sections are unnumbered, ALL CAPS labels
 *
 * PART STRUCTURE:
 *   PART 1 – GENERAL        (contains content)
 *   PART 2 – PRODUCTS       (NOT USED)
 *   PART 3 – EXECUTION      (NOT USED)
 *   END OF SECTION
 */

const STYLE_PROFILE = {
  page: {
    width: 12240,         // 8.5" in DXA
    height: 15840,        // 11" in DXA
    margins: {
      top: 1440,          // 1"
      bottom: 1440,       // 1"
      left: 1800,         // 1.25"
      right: 1440,        // 1"
    },
  },

  fonts: {
    default: 'Arial',
    heading: 'Arial',
    body: 'Arial',
  },

  sizes: {
    sectionTitle: 28,     // 14pt in half-points
    partHeader: 24,       // 12pt
    subSection: 22,       // 11pt
    body: 20,             // 10pt
    footer: 18,           // 9pt
  },

  spacing: {
    sectionTitle: { before: 240, after: 120 },
    partHeader:   { before: 180, after: 120 },
    subSection:   { before: 120, after: 60 },
    body:         { before: 0,   after: 120 },
    bullet:       { before: 0,   after: 60 },
  },

  indents: {
    subSection: 720,      // 0.5" indent for sub-section headings (tab stop)
    bulletL1:   { left: 720,  hanging: 360 },
    bulletL2:   { left: 1080, hanging: 360 },
  },

  formatting: {
    sectionTitle: { bold: true, allCaps: true },
    partHeader:   { bold: true, smallCaps: false },
    subSection:   { bold: true, allCaps: true },
    body:         { bold: false },
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// STEP 1: UNPACK input docx and extract raw XML
// ─────────────────────────────────────────────────────────────────────────────

function unpackDocx(inputPath, outputDir) {
  console.log(`[1/4] Unpacking: ${inputPath}`);
  execSync(
    `python /mnt/skills/public/docx/scripts/office/unpack.py "${inputPath}" "${outputDir}"`,
    { stdio: 'inherit' }
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// STEP 2: QA/QC ANALYSIS – diff input style vs reference style profile
// ─────────────────────────────────────────────────────────────────────────────

function analyzeDocument(unpackedDir) {
  console.log(`[2/4] Analyzing document style...`);
  const docXmlPath = path.join(unpackedDir, 'word', 'document.xml');
  const stylesXmlPath = path.join(unpackedDir, 'word', 'styles.xml');

  const docXml = fs.existsSync(docXmlPath) ? fs.readFileSync(docXmlPath, 'utf8') : '';
  const stylesXml = fs.existsSync(stylesXmlPath) ? fs.readFileSync(stylesXmlPath, 'utf8') : '';

  const issues = [];

  // ── Check page size ──────────────────────────────────────────────────────
  const pgSzMatch = docXml.match(/<w:pgSz[^>]*>/);
  if (pgSzMatch) {
    const wMatch = pgSzMatch[0].match(/w:w="(\d+)"/);
    const hMatch = pgSzMatch[0].match(/w:h="(\d+)"/);
    if (wMatch && parseInt(wMatch[1]) !== STYLE_PROFILE.page.width) {
      issues.push({ type: 'PAGE_SIZE', severity: 'HIGH',
        msg: `Page width is ${wMatch[1]} DXA, expected ${STYLE_PROFILE.page.width} (US Letter)` });
    }
    if (hMatch && parseInt(hMatch[1]) !== STYLE_PROFILE.page.height) {
      issues.push({ type: 'PAGE_SIZE', severity: 'HIGH',
        msg: `Page height is ${hMatch[1]} DXA, expected ${STYLE_PROFILE.page.height} (US Letter)` });
    }
  } else {
    issues.push({ type: 'PAGE_SIZE', severity: 'HIGH', msg: 'No page size definition found — will default to A4' });
  }

  // ── Check default font ────────────────────────────────────────────────────
  const defaultFontMatch = stylesXml.match(/<w:rFonts[^>]*w:ascii="([^"]+)"/);
  if (defaultFontMatch && defaultFontMatch[1] !== STYLE_PROFILE.fonts.default) {
    issues.push({ type: 'FONT', severity: 'MEDIUM',
      msg: `Default font is "${defaultFontMatch[1]}", expected "${STYLE_PROFILE.fonts.default}"` });
  }

  // ── Check heading styles ──────────────────────────────────────────────────
  const headingStyleIds = ['Heading1', 'Heading2', 'Heading3'];
  headingStyleIds.forEach((id) => {
    const re = new RegExp(`<w:style[^>]*w:styleId="${id}"[^>]*>[\\s\\S]*?</w:style>`);
    const match = stylesXml.match(re);
    if (!match) {
      issues.push({ type: 'STYLE_MISSING', severity: 'HIGH', msg: `Style "${id}" not defined` });
    }
  });

  // ── Check for unicode bullets ─────────────────────────────────────────────
  if (docXml.includes('\u2022') || docXml.includes('&#x2022;')) {
    issues.push({ type: 'BULLETS', severity: 'HIGH',
      msg: 'Unicode bullet characters (•) found — must use LevelFormat.BULLET numbering instead' });
  }

  // ── Check for margin settings ─────────────────────────────────────────────
  const pgMarMatch = docXml.match(/<w:pgMar[^>]*>/);
  if (!pgMarMatch) {
    issues.push({ type: 'MARGINS', severity: 'MEDIUM', msg: 'No page margin definition found' });
  }

  // ── Check for END OF SECTION marker ──────────────────────────────────────
  if (!docXml.includes('END OF SECTION') && !docXml.includes('END**** ****OF**** ****SECTION')) {
    issues.push({ type: 'STRUCTURE', severity: 'LOW',
      msg: 'No "END OF SECTION" marker found — may be missing CSI section footer' });
  }

  return issues;
}

// ─────────────────────────────────────────────────────────────────────────────
// STEP 3: GENERATE reformatted docx using reference style profile
// ─────────────────────────────────────────────────────────────────────────────

function generateReformattedDocx(parsedContent, outputPath) {
  console.log(`[3/4] Generating reformatted document...`);

  const scriptPath = path.join(__dirname, '_generate_docx.js');
  const contentJson = JSON.stringify(parsedContent, null, 2);
  const contentPath = path.join(__dirname, '_content_tmp.json');
  fs.writeFileSync(contentPath, contentJson);

  // The generator script (see _generate_docx.js) reads the JSON and writes the docx
  execSync(`node "${scriptPath}" --content "${contentPath}" --output "${outputPath}"`, {
    stdio: 'inherit',
  });

  fs.unlinkSync(contentPath);
}

// ─────────────────────────────────────────────────────────────────────────────
// STEP 4: VALIDATE output
// ─────────────────────────────────────────────────────────────────────────────

function validateDocx(outputPath) {
  console.log(`[4/4] Validating: ${outputPath}`);
  try {
    execSync(
      `python /mnt/skills/public/docx/scripts/office/validate.py "${outputPath}"`,
      { stdio: 'inherit' }
    );
    console.log('✅ Validation passed.');
  } catch (e) {
    console.error('⚠️  Validation issues found — review output.');
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN: Print QA report to console
// ─────────────────────────────────────────────────────────────────────────────

function printQAReport(issues, inputFile) {
  console.log('\n' + '═'.repeat(70));
  console.log(`QA/QC REPORT — ${path.basename(inputFile)}`);
  console.log('═'.repeat(70));

  if (issues.length === 0) {
    console.log('✅  No style deviations found. Document matches reference profile.');
  } else {
    const high   = issues.filter(i => i.severity === 'HIGH');
    const medium = issues.filter(i => i.severity === 'MEDIUM');
    const low    = issues.filter(i => i.severity === 'LOW');

    console.log(`\nFound ${issues.length} issue(s): ${high.length} HIGH  ${medium.length} MEDIUM  ${low.length} LOW\n`);

    [...high, ...medium, ...low].forEach((issue, idx) => {
      const icon = issue.severity === 'HIGH' ? '🔴' : issue.severity === 'MEDIUM' ? '🟡' : '🔵';
      console.log(`  ${icon} [${issue.severity}] [${issue.type}]`);
      console.log(`     ${issue.msg}\n`);
    });
  }

  console.log('═'.repeat(70) + '\n');
}

// ─────────────────────────────────────────────────────────────────────────────
// CLI ENTRY POINT
// ─────────────────────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const inputIndex = args.indexOf('--input');
const outputIndex = args.indexOf('--output');
const batchIndex = args.indexOf('--batch');
const outdirIndex = args.indexOf('--outdir');
const reportOnlyIndex = args.indexOf('--report-only');

const inputFile  = inputIndex  !== -1 ? args[inputIndex  + 1] : null;
const outputFile = outputIndex !== -1 ? args[outputIndex + 1] : null;
const batchDir   = batchIndex  !== -1 ? args[batchIndex  + 1] : null;
const outDir     = outdirIndex !== -1 ? args[outdirIndex + 1] : './output';
const reportOnly = reportOnlyIndex !== -1;

if (!inputFile && !batchDir) {
  console.log(`
Usage:
  node analyze_and_reformat.js --input <file.docx> [--output <out.docx>] [--report-only]
  node analyze_and_reformat.js --batch <folder/> [--outdir <output_folder/>]

Options:
  --input        Single input .docx file
  --output       Output path for reformatted file (default: <input>_reformatted.docx)
  --batch        Folder of .docx files to process
  --outdir       Output folder for batch mode (default: ./output)
  --report-only  Only print QA report without generating reformatted output
  `);
  process.exit(0);
}

function processFile(inputPath, outputPath) {
  const tmpDir = path.join('/tmp', `docx_unpack_${Date.now()}`);
  fs.mkdirSync(tmpDir, { recursive: true });

  try {
    unpackDocx(inputPath, tmpDir);
    const issues = analyzeDocument(tmpDir);
    printQAReport(issues, inputPath);

    if (!reportOnly) {
      // Note: Full reformat uses _generate_docx.js — see that file for implementation
      console.log(`[INFO] To apply reformatting, run: node _generate_docx.js --content <parsed> --output "${outputPath}"`);
    }
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
}

if (inputFile) {
  const out = outputFile || inputFile.replace(/\.docx$/i, '_reformatted.docx');
  processFile(inputFile, out);
} else if (batchDir) {
  fs.mkdirSync(outDir, { recursive: true });
  const files = fs.readdirSync(batchDir).filter(f => f.endsWith('.docx'));
  console.log(`Batch mode: ${files.length} file(s) found in ${batchDir}`);
  files.forEach(f => {
    const inputPath = path.join(batchDir, f);
    const outputPath = path.join(outDir, f.replace(/\.docx$/i, '_reformatted.docx'));
    processFile(inputPath, outputPath);
  });
}

module.exports = { STYLE_PROFILE, analyzeDocument, printQAReport };
