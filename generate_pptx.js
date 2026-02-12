/**
 * ProposalSnap PPTX Generator
 * Takes JSON input via stdin, generates a professional PPTX file
 */
const pptxgen = require("pptxgenjs");
const fs = require("fs");

// Read JSON from stdin
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

  // Font mapping
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

  // Helper: fresh shadow object each time
  const cardShadow = () => ({ type: "outer", blur: 6, offset: 2, angle: 135, color: "000000", opacity: 0.1 });

  // Helper: add logo to slide
  function addLogo(slide, x, y, w) {
    if (logoPath && fs.existsSync(logoPath)) {
      try {
        const logoData = fs.readFileSync(logoPath);
        const ext = logoPath.toLowerCase().endsWith(".png") ? "png" : "jpeg";
        const b64 = `image/${ext};base64,${logoData.toString("base64")}`;
        slide.addImage({ data: b64, x, y, w, h: w * 0.6, sizing: { type: "contain", w, h: w * 0.6 } });
      } catch (e) {}
    }
  }

  // Helper: add footer bar
  function addFooter(slide, companyName, pageNum, total) {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 5.1, w: 10, h: 0.525, fill: { color: dark }
    });
    slide.addText(companyName || "", {
      x: 0.5, y: 5.1, w: 4, h: 0.525, fontSize: 9,
      color: textMuted, fontFace: bFont, valign: "middle", margin: 0
    });
    slide.addText(`${pageNum} / ${total}`, {
      x: 8, y: 5.1, w: 1.5, h: 0.525, fontSize: 9,
      color: textMuted, fontFace: bFont, align: "right", valign: "middle", margin: 0
    });
  }

  const totalSlides = slides.length;

  slides.forEach((slideData, idx) => {
    const slide = pres.addSlide();
    const sType = slideData.layout || "content";

    if (sType === "title") {
      // ── TITLE SLIDE ──
      slide.background = { color: dark };
      
      // Top accent bar
      slide.addShape(pres.shapes.RECTANGLE, {
        x: 0, y: 0, w: 10, h: 0.06, fill: { color: accent }
      });

      addLogo(slide, 0.6, 0.5, 1.8);

      slide.addText(slideData.title || "", {
        x: 0.6, y: 1.6, w: 8.8, h: 1.4, fontSize: 40, fontFace: hFont,
        color: textLight, bold: true, margin: 0
      });

      slide.addText(slideData.subtitle || "", {
        x: 0.6, y: 3.0, w: 8.8, h: 0.6, fontSize: 18, fontFace: bFont,
        color: secondary, margin: 0
      });

      // Client + Date
      const dateStr = new Date().toLocaleDateString("en-US", { month: "long", year: "numeric" });
      slide.addText(`Prepared for ${clientName || "Client"} · ${dateStr}`, {
        x: 0.6, y: 3.8, w: 8.8, h: 0.5, fontSize: 12, fontFace: bFont,
        color: textMuted, margin: 0
      });

      // Bottom accent bar
      slide.addShape(pres.shapes.RECTANGLE, {
        x: 0, y: 5.565, w: 10, h: 0.06, fill: { color: accent }
      });

    } else if (sType === "agenda") {
      // ── AGENDA SLIDE ──
      slide.background = { color: light };
      
      slide.addText(slideData.title || "Agenda", {
        x: 0.6, y: 0.4, w: 8.8, h: 0.7, fontSize: 32, fontFace: hFont,
        color: textDark, bold: true, margin: 0
      });

      const items = slideData.bullets || [];
      items.forEach((item, i) => {
        const yPos = 1.4 + i * 0.65;
        // Number circle
        slide.addShape(pres.shapes.OVAL, {
          x: 0.6, y: yPos, w: 0.45, h: 0.45, fill: { color: accent }
        });
        slide.addText(`${i + 1}`, {
          x: 0.6, y: yPos, w: 0.45, h: 0.45, fontSize: 14, fontFace: bFont,
          color: textLight, bold: true, align: "center", valign: "middle", margin: 0
        });
        slide.addText(item, {
          x: 1.25, y: yPos, w: 8, h: 0.45, fontSize: 16, fontFace: bFont,
          color: textDark, valign: "middle", margin: 0
        });
      });

      addFooter(slide, companyName, idx + 1, totalSlides);

    } else if (sType === "two_column") {
      // ── TWO COLUMN LAYOUT ──
      slide.background = { color: light };

      slide.addText(slideData.title || "", {
        x: 0.6, y: 0.4, w: 8.8, h: 0.7, fontSize: 28, fontFace: hFont,
        color: textDark, bold: true, margin: 0
      });

      // Left column card
      slide.addShape(pres.shapes.RECTANGLE, {
        x: 0.5, y: 1.3, w: 4.3, h: 3.4, fill: { color: "FFFFFF" },
        shadow: cardShadow()
      });
      
      const leftBullets = (slideData.left_bullets || []).map((b, i, arr) => ({
        text: b, options: { bullet: true, fontSize: 13, fontFace: bFont, color: textDark,
          breakLine: i < arr.length - 1, paraSpaceAfter: 6 }
      }));
      if (leftBullets.length) {
        slide.addText(slideData.left_title || "", {
          x: 0.75, y: 1.45, w: 3.8, h: 0.45, fontSize: 16, fontFace: hFont,
          color: primary, bold: true, margin: 0
        });
        slide.addText(leftBullets, {
          x: 0.75, y: 1.95, w: 3.8, h: 2.5, valign: "top", margin: 0
        });
      }

      // Right column card
      slide.addShape(pres.shapes.RECTANGLE, {
        x: 5.2, y: 1.3, w: 4.3, h: 3.4, fill: { color: "FFFFFF" },
        shadow: cardShadow()
      });

      const rightBullets = (slideData.right_bullets || []).map((b, i, arr) => ({
        text: b, options: { bullet: true, fontSize: 13, fontFace: bFont, color: textDark,
          breakLine: i < arr.length - 1, paraSpaceAfter: 6 }
      }));
      if (rightBullets.length) {
        slide.addText(slideData.right_title || "", {
          x: 5.45, y: 1.45, w: 3.8, h: 0.45, fontSize: 16, fontFace: hFont,
          color: primary, bold: true, margin: 0
        });
        slide.addText(rightBullets, {
          x: 5.45, y: 1.95, w: 3.8, h: 2.5, valign: "top", margin: 0
        });
      }

      addFooter(slide, companyName, idx + 1, totalSlides);

    } else if (sType === "stats") {
      // ── STATS / KEY NUMBERS ──
      slide.background = { color: dark };

      slide.addText(slideData.title || "", {
        x: 0.6, y: 0.4, w: 8.8, h: 0.7, fontSize: 28, fontFace: hFont,
        color: textLight, bold: true, margin: 0
      });

      const stats = slideData.stats || [];
      const cols = Math.min(stats.length, 4);
      const cardW = (9 - (cols - 1) * 0.3) / cols;
      
      stats.forEach((stat, i) => {
        const xPos = 0.5 + i * (cardW + 0.3);
        slide.addShape(pres.shapes.RECTANGLE, {
          x: xPos, y: 1.5, w: cardW, h: 2.8,
          fill: { color: primary, transparency: 30 }
        });
        slide.addText(stat.value || "", {
          x: xPos, y: 1.7, w: cardW, h: 1.2, fontSize: 42, fontFace: hFont,
          color: accent, bold: true, align: "center", valign: "middle", margin: 0
        });
        slide.addText(stat.label || "", {
          x: xPos, y: 2.9, w: cardW, h: 0.5, fontSize: 14, fontFace: bFont,
          color: secondary, align: "center", valign: "top", margin: 0
        });
        if (stat.description) {
          slide.addText(stat.description, {
            x: xPos + 0.15, y: 3.4, w: cardW - 0.3, h: 0.7, fontSize: 11, fontFace: bFont,
            color: textMuted, align: "center", valign: "top", margin: 0
          });
        }
      });

      addFooter(slide, companyName, idx + 1, totalSlides);

    } else if (sType === "timeline") {
      // ── TIMELINE / PROCESS ──
      slide.background = { color: light };

      slide.addText(slideData.title || "", {
        x: 0.6, y: 0.4, w: 8.8, h: 0.7, fontSize: 28, fontFace: hFont,
        color: textDark, bold: true, margin: 0
      });

      const steps = slideData.steps || [];
      const stepW = (9 - (steps.length - 1) * 0.2) / steps.length;

      // Connecting line
      slide.addShape(pres.shapes.LINE, {
        x: 0.5 + stepW / 2, y: 2.0,
        w: 9 - stepW, h: 0,
        line: { color: secondary, width: 2 }
      });

      steps.forEach((step, i) => {
        const xPos = 0.5 + i * (stepW + 0.2);
        // Circle
        slide.addShape(pres.shapes.OVAL, {
          x: xPos + stepW / 2 - 0.22, y: 1.78, w: 0.44, h: 0.44, fill: { color: accent }
        });
        slide.addText(`${i + 1}`, {
          x: xPos + stepW / 2 - 0.22, y: 1.78, w: 0.44, h: 0.44,
          fontSize: 14, fontFace: bFont, color: textLight, bold: true,
          align: "center", valign: "middle", margin: 0
        });
        // Phase name
        slide.addText(step.phase || "", {
          x: xPos, y: 2.4, w: stepW, h: 0.4, fontSize: 13, fontFace: hFont,
          color: primary, bold: true, align: "center", margin: 0
        });
        // Description
        slide.addText(step.description || "", {
          x: xPos, y: 2.8, w: stepW, h: 1.2, fontSize: 11, fontFace: bFont,
          color: textDark, align: "center", valign: "top", margin: 0
        });
        // Duration
        if (step.duration) {
          slide.addText(step.duration, {
            x: xPos, y: 4.0, w: stepW, h: 0.35, fontSize: 10, fontFace: bFont,
            color: accent, align: "center", italic: true, margin: 0
          });
        }
      });

      addFooter(slide, companyName, idx + 1, totalSlides);

    } else if (sType === "pricing") {
      // ── PRICING / INVESTMENT ──
      slide.background = { color: light };

      slide.addText(slideData.title || "Investment", {
        x: 0.6, y: 0.4, w: 8.8, h: 0.7, fontSize: 28, fontFace: hFont,
        color: textDark, bold: true, margin: 0
      });

      const tiers = slideData.tiers || [];
      const tierW = tiers.length <= 3 ? (9 - (tiers.length - 1) * 0.3) / tiers.length : 2.1;

      tiers.forEach((tier, i) => {
        const xPos = 0.5 + i * (tierW + 0.3);
        const isHighlight = tier.highlight;
        
        slide.addShape(pres.shapes.RECTANGLE, {
          x: xPos, y: 1.2, w: tierW, h: 3.5,
          fill: { color: isHighlight ? primary : "FFFFFF" },
          shadow: cardShadow()
        });

        slide.addText(tier.name || "", {
          x: xPos, y: 1.35, w: tierW, h: 0.45, fontSize: 16, fontFace: hFont,
          color: isHighlight ? textLight : textDark, bold: true, align: "center", margin: 0
        });
        slide.addText(tier.price || "", {
          x: xPos, y: 1.85, w: tierW, h: 0.55, fontSize: 28, fontFace: hFont,
          color: isHighlight ? accent : primary, bold: true, align: "center", margin: 0
        });

        const features = (tier.features || []).map((f, fi, arr) => ({
          text: f, options: { bullet: true, fontSize: 11, fontFace: bFont,
            color: isHighlight ? secondary : textDark,
            breakLine: fi < arr.length - 1, paraSpaceAfter: 4 }
        }));
        if (features.length) {
          slide.addText(features, {
            x: xPos + 0.2, y: 2.5, w: tierW - 0.4, h: 2, valign: "top", margin: 0
          });
        }
      });

      addFooter(slide, companyName, idx + 1, totalSlides);

    } else if (sType === "team") {
      // ── TEAM SLIDE ──
      slide.background = { color: light };

      slide.addText(slideData.title || "Our Team", {
        x: 0.6, y: 0.4, w: 8.8, h: 0.7, fontSize: 28, fontFace: hFont,
        color: textDark, bold: true, margin: 0
      });

      const members = slideData.members || [];
      const memW = (9 - (members.length - 1) * 0.3) / Math.min(members.length, 4);

      members.slice(0, 4).forEach((m, i) => {
        const xPos = 0.5 + i * (memW + 0.3);
        
        slide.addShape(pres.shapes.RECTANGLE, {
          x: xPos, y: 1.3, w: memW, h: 3.2, fill: { color: "FFFFFF" },
          shadow: cardShadow()
        });
        // Avatar circle
        slide.addShape(pres.shapes.OVAL, {
          x: xPos + memW / 2 - 0.4, y: 1.5, w: 0.8, h: 0.8, fill: { color: accent }
        });
        slide.addText((m.name || "")[0] || "?", {
          x: xPos + memW / 2 - 0.4, y: 1.5, w: 0.8, h: 0.8,
          fontSize: 24, fontFace: hFont, color: textLight, bold: true,
          align: "center", valign: "middle", margin: 0
        });

        slide.addText(m.name || "", {
          x: xPos, y: 2.45, w: memW, h: 0.35, fontSize: 14, fontFace: hFont,
          color: textDark, bold: true, align: "center", margin: 0
        });
        slide.addText(m.role || "", {
          x: xPos, y: 2.8, w: memW, h: 0.3, fontSize: 11, fontFace: bFont,
          color: accent, align: "center", margin: 0
        });
        slide.addText(m.bio || "", {
          x: xPos + 0.15, y: 3.15, w: memW - 0.3, h: 1.1, fontSize: 10, fontFace: bFont,
          color: textMuted, align: "center", valign: "top", margin: 0
        });
      });

      addFooter(slide, companyName, idx + 1, totalSlides);

    } else if (sType === "closing") {
      // ── CLOSING / THANK YOU ──
      slide.background = { color: dark };

      slide.addShape(pres.shapes.RECTANGLE, {
        x: 0, y: 0, w: 10, h: 0.06, fill: { color: accent }
      });

      addLogo(slide, 4.1, 1.0, 1.8);

      slide.addText(slideData.title || "Thank You", {
        x: 0.6, y: 2.2, w: 8.8, h: 1.0, fontSize: 38, fontFace: hFont,
        color: textLight, bold: true, align: "center", margin: 0
      });

      slide.addText(slideData.subtitle || "", {
        x: 0.6, y: 3.2, w: 8.8, h: 0.5, fontSize: 16, fontFace: bFont,
        color: secondary, align: "center", margin: 0
      });

      if (slideData.contact) {
        slide.addText(slideData.contact, {
          x: 0.6, y: 3.9, w: 8.8, h: 0.5, fontSize: 13, fontFace: bFont,
          color: textMuted, align: "center", margin: 0
        });
      }

      slide.addShape(pres.shapes.RECTANGLE, {
        x: 0, y: 5.565, w: 10, h: 0.06, fill: { color: accent }
      });

    } else {
      // ── DEFAULT CONTENT SLIDE ──
      slide.background = { color: light };

      slide.addText(slideData.title || "", {
        x: 0.6, y: 0.4, w: 8.8, h: 0.7, fontSize: 28, fontFace: hFont,
        color: textDark, bold: true, margin: 0
      });

      if (slideData.subtitle) {
        slide.addText(slideData.subtitle, {
          x: 0.6, y: 1.1, w: 8.8, h: 0.4, fontSize: 14, fontFace: bFont,
          color: textMuted, margin: 0
        });
      }

      // Content card
      slide.addShape(pres.shapes.RECTANGLE, {
        x: 0.5, y: slideData.subtitle ? 1.65 : 1.3, w: 9, h: slideData.subtitle ? 3.0 : 3.35,
        fill: { color: "FFFFFF" }, shadow: cardShadow()
      });

      // Left accent bar on card
      slide.addShape(pres.shapes.RECTANGLE, {
        x: 0.5, y: slideData.subtitle ? 1.65 : 1.3, w: 0.06, h: slideData.subtitle ? 3.0 : 3.35,
        fill: { color: accent }
      });

      const bullets = (slideData.bullets || []).map((b, i, arr) => ({
        text: b, options: { bullet: true, fontSize: 14, fontFace: bFont, color: textDark,
          breakLine: i < arr.length - 1, paraSpaceAfter: 8 }
      }));
      
      if (bullets.length) {
        slide.addText(bullets, {
          x: 0.85, y: slideData.subtitle ? 1.8 : 1.45, w: 8.4,
          h: slideData.subtitle ? 2.7 : 3.05, valign: "top", margin: 0
        });
      } else if (slideData.body) {
        slide.addText(slideData.body, {
          x: 0.85, y: slideData.subtitle ? 1.8 : 1.45, w: 8.4,
          h: slideData.subtitle ? 2.7 : 3.05, fontSize: 14, fontFace: bFont,
          color: textDark, valign: "top", margin: 0
        });
      }

      addFooter(slide, companyName, idx + 1, totalSlides);
    }
  });

  await pres.writeFile({ fileName: outputPath });
  console.log("OK:" + outputPath);
}
