/**
 * _generate_docx.js
 *
 * Applies the reference style profile (from 001_01_11_00 – Summary of Work)
 * to a parsed content JSON and writes a fully formatted .docx output.
 *
 * Called by analyze_and_reformat.js, or can be run standalone:
 *   node _generate_docx.js --content content.json --output output.docx
 *
 * Content JSON format:  See CONTENT_SCHEMA below.
 */

const {
  Document, Packer, Paragraph, TextRun, Header, Footer,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  PageNumber, NumberFormat, TabStopType, TabStopPosition,
} = require('docx');
const fs = require('fs');
const path = require('path');

// ─────────────────────────────────────────────────────────────────────────────
// CONTENT SCHEMA
// Each block in the content array has a "type" and "text" (plus optional flags)
//
// Types:
//   "section_title"   → SECTION 01 11 00 – SUMMARY OF WORK  (H1, bold, caps)
//   "part_header"     → PART 1 – GENERAL                    (H2, bold)
//   "subsection"      → THE SUMMARY / CONTRACTOR RESP...    (H3, bold, caps, indented)
//   "body"            → Normal paragraph text
//   "bullet"          → Level 1 bullet item
//   "bullet_indent"   → Level 2 (indented) bullet item
//   "not_used"        → PART 2 – PRODUCTS (NOT USED)        (H2, bold, italic marker)
//   "end_of_section"  → END OF SECTION                       (centered, bold, caps)
//   "spacer"          → empty paragraph for vertical spacing
// ─────────────────────────────────────────────────────────────────────────────

const PROFILE = {
  page: { width: 12240, height: 15840,
    margins: { top: 1440, bottom: 1440, left: 1800, right: 1440 } },
  font: 'Arial',
  sizes: { sectionTitle: 28, partHeader: 24, subSection: 22, body: 20, footer: 18 },
  spacing: {
    sectionTitle: { before: 240, after: 120 },
    partHeader:   { before: 200, after: 120 },
    subSection:   { before: 160, after: 60 },
    body:         { before: 0,   after: 120 },
    bullet:       { before: 0,   after: 60 },
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// PARAGRAPH BUILDERS
// ─────────────────────────────────────────────────────────────────────────────

function makeSectionTitle(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: PROFILE.spacing.sectionTitle,
    alignment: AlignmentType.LEFT,
    children: [
      new TextRun({
        text: text.toUpperCase(),
        bold: true,
        allCaps: true,
        font: PROFILE.font,
        size: PROFILE.sizes.sectionTitle,
      }),
    ],
  });
}

function makePartHeader(text, notUsed = false) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: PROFILE.spacing.partHeader,
    children: [
      new TextRun({
        text: text,
        bold: true,
        font: PROFILE.font,
        size: PROFILE.sizes.partHeader,
      }),
      ...(notUsed ? [new TextRun({
        text: ' (NOT USED)',
        bold: true,
        italics: true,
        font: PROFILE.font,
        size: PROFILE.sizes.partHeader,
      })] : []),
    ],
  });
}

function makeSubSection(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: PROFILE.spacing.subSection,
    indent: { left: 720 },   // 0.5" indent
    children: [
      new TextRun({
        text: text.toUpperCase(),
        bold: true,
        allCaps: true,
        font: PROFILE.font,
        size: PROFILE.sizes.subSection,
      }),
    ],
  });
}

function makeBody(text) {
  // Detect inline ALL-CAPS terms (CONTRACTOR, OWNER, ENGINEER, etc.) — preserve as-is
  return new Paragraph({
    spacing: PROFILE.spacing.body,
    children: [
      new TextRun({
        text: text,
        font: PROFILE.font,
        size: PROFILE.sizes.body,
      }),
    ],
  });
}

function makeBullet(text, level = 0) {
  const ref = level === 0 ? 'bullet-l1' : 'bullet-l2';
  return new Paragraph({
    numbering: { reference: ref, level: 0 },
    spacing: PROFILE.spacing.bullet,
    children: [
      new TextRun({
        text: text,
        font: PROFILE.font,
        size: PROFILE.sizes.body,
      }),
    ],
  });
}

function makeEndOfSection() {
  return new Paragraph({
    spacing: { before: 360, after: 0 },
    alignment: AlignmentType.CENTER,
    children: [
      new TextRun({
        text: 'END OF SECTION',
        bold: true,
        allCaps: true,
        font: PROFILE.font,
        size: PROFILE.sizes.body,
      }),
    ],
  });
}

function makeSpacer() {
  return new Paragraph({ spacing: { before: 0, after: 60 }, children: [] });
}

// ─────────────────────────────────────────────────────────────────────────────
// DOCUMENT BUILDER
// ─────────────────────────────────────────────────────────────────────────────

