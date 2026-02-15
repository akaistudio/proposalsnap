/**
 * ProposalSnap PPTX Generator v2
 * Professional presentations with infographics, decorative elements, and visual layouts
 */
const pptxgen = require("pptxgenjs");
const fs = require("fs");

let inputData = "";
process.stdin.on("data", chunk => inputData += chunk);
process.stdin.on("end", async () => {
  try {
    const data = JSON.parse(inputData);
    await generatePresentation(data);
  } catch (e) {
    console.error("Error:", e.message);
    process.exit(1);
  }
});

async function generatePresentation(data) {
  const {
    outputPath, clientName, companyName, presentationType,
    tone, slides, colors, logoPath, fontStyle
  } = data;

  const fontMap = {
    aptos: { header: "Aptos", body: "Aptos" },
    georgia: { header: "Georgia", body: "Calibri" },
    arial: { header: "Arial Black", body: "Arial" },
    trebuchet: { header: "Trebuchet MS", body: "Calibri" },
    palatino: { header: "Palatino", body: "Garamond" },
    cambria: { header: "Cambria", body: "Calibri" }
  };
  const fonts = fontMap[fontStyle] || fontMap.aptos;
  const hFont = fonts.header;
  const bFont = fonts.body;

  const primary = colors.primary || "1E2761";
  const secondary = colors.secondary || "CADCFC";
  const accent = colors.accent || "4A90D9";
  const dark = colors.dark || "0F1629";
  const light = colors.light || "F8F9FA";
  const textDark = colors.textDark || "1A1A2E";
  const textLight = colors.textLight || "FFFFFF";
  const textMuted = colors.textMuted || "6B7280";

  let pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = companyName || "ProposalSnap";
  pres.title = slides[0]?.title || "Proposal";

  const cardShadow = () => ({ type: "outer", blur: 6, offset: 2, angle: 135, color: "000000", opacity: 0.1 });
  const softShadow = () => ({ type: "outer", blur: 4, offset: 1, angle: 135, color: "000000", opacity: 0.06 });

  // ── DECORATIVE HELPERS ──
  function addCornerBrackets(slide, color, size) {
    size = size || 0.4;
    const w = 0.03;
    slide.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 0.3, w: size, h: w, fill: { color } });
    slide.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 0.3, w: w, h: size, fill: { color } });
    slide.addShape(pres.shapes.RECTANGLE, { x: 10 - 0.3 - size, y: 0.3, w: size, h: w, fill: { color } });
    slide.addShape(pres.shapes.RECTANGLE, { x: 10 - 0.3 - w, y: 0.3, w: w, h: size, fill: { color } });
    slide.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 5.625 - 0.3 - w, w: size, h: w, fill: { color } });
    slide.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 5.625 - 0.3 - size, w: w, h: size, fill: { color } });
    slide.addShape(pres.shapes.RECTANGLE, { x: 10 - 0.3 - size, y: 5.625 - 0.3 - w, w: size, h: w, fill: { color } });
    slide.addShape(pres.shapes.RECTANGLE, { x: 10 - 0.3 - w, y: 5.625 - 0.3 - size, w: w, h: size, fill: { color } });
  }

  function addTopAccentBar(slide, color) {
    slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color } });
  }

  function addBottomAccentBar(slide, color) {
    slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.565, w: 10, h: 0.06, fill: { color } });
  }

  function addSideStripe(slide, color) {
    slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.08, h: 5.625, fill: { color } });
  }

  function addDecoCircle(slide, x, y, size, color, opacity) {
    opacity = opacity || 0.06;
    slide.addShape(pres.shapes.OVAL, {
      x: x, y: y, w: size, h: size, fill: { color: color, transparency: Math.round((1 - opacity) * 100) }
    });
  }

  function addDotGrid(slide, x, y, cols, rows, color) {
    var spacing = 0.18;
    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        slide.addShape(pres.shapes.OVAL, {
          x: x + c * spacing, y: y + r * spacing, w: 0.05, h: 0.05,
          fill: { color: color, transparency: 88 }
        });
      }
    }
  }

  function addSectionLabel(slide, text, x, y, color) {
    slide.addShape(pres.shapes.RECTANGLE, { x: x, y: y + 0.02, w: 0.04, h: 0.22, fill: { color } });
    slide.addText(text.toUpperCase(), {
      x: x + 0.15, y: y, w: 3, h: 0.26, fontSize: 9, fontFace: bFont,
      color: color, bold: true, margin: 0
    });
  }

  function addLogo(slide, x, y, w) {
    if (logoPath && fs.existsSync(logoPath)) {
      try {
        var logoData = fs.readFileSync(logoPath);
        var ext = logoPath.toLowerCase().endsWith(".png") ? "png" : "jpeg";
        var b64 = "image/" + ext + ";base64," + logoData.toString("base64");
        slide.addImage({ data: b64, x: x, y: y, w: w, h: w * 0.6, sizing: { type: "contain", w: w, h: w * 0.6 } });
      } catch (e) {}
    }
  }

  function addFooter(slide, pageNum, total, bgColor) {
    bgColor = bgColor || dark;
    slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.1, w: 10, h: 0.525, fill: { color: bgColor } });
    slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 5.1, w: 0.5, h: 0.03, fill: { color: accent } });
    slide.addText(companyName || "", {
      x: 0.5, y: 5.12, w: 4, h: 0.5, fontSize: 9, color: textMuted, fontFace: bFont, valign: "middle", margin: 0
    });
    slide.addText(pageNum + " / " + total, {
      x: 8, y: 5.12, w: 1.5, h: 0.5, fontSize: 9, color: textMuted, fontFace: bFont, align: "right", valign: "middle", margin: 0
    });
  }

  var totalSlides = slides.length;

  slides.forEach(function(sd, idx) {
    var slide = pres.addSlide();
    var sType = sd.layout || "content";

    // ═══ TITLE SLIDE ═══
    if (sType === "title") {
      slide.background = { color: dark };
      addTopAccentBar(slide, accent);
      addBottomAccentBar(slide, accent);
      addCornerBrackets(slide, accent, 0.5);
      addDecoCircle(slide, 7.5, -1.5, 5, accent, 0.04);
      addDecoCircle(slide, -1.5, 3.5, 4, primary, 0.03);
      addDotGrid(slide, 8.2, 4.2, 5, 4, accent);

      addLogo(slide, 0.6, 0.5, 1.8);

      slide.addText(sd.title || "", {
        x: 0.6, y: 1.6, w: 8.8, h: 1.5, fontSize: 42, fontFace: hFont,
        color: textLight, bold: true, margin: 0
      });
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 3.15, w: 1.5, h: 0.05, fill: { color: accent } });
      slide.addText(sd.subtitle || "", {
        x: 0.6, y: 3.35, w: 8.8, h: 0.5, fontSize: 18, fontFace: bFont, color: secondary, margin: 0
      });
      var dateStr = new Date().toLocaleDateString("en-US", { month: "long", year: "numeric" });
      slide.addText("Prepared for " + (clientName || "Client") + "  \u00B7  " + dateStr, {
        x: 0.6, y: 4.1, w: 8.8, h: 0.4, fontSize: 12, fontFace: bFont, color: textMuted, margin: 0
      });

    // ═══ AGENDA ═══
    } else if (sType === "agenda") {
      slide.background = { color: light };
      addSideStripe(slide, accent);
      addDecoCircle(slide, 7.5, 3.5, 3, accent, 0.04);

      slide.addText(sd.title || "Agenda", {
        x: 0.6, y: 0.35, w: 8.8, h: 0.7, fontSize: 32, fontFace: hFont, color: textDark, bold: true, margin: 0
      });
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 1.05, w: 1, h: 0.04, fill: { color: accent } });

      var items = sd.bullets || [];
      items.forEach(function(item, i) {
        var yPos = 1.35 + i * 0.58;
        slide.addShape(pres.shapes.OVAL, { x: 0.6, y: yPos + 0.02, w: 0.4, h: 0.4, fill: { color: accent } });
        slide.addText("" + (i + 1), {
          x: 0.6, y: yPos + 0.02, w: 0.4, h: 0.4, fontSize: 14, fontFace: hFont,
          color: textLight, bold: true, align: "center", valign: "middle", margin: 0
        });
        slide.addText(item, {
          x: 1.2, y: yPos, w: 7.8, h: 0.44, fontSize: 15, fontFace: bFont, color: textDark, valign: "middle", margin: 0
        });
        if (i < items.length - 1) {
          slide.addShape(pres.shapes.RECTANGLE, { x: 1.2, y: yPos + 0.5, w: 7.8, h: 0.005, fill: { color: secondary } });
        }
      });
      addFooter(slide, idx + 1, totalSlides);

    // ═══ TWO COLUMN ═══
    } else if (sType === "two_column") {
      slide.background = { color: light };
      addSideStripe(slide, accent);

      slide.addText(sd.title || "", {
        x: 0.6, y: 0.35, w: 8.8, h: 0.6, fontSize: 28, fontFace: hFont, color: textDark, bold: true, margin: 0
      });
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 0.95, w: 0.8, h: 0.04, fill: { color: accent } });

      // Left card
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.2, w: 4.3, h: 3.5, fill: { color: "FFFFFF" }, shadow: cardShadow() });
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.2, w: 4.3, h: 0.05, fill: { color: accent } });
      slide.addText(sd.left_title || "", { x: 0.75, y: 1.4, w: 3.8, h: 0.4, fontSize: 15, fontFace: hFont, color: primary, bold: true, margin: 0 });
      var lb = (sd.left_bullets || []).map(function(b, i, a) {
        return { text: b, options: { bullet: { code: "25CF" }, fontSize: 12, fontFace: bFont, color: textDark, breakLine: i < a.length - 1, paraSpaceAfter: 5 } };
      });
      if (lb.length) slide.addText(lb, { x: 0.75, y: 1.9, w: 3.8, h: 2.6, valign: "top", margin: 0 });

      // Right card
      slide.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 1.2, w: 4.3, h: 3.5, fill: { color: "FFFFFF" }, shadow: cardShadow() });
      slide.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 1.2, w: 4.3, h: 0.05, fill: { color: primary } });
      slide.addText(sd.right_title || "", { x: 5.45, y: 1.4, w: 3.8, h: 0.4, fontSize: 15, fontFace: hFont, color: primary, bold: true, margin: 0 });
      var rb = (sd.right_bullets || []).map(function(b, i, a) {
        return { text: b, options: { bullet: { code: "25CF" }, fontSize: 12, fontFace: bFont, color: textDark, breakLine: i < a.length - 1, paraSpaceAfter: 5 } };
      });
      if (rb.length) slide.addText(rb, { x: 5.45, y: 1.9, w: 3.8, h: 2.6, valign: "top", margin: 0 });

      addFooter(slide, idx + 1, totalSlides);

    // ═══ STATS ═══
    } else if (sType === "stats") {
      slide.background = { color: dark };
      addCornerBrackets(slide, accent, 0.35);
      addDecoCircle(slide, -1, -1, 4, accent, 0.03);
      addDotGrid(slide, 8.5, 0.4, 4, 3, accent);

      addSectionLabel(slide, sd.title || "Key Metrics", 0.6, 0.4, accent);
      slide.addText(sd.title || "Key Metrics", {
        x: 0.6, y: 0.7, w: 8.8, h: 0.6, fontSize: 28, fontFace: hFont, color: textLight, bold: true, margin: 0
      });

      var stats = sd.stats || [];
      var cols = Math.min(stats.length, 4);
      var cardW = (9 - (cols - 1) * 0.25) / cols;

      stats.forEach(function(stat, i) {
        var xPos = 0.5 + i * (cardW + 0.25);
        slide.addShape(pres.shapes.RECTANGLE, { x: xPos, y: 1.55, w: cardW, h: 2.8, fill: { color: primary, transparency: 60 } });
        slide.addShape(pres.shapes.RECTANGLE, { x: xPos, y: 1.55, w: cardW, h: 0.05, fill: { color: accent } });
        slide.addText(stat.value || "", {
          x: xPos, y: 1.8, w: cardW, h: 1.1, fontSize: 40, fontFace: hFont, color: accent, bold: true, align: "center", valign: "middle", margin: 0
        });
        slide.addText((stat.label || "").toUpperCase(), {
          x: xPos, y: 2.9, w: cardW, h: 0.4, fontSize: 11, fontFace: bFont, color: secondary, align: "center", bold: true, margin: 0
        });
        if (stat.description) {
          slide.addText(stat.description, {
            x: xPos + 0.15, y: 3.3, w: cardW - 0.3, h: 0.8, fontSize: 10, fontFace: bFont, color: textMuted, align: "center", valign: "top", margin: 0
          });
        }
      });
      addFooter(slide, idx + 1, totalSlides, dark);

    // ═══ TIMELINE ═══
    } else if (sType === "timeline") {
      slide.background = { color: light };
      addSideStripe(slide, accent);

      slide.addText(sd.title || "", {
        x: 0.6, y: 0.35, w: 8.8, h: 0.6, fontSize: 28, fontFace: hFont, color: textDark, bold: true, margin: 0
      });
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 0.95, w: 0.8, h: 0.04, fill: { color: accent } });

      var steps = sd.steps || [];
      var stepW = (9 - (steps.length - 1) * 0.15) / steps.length;

      slide.addShape(pres.shapes.LINE, {
        x: 0.5 + stepW / 2, y: 1.8, w: 9 - stepW, h: 0,
        line: { color: accent, width: 2.5, dashType: "dash" }
      });

      steps.forEach(function(step, i) {
        var xPos = 0.5 + i * (stepW + 0.15);
        slide.addShape(pres.shapes.OVAL, { x: xPos + stepW / 2 - 0.25, y: 1.55, w: 0.5, h: 0.5, fill: { color: accent } });
        slide.addText("" + (i + 1), {
          x: xPos + stepW / 2 - 0.25, y: 1.55, w: 0.5, h: 0.5,
          fontSize: 16, fontFace: hFont, color: textLight, bold: true, align: "center", valign: "middle", margin: 0
        });
        slide.addShape(pres.shapes.RECTANGLE, { x: xPos, y: 2.25, w: stepW, h: 2.4, fill: { color: "FFFFFF" }, shadow: softShadow() });
        slide.addShape(pres.shapes.RECTANGLE, { x: xPos, y: 2.25, w: stepW, h: 0.04, fill: { color: accent } });
        slide.addText(step.phase || "", {
          x: xPos + 0.1, y: 2.4, w: stepW - 0.2, h: 0.35, fontSize: 12, fontFace: hFont, color: primary, bold: true, align: "center", margin: 0
        });
        slide.addText(step.description || "", {
          x: xPos + 0.1, y: 2.8, w: stepW - 0.2, h: 1.2, fontSize: 10, fontFace: bFont, color: textDark, align: "center", valign: "top", margin: 0
        });
        if (step.duration) {
          slide.addShape(pres.shapes.RECTANGLE, { x: xPos + 0.15, y: 4.15, w: stepW - 0.3, h: 0.3, fill: { color: accent, transparency: 85 } });
          slide.addText(step.duration, {
            x: xPos + 0.15, y: 4.15, w: stepW - 0.3, h: 0.3, fontSize: 9, fontFace: bFont, color: accent, align: "center", valign: "middle", bold: true, margin: 0
          });
        }
      });
      addFooter(slide, idx + 1, totalSlides);

    // ═══ ICON GRID ═══
    } else if (sType === "icon_grid") {
      slide.background = { color: light };
      addSideStripe(slide, accent);
      addDecoCircle(slide, 8, 3.5, 3, accent, 0.03);

      slide.addText(sd.title || "", {
        x: 0.6, y: 0.35, w: 8.8, h: 0.6, fontSize: 28, fontFace: hFont, color: textDark, bold: true, margin: 0
      });
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 0.95, w: 0.8, h: 0.04, fill: { color: accent } });

      var gitems = sd.items || [];
      var gcols = gitems.length <= 3 ? gitems.length : (gitems.length <= 4 ? 2 : 3);
      var grows = Math.ceil(gitems.length / gcols);
      var gcw = (9 - (gcols - 1) * 0.2) / gcols;
      var gch = grows === 1 ? 3.2 : (3.6 / grows);

      gitems.forEach(function(item, i) {
        var col = i % gcols;
        var row = Math.floor(i / gcols);
        var xPos = 0.5 + col * (gcw + 0.2);
        var yPos = 1.25 + row * (gch + 0.15);

        slide.addShape(pres.shapes.RECTANGLE, { x: xPos, y: yPos, w: gcw, h: gch, fill: { color: "FFFFFF" }, shadow: softShadow() });
        slide.addShape(pres.shapes.RECTANGLE, { x: xPos, y: yPos, w: 0.05, h: gch, fill: { color: accent } });
        slide.addShape(pres.shapes.OVAL, { x: xPos + 0.2, y: yPos + 0.2, w: 0.5, h: 0.5, fill: { color: accent, transparency: 85 } });
        slide.addText(item.icon || "", {
          x: xPos + 0.2, y: yPos + 0.2, w: 0.5, h: 0.5, fontSize: 18, align: "center", valign: "middle", margin: 0
        });
        slide.addText(item.heading || "", {
          x: xPos + 0.85, y: yPos + 0.2, w: gcw - 1.1, h: 0.35, fontSize: 13, fontFace: hFont, color: primary, bold: true, valign: "middle", margin: 0
        });
        slide.addText(item.description || "", {
          x: xPos + 0.85, y: yPos + 0.55, w: gcw - 1.1, h: gch - 0.8, fontSize: 10, fontFace: bFont, color: textDark, valign: "top", margin: 0
        });
      });
      addFooter(slide, idx + 1, totalSlides);

    // ═══ COMPARISON TABLE ═══
    } else if (sType === "comparison") {
      slide.background = { color: light };
      addSideStripe(slide, accent);

      slide.addText(sd.title || "", {
        x: 0.6, y: 0.35, w: 8.8, h: 0.6, fontSize: 28, fontFace: hFont, color: textDark, bold: true, margin: 0
      });
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 0.95, w: 0.8, h: 0.04, fill: { color: accent } });

      slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.25, w: 9, h: 0.45, fill: { color: dark } });
      slide.addText("Feature", { x: 0.7, y: 1.25, w: 3, h: 0.45, fontSize: 11, fontFace: hFont, color: textLight, bold: true, valign: "middle", margin: 0 });
      slide.addText(sd.left_label || "Before", { x: 3.7, y: 1.25, w: 2.8, h: 0.45, fontSize: 11, fontFace: hFont, color: accent, bold: true, align: "center", valign: "middle", margin: 0 });
      slide.addText(sd.right_label || "After", { x: 6.7, y: 1.25, w: 2.8, h: 0.45, fontSize: 11, fontFace: hFont, color: accent, bold: true, align: "center", valign: "middle", margin: 0 });

      var crows = sd.rows || [];
      crows.forEach(function(row, i) {
        var yPos = 1.7 + i * 0.48;
        var bg = i % 2 === 0 ? "FFFFFF" : "F3F4F6";
        slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: yPos, w: 9, h: 0.48, fill: { color: bg } });
        slide.addText(row.feature || "", { x: 0.7, y: yPos, w: 3, h: 0.48, fontSize: 11, fontFace: bFont, color: textDark, bold: true, valign: "middle", margin: 0 });
        slide.addText(row.left_value || "", { x: 3.7, y: yPos, w: 2.8, h: 0.48, fontSize: 11, fontFace: bFont, color: textMuted, align: "center", valign: "middle", margin: 0 });
        slide.addText(row.right_value || "", { x: 6.7, y: yPos, w: 2.8, h: 0.48, fontSize: 11, fontFace: bFont, color: primary, bold: true, align: "center", valign: "middle", margin: 0 });
      });
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.25, w: 9, h: 0.03, fill: { color: accent } });
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.7 + crows.length * 0.48, w: 9, h: 0.02, fill: { color: accent } });

      addFooter(slide, idx + 1, totalSlides);

    // ═══ QUOTE ═══
    } else if (sType === "quote") {
      slide.background = { color: dark };
      addCornerBrackets(slide, accent, 0.35);
      addDecoCircle(slide, 7, 0, 4, accent, 0.03);
      addDecoCircle(slide, -1, 3, 3, primary, 0.03);

      slide.addText("\u201C", {
        x: 0.5, y: 0.4, w: 1.5, h: 1.5, fontSize: 120, fontFace: "Georgia", color: accent, margin: 0
      });
      slide.addText(sd.quote || "", {
        x: 1.0, y: 1.5, w: 8, h: 2.2, fontSize: 22, fontFace: hFont, color: textLight, italic: true, margin: 0
      });
      slide.addShape(pres.shapes.RECTANGLE, { x: 1.0, y: 3.85, w: 1.5, h: 0.04, fill: { color: accent } });
      slide.addText(sd.attribution || "", {
        x: 1.0, y: 4.05, w: 8, h: 0.35, fontSize: 14, fontFace: hFont, color: accent, bold: true, margin: 0
      });
      slide.addText(sd.role || "", {
        x: 1.0, y: 4.4, w: 8, h: 0.3, fontSize: 12, fontFace: bFont, color: textMuted, margin: 0
      });
      addFooter(slide, idx + 1, totalSlides, dark);

    // ═══ METRIC BAR ═══
    } else if (sType === "metric_bar") {
      slide.background = { color: light };
      addSideStripe(slide, accent);

      slide.addText(sd.title || "", {
        x: 0.6, y: 0.35, w: 8.8, h: 0.6, fontSize: 28, fontFace: hFont, color: textDark, bold: true, margin: 0
      });
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 0.95, w: 0.8, h: 0.04, fill: { color: accent } });

      var bmetrics = sd.metrics || [];
      var barH = 0.35;
      var browH = Math.min(0.85, 3.5 / bmetrics.length);

      bmetrics.forEach(function(m, i) {
        var yPos = 1.3 + i * browH;
        var pct = Math.min(100, ((m.value || 0) / (m.max_value || 100)) * 100);
        var barW = 5.5 * (pct / 100);

        slide.addText(m.label || "", {
          x: 0.6, y: yPos, w: 3, h: 0.25, fontSize: 12, fontFace: hFont, color: textDark, bold: true, margin: 0
        });
        slide.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: yPos + 0.3, w: 5.5, h: barH, fill: { color: secondary } });
        if (barW > 0.1) {
          slide.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: yPos + 0.3, w: barW, h: barH, fill: { color: accent } });
        }
        slide.addText("" + (m.value || 0), {
          x: 6.3, y: yPos + 0.3, w: 0.8, h: barH, fontSize: 14, fontFace: hFont, color: accent, bold: true, valign: "middle", margin: 0
        });
        if (m.description) {
          slide.addText(m.description, {
            x: 7.2, y: yPos + 0.3, w: 2.3, h: barH, fontSize: 10, fontFace: bFont, color: textMuted, valign: "middle", margin: 0
          });
        }
      });
      addFooter(slide, idx + 1, totalSlides);

    // ═══ PROCESS FLOW ═══
    } else if (sType === "process_flow") {
      slide.background = { color: dark };
      addCornerBrackets(slide, accent, 0.35);
      addDotGrid(slide, 0.5, 4.3, 6, 3, accent);

      addSectionLabel(slide, sd.title || "Process", 0.6, 0.4, accent);
      slide.addText(sd.title || "Our Process", {
        x: 0.6, y: 0.7, w: 8.8, h: 0.6, fontSize: 28, fontFace: hFont, color: textLight, bold: true, margin: 0
      });

      var psteps = sd.steps || [];
      var pcols = Math.min(psteps.length, 4);
      var pcw = (9 - (pcols - 1) * 0.15) / pcols;

      psteps.forEach(function(step, i) {
        var xPos = 0.5 + i * (pcw + 0.15);
        slide.addShape(pres.shapes.RECTANGLE, { x: xPos, y: 1.6, w: pcw, h: 3.0, fill: { color: primary, transparency: 60 } });
        slide.addShape(pres.shapes.RECTANGLE, { x: xPos, y: 1.6, w: pcw, h: 0.05, fill: { color: accent } });
        slide.addShape(pres.shapes.OVAL, { x: xPos + pcw / 2 - 0.3, y: 1.85, w: 0.6, h: 0.6, fill: { color: accent } });
        slide.addText("" + (step.number || i + 1), {
          x: xPos + pcw / 2 - 0.3, y: 1.85, w: 0.6, h: 0.6,
          fontSize: 20, fontFace: hFont, color: textLight, bold: true, align: "center", valign: "middle", margin: 0
        });
        slide.addText(step.title || "", {
          x: xPos + 0.15, y: 2.6, w: pcw - 0.3, h: 0.4, fontSize: 13, fontFace: hFont, color: textLight, bold: true, align: "center", margin: 0
        });
        slide.addText(step.description || "", {
          x: xPos + 0.15, y: 3.05, w: pcw - 0.3, h: 1.3, fontSize: 10, fontFace: bFont, color: secondary, align: "center", valign: "top", margin: 0
        });
        if (i < psteps.length - 1) {
          slide.addText("\u2192", {
            x: xPos + pcw - 0.05, y: 2.8, w: 0.35, h: 0.4, fontSize: 20, color: accent, align: "center", valign: "middle", margin: 0
          });
        }
      });
      addFooter(slide, idx + 1, totalSlides, dark);

    // ═══ CHECKLIST ═══
    } else if (sType === "checklist") {
      slide.background = { color: light };
      addSideStripe(slide, accent);
      addDecoCircle(slide, 7.5, 3, 3.5, accent, 0.03);

      slide.addText(sd.title || "Deliverables", {
        x: 0.6, y: 0.35, w: 8.8, h: 0.6, fontSize: 28, fontFace: hFont, color: textDark, bold: true, margin: 0
      });
      if (sd.subtitle) {
        slide.addText(sd.subtitle, { x: 0.6, y: 0.95, w: 8.8, h: 0.3, fontSize: 13, fontFace: bFont, color: textMuted, margin: 0 });
      }
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: sd.subtitle ? 1.25 : 0.95, w: 0.8, h: 0.04, fill: { color: accent } });

      var citems = sd.items || [];
      var cstartY = sd.subtitle ? 1.5 : 1.2;
      var crowH = Math.min(0.52, 3.4 / citems.length);

      citems.forEach(function(item, i) {
        var yPos = cstartY + i * crowH;
        slide.addShape(pres.shapes.OVAL, { x: 0.6, y: yPos + 0.06, w: 0.3, h: 0.3, fill: { color: accent } });
        slide.addText("\u2713", {
          x: 0.6, y: yPos + 0.06, w: 0.3, h: 0.3,
          fontSize: 12, fontFace: bFont, color: textLight, bold: true, align: "center", valign: "middle", margin: 0
        });
        slide.addText(item, {
          x: 1.05, y: yPos, w: 8, h: 0.4, fontSize: 13, fontFace: bFont, color: textDark, valign: "middle", margin: 0
        });
        if (i < citems.length - 1) {
          slide.addShape(pres.shapes.RECTANGLE, { x: 1.05, y: yPos + crowH - 0.03, w: 7.5, h: 0.005, fill: { color: secondary } });
        }
      });
      addFooter(slide, idx + 1, totalSlides);

    // ═══ BIG STATEMENT ═══
    } else if (sType === "big_statement") {
      slide.background = { color: dark };
      addCornerBrackets(slide, accent, 0.5);
      addDecoCircle(slide, 6, -1, 5, accent, 0.03);
      addDecoCircle(slide, -2, 3, 4, primary, 0.03);
      addDotGrid(slide, 8, 4.2, 5, 4, accent);

      slide.addText(sd.statement || "", {
        x: 0.8, y: 1.2, w: 8.4, h: 2.5, fontSize: 32, fontFace: hFont, color: textLight, bold: true, margin: 0
      });
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 3.85, w: 2, h: 0.05, fill: { color: accent } });
      if (sd.supporting_text) {
        slide.addText(sd.supporting_text, {
          x: 0.8, y: 4.1, w: 8.4, h: 0.6, fontSize: 14, fontFace: bFont, color: textMuted, margin: 0
        });
      }
      addFooter(slide, idx + 1, totalSlides, dark);

    // ═══ PRICING ═══
    } else if (sType === "pricing") {
      slide.background = { color: light };
      addSideStripe(slide, accent);

      slide.addText(sd.title || "Investment", {
        x: 0.6, y: 0.35, w: 8.8, h: 0.6, fontSize: 28, fontFace: hFont, color: textDark, bold: true, margin: 0
      });
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 0.95, w: 0.8, h: 0.04, fill: { color: accent } });

      var tiers = sd.tiers || [];
      var tierW = tiers.length <= 3 ? (9 - (tiers.length - 1) * 0.25) / tiers.length : 2.1;

      tiers.forEach(function(tier, i) {
        var xPos = 0.5 + i * (tierW + 0.25);
        var isHL = tier.highlight;

        slide.addShape(pres.shapes.RECTANGLE, { x: xPos, y: 1.2, w: tierW, h: 3.5, fill: { color: isHL ? primary : "FFFFFF" }, shadow: cardShadow() });
        slide.addShape(pres.shapes.RECTANGLE, { x: xPos, y: 1.2, w: tierW, h: 0.06, fill: { color: accent } });

        if (isHL) {
          slide.addShape(pres.shapes.RECTANGLE, { x: xPos + 0.15, y: 1.35, w: tierW - 0.3, h: 0.22, fill: { color: accent } });
          slide.addText("RECOMMENDED", { x: xPos, y: 1.35, w: tierW, h: 0.22, fontSize: 8, fontFace: bFont, color: textLight, bold: true, align: "center", valign: "middle", margin: 0 });
        }
        slide.addText(tier.name || "", {
          x: xPos, y: isHL ? 1.65 : 1.35, w: tierW, h: 0.4, fontSize: 16, fontFace: hFont, color: isHL ? textLight : textDark, bold: true, align: "center", margin: 0
        });
        slide.addText(tier.price || "", {
          x: xPos, y: isHL ? 2.05 : 1.8, w: tierW, h: 0.55, fontSize: 28, fontFace: hFont, color: isHL ? accent : primary, bold: true, align: "center", margin: 0
        });
        var features = (tier.features || []).map(function(f, fi, a) {
          return { text: f, options: { bullet: { code: "25CF" }, fontSize: 10, fontFace: bFont, color: isHL ? secondary : textDark, breakLine: fi < a.length - 1, paraSpaceAfter: 4 } };
        });
        if (features.length) {
          slide.addText(features, { x: xPos + 0.2, y: isHL ? 2.65 : 2.4, w: tierW - 0.4, h: 2, valign: "top", margin: 0 });
        }
      });
      addFooter(slide, idx + 1, totalSlides);

    // ═══ TEAM ═══
    } else if (sType === "team") {
      slide.background = { color: light };
      addSideStripe(slide, accent);

      slide.addText(sd.title || "Our Team", {
        x: 0.6, y: 0.35, w: 8.8, h: 0.6, fontSize: 28, fontFace: hFont, color: textDark, bold: true, margin: 0
      });
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 0.95, w: 0.8, h: 0.04, fill: { color: accent } });

      var members = sd.members || [];
      var memW = (9 - (members.length - 1) * 0.2) / Math.min(members.length, 4);

      members.slice(0, 4).forEach(function(m, i) {
        var xPos = 0.5 + i * (memW + 0.2);
        slide.addShape(pres.shapes.RECTANGLE, { x: xPos, y: 1.25, w: memW, h: 3.3, fill: { color: "FFFFFF" }, shadow: softShadow() });
        slide.addShape(pres.shapes.RECTANGLE, { x: xPos, y: 1.25, w: memW, h: 0.04, fill: { color: accent } });
        slide.addShape(pres.shapes.OVAL, { x: xPos + memW / 2 - 0.4, y: 1.5, w: 0.8, h: 0.8, fill: { color: accent } });
        slide.addText((m.name || "")[0] || "?", {
          x: xPos + memW / 2 - 0.4, y: 1.5, w: 0.8, h: 0.8,
          fontSize: 24, fontFace: hFont, color: textLight, bold: true, align: "center", valign: "middle", margin: 0
        });
        slide.addText(m.name || "", { x: xPos, y: 2.45, w: memW, h: 0.35, fontSize: 14, fontFace: hFont, color: textDark, bold: true, align: "center", margin: 0 });
        slide.addText(m.role || "", { x: xPos, y: 2.75, w: memW, h: 0.25, fontSize: 11, fontFace: bFont, color: accent, align: "center", margin: 0 });
        slide.addText(m.bio || "", { x: xPos + 0.15, y: 3.1, w: memW - 0.3, h: 1.2, fontSize: 10, fontFace: bFont, color: textMuted, align: "center", valign: "top", margin: 0 });
      });
      addFooter(slide, idx + 1, totalSlides);

    // ═══ CLOSING ═══
    } else if (sType === "closing") {
      slide.background = { color: dark };
      addTopAccentBar(slide, accent);
      addBottomAccentBar(slide, accent);
      addCornerBrackets(slide, accent, 0.5);
      addDecoCircle(slide, 3.5, 1, 5, accent, 0.03);
      addDotGrid(slide, 0.5, 4.5, 5, 3, accent);
      addDotGrid(slide, 8.2, 0.5, 5, 3, accent);

      addLogo(slide, 4.1, 0.8, 1.8);
      slide.addText(sd.title || "Thank You", {
        x: 0.6, y: 2.1, w: 8.8, h: 1.0, fontSize: 40, fontFace: hFont, color: textLight, bold: true, align: "center", margin: 0
      });
      slide.addShape(pres.shapes.RECTANGLE, { x: 4.25, y: 3.15, w: 1.5, h: 0.04, fill: { color: accent } });
      slide.addText(sd.subtitle || "", {
        x: 0.6, y: 3.35, w: 8.8, h: 0.45, fontSize: 16, fontFace: bFont, color: secondary, align: "center", margin: 0
      });
      if (sd.contact) {
        slide.addText(sd.contact, {
          x: 0.6, y: 3.95, w: 8.8, h: 0.4, fontSize: 13, fontFace: bFont, color: textMuted, align: "center", margin: 0
        });
      }

    // ═══ DEFAULT CONTENT ═══
    } else {
      slide.background = { color: light };
      addSideStripe(slide, accent);

      slide.addText(sd.title || "", {
        x: 0.6, y: 0.35, w: 8.8, h: 0.6, fontSize: 28, fontFace: hFont, color: textDark, bold: true, margin: 0
      });
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 0.95, w: 0.8, h: 0.04, fill: { color: accent } });

      if (sd.subtitle) {
        slide.addText(sd.subtitle, { x: 0.6, y: 1.05, w: 8.8, h: 0.35, fontSize: 13, fontFace: bFont, color: textMuted, margin: 0 });
      }

      var cardY = sd.subtitle ? 1.55 : 1.2;
      var cardH = sd.subtitle ? 3.1 : 3.45;

      slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: cardY, w: 9, h: cardH, fill: { color: "FFFFFF" }, shadow: softShadow() });
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: cardY, w: 0.06, h: cardH, fill: { color: accent } });

      var bullets = (sd.bullets || []).map(function(b, i, a) {
        return { text: b, options: { bullet: { code: "25CF" }, fontSize: 13, fontFace: bFont, color: textDark, breakLine: i < a.length - 1, paraSpaceAfter: 8 } };
      });

      if (bullets.length) {
        slide.addText(bullets, { x: 0.85, y: cardY + 0.15, w: 8.4, h: cardH - 0.3, valign: "top", margin: 0 });
      } else if (sd.body) {
        slide.addText(sd.body, {
          x: 0.85, y: cardY + 0.15, w: 8.4, h: cardH - 0.3, fontSize: 14, fontFace: bFont, color: textDark, valign: "top", margin: 0
        });
      }

      addDecoCircle(slide, 7.5, 3.5, 3, accent, 0.03);
      addFooter(slide, idx + 1, totalSlides);
    }
  });

  await pres.writeFile({ fileName: outputPath });
  console.log("OK:" + outputPath);
}
