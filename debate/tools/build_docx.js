// Build the definitions .docx from an ordered JSON export.
// Usage: node build_docx.js ordered.json output.docx
// Headings follow Verbatim conventions: H1 = section (pocket), H2 = term (hat), H4 = card tag.
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, ExternalHyperlink,
  InternalHyperlink, Bookmark, AlignmentType, PageBreak, Footer, PageNumber, BorderStyle,
} = require("docx");

const [, , inPath, outPath] = process.argv;
const data = JSON.parse(fs.readFileSync(inPath, "utf8"));
const LQ = "“", RQ = "”";
const slug = (s) => "t_" + s.replace(/[^a-z0-9]+/gi, "_").slice(0, 36);

const total = data.sections.reduce((n, s) => n + s.terms.reduce((m, t) => m + t.entries.length, 0), 0);
const nTerms = data.sections.reduce((n, s) => n + s.terms.length, 0);

const body = [];

// Title + intro
body.push(new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun("2026–27 CCA Resolution: Definitions File")] }));
body.push(new Paragraph({
  spacing: { after: 200 },
  border: { left: { style: BorderStyle.SINGLE, size: 18, color: "1F4E79", space: 8 } },
  children: [new TextRun({ text: data.resolution, bold: true, size: 26 })],
}));
body.push(new Paragraph({ spacing: { after: 120 }, children: [
  new TextRun({ text: `${total} definitions across ${nTerms} terms and phrases. `, bold: true }),
  new TextRun("Every quote was copied from the live source page and checked word-for-word against that page's text on 2026-10-09; only spacing and curly-vs-straight quote marks may differ from the page. Entries that failed the check were removed."),
] }));
body.push(new Paragraph({ spacing: { after: 120 }, children: [
  new TextRun("Card format: "), new TextRun({ text: "tag", bold: true }),
  new TextRun(" → citation (source, author, title, date, link, access date, source type) → "),
  new TextRun({ text: "context note", italics: true }), new TextRun(" → the full unedited quote."),
] }));
body.push(new Paragraph({ spacing: { after: 240 }, children: [
  new TextRun("Headings use Word's built-in styles (Heading 1 = section, Heading 2 = term, Heading 4 = card tag), so View → Navigation Pane jumps anywhere and cards paste cleanly into Verbatim."),
] }));

// Contents (internal links, no field update prompt)
body.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Contents")] }));
for (const s of data.sections) {
  body.push(new Paragraph({ spacing: { before: 100, after: 20 }, children: [new TextRun({ text: s.heading, bold: true })] }));
  for (const t of s.terms) {
    body.push(new Paragraph({ indent: { left: 360 }, spacing: { after: 0 }, children: [
      new InternalHyperlink({ anchor: slug(t.term), children: [new TextRun({ text: `${LQ}${t.term}${RQ}`, style: "Hyperlink" })] }),
      new TextRun({ text: `  (${t.entries.length})`, color: "666666" }),
    ] }));
  }
}

// Cards
for (const s of data.sections) {
  body.push(new Paragraph({ children: [new PageBreak()] }));
  body.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(s.heading)] }));
  for (const t of s.terms) {
    body.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: [
      new Bookmark({ id: slug(t.term), children: [new TextRun(`${LQ}${t.term}${RQ} (${t.entries.length})`)] }),
    ] }));
    for (const e of t.entries) {
      body.push(new Paragraph({ heading: HeadingLevel.HEADING_4, keepNext: true, children: [new TextRun(e.tag || "")] }));
      const cite = [new TextRun({ text: e.source, bold: true, size: 24 })];
      const rest = [];
      if (e.author && e.author !== e.source) rest.push(e.author);
      if (e.title) rest.push(`${LQ}${e.title}${RQ}`);
      rest.push(e.date || "n.d.");
      cite.push(new TextRun({ text: ", " + rest.join(", ") + ", ", size: 18 }));
      cite.push(new ExternalHyperlink({ link: e.url, children: [new TextRun({ text: e.url, style: "Hyperlink", size: 18 })] }));
      cite.push(new TextRun({ text: `, accessed ${e.accessed || "2026-10-09"} — `, size: 18 }));
      cite.push(new TextRun({ text: e.source_type || "", italics: true, size: 18 }));
      body.push(new Paragraph({ keepNext: true, spacing: { after: 60 }, children: cite }));
      if (e.context) {
        body.push(new Paragraph({ keepNext: true, spacing: { after: 60 }, children: [
          new TextRun({ text: "Context: " + e.context, italics: true, size: 18, color: "595959" }),
        ] }));
      }
      const lines = e.quote.trim().split(/\n+/).filter((l) => l.trim());
      lines.forEach((ln, i) => body.push(new Paragraph({
        spacing: { after: i === lines.length - 1 ? 280 : 60 },
        children: [new TextRun({ text: ln.trim(), size: 22 })],
      })));
    }
  }
}

const doc = new Document({
  creator: "CCA definitions research",
  title: "2026-27 CCA Resolution Definitions",
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", next: "Normal", run: { font: "Calibri", size: 40, bold: true, color: "1F4E79" }, paragraph: { spacing: { after: 200 } } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Calibri", size: 36, bold: true, color: "1F4E79" }, paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: "1F4E79", space: 4 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Calibri", size: 30, bold: true, color: "2E75B6" }, paragraph: { spacing: { before: 320, after: 160 }, outlineLevel: 1, keepNext: true } },
      { id: "Heading4", name: "Heading 4", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Calibri", size: 26, bold: true }, paragraph: { spacing: { before: 200, after: 60 }, outlineLevel: 3, keepNext: true } },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
      new TextRun({ text: "2026–27 CCA Definitions — page ", size: 16, color: "808080" }),
      new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "808080" }),
    ] })] }) },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(outPath, buf);
  console.log(`wrote ${outPath}: ${total} cards, ${nTerms} terms`);
});