function buildDocument(blocks) {
  const children = [];

  for (const block of blocks) {
    switch (block.type) {
      case 'section_title':    children.push(makeSectionTitle(block.text)); break;
      case 'part_header':      children.push(makePartHeader(block.text, false)); break;
      case 'not_used':         children.push(makePartHeader(block.text, true)); break;
      case 'subsection':       children.push(makeSubSection(block.text)); break;
      case 'body':             children.push(makeBody(block.text)); break;
      case 'bullet':           children.push(makeBullet(block.text, 0)); break;
      case 'bullet_indent':    children.push(makeBullet(block.text, 1)); break;
      case 'end_of_section':   children.push(makeEndOfSection()); break;
      case 'spacer':           children.push(makeSpacer()); break;
      default:
        console.warn(`[WARN] Unknown block type: "${block.type}" — rendered as body`);
        children.push(makeBody(block.text || ''));
    }
  }

  return new Document({
    numbering: {
      config: [
        {
          reference: 'bullet-l1',
          levels: [{
            level: 0,
            format: LevelFormat.BULLET,
            text: '\u2022',
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } },
          }],
        },
        {
          reference: 'bullet-l2',
          levels: [{
            level: 0,
            format: LevelFormat.BULLET,
            text: '\u2013',        // en-dash for level 2
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 1080, hanging: 360 } } },
          }],
        },
      ],
    },

    styles: {
      default: {
        document: { run: { font: PROFILE.font, size: PROFILE.sizes.body } },
      },
      paragraphStyles: [
        {
          id: 'Heading1',
          name: 'Heading 1',
          basedOn: 'Normal',
          next: 'Normal',
          quickFormat: true,
          run: { size: PROFILE.sizes.sectionTitle, bold: true, allCaps: true, font: PROFILE.font },
          paragraph: { spacing: PROFILE.spacing.sectionTitle, outlineLevel: 0 },
        },
        {
          id: 'Heading2',
          name: 'Heading 2',
          basedOn: 'Normal',
          next: 'Normal',
          quickFormat: true,
          run: { size: PROFILE.sizes.partHeader, bold: true, font: PROFILE.font },
          paragraph: { spacing: PROFILE.spacing.partHeader, outlineLevel: 1 },
        },
        {
          id: 'Heading3',
          name: 'Heading 3',
          basedOn: 'Normal',
          next: 'Normal',
          quickFormat: true,
          run: { size: PROFILE.sizes.subSection, bold: true, allCaps: true, font: PROFILE.font },
          paragraph: { spacing: PROFILE.spacing.subSection, indent: { left: 720 }, outlineLevel: 2 },
        },
      ],
    },

    sections: [
      {
        properties: {
          page: {
            size: { width: PROFILE.page.width, height: PROFILE.page.height },
            margin: PROFILE.page.margins,
          },
        },
        headers: {
          default: new Header({
            children: [
              new Paragraph({
                border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: '444444', space: 1 } },
                spacing: { after: 120 },
                children: [
                  new TextRun({
                    text: 'LIFT STATION NO. 16 REHABILITATION – TECHNICAL SPECIFICATIONS',
                    font: PROFILE.font,
                    size: PROFILE.sizes.footer,
                    color: '444444',
                  }),
                ],
              }),
            ],
          }),
        },
        footers: {
          default: new Footer({
            children: [
              new Paragraph({
                border: { top: { style: BorderStyle.SINGLE, size: 6, color: '444444', space: 1 } },
                tabStops: [
                  { type: TabStopType.RIGHT, position: TabStopPosition.MAX },
                ],
                children: [
                  new TextRun({ text: 'Page ', font: PROFILE.font, size: PROFILE.sizes.footer }),
                  new TextRun({ children: [PageNumber.CURRENT], font: PROFILE.font, size: PROFILE.sizes.footer }),
                  new TextRun({ text: '\t', font: PROFILE.font, size: PROFILE.sizes.footer }),
                  new TextRun({ text: 'City of Riviera Beach Utility Special District', font: PROFILE.font, size: PROFILE.sizes.footer, color: '666666' }),
                ],
              }),
            ],
          }),
        },
        children,
      },
    ],
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// CLI
// ─────────────────────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const contentIndex = args.indexOf('--content');
const outputIndex  = args.indexOf('--output');

if (contentIndex === -1 || outputIndex === -1) {
  console.log('Usage: node _generate_docx.js --content <content.json> --output <output.docx>');
  process.exit(1);
}

const contentPath = args[contentIndex + 1];
const outputPath  = args[outputIndex  + 1];

const rawContent = JSON.parse(fs.readFileSync(contentPath, 'utf8'));
const doc = buildDocument(rawContent.blocks || rawContent);

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outputPath, buffer);
  console.log(`✅ Written: ${outputPath}`);
}).catch(err => {
  console.error('❌ Error generating docx:', err);
  process.exit(1);
});
