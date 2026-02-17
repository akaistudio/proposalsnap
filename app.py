"""
ProposalSnap - AI Presentation Maker
=====================================
Upload your logo, describe your proposal, get a professional PPTX in seconds.
"""

import os, json, uuid, subprocess, colorsys
from datetime import datetime
from pathlib import Path
from io import BytesIO

import anthropic
from PIL import Image
from flask import Flask, request, jsonify, send_file, render_template_string, redirect

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

UPLOAD_DIR = Path(__file__).parent / "uploads"
OUTPUT_DIR = Path(__file__).parent / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

MODEL = "claude-sonnet-4-5-20250929"
client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY', ''))

# ── Color Extraction ──────────────────────────────────────────
def extract_colors_from_logo(logo_path):
    """Extract dominant colors from logo and generate complementary palette"""
    try:
        img = Image.open(logo_path).convert("RGB")
        img = img.resize((100, 100))
        pixels = list(img.getdata())
        
        # Filter out near-white and near-black pixels
        filtered = [(r, g, b) for r, g, b in pixels 
                     if not (r > 240 and g > 240 and b > 240) 
                     and not (r < 15 and g < 15 and b < 15)]
        
        if not filtered:
            filtered = pixels
        
        # Simple dominant color: average of filtered pixels
        avg_r = int(sum(p[0] for p in filtered) / len(filtered))
        avg_g = int(sum(p[1] for p in filtered) / len(filtered))
        avg_b = int(sum(p[2] for p in filtered) / len(filtered))
        
        # Get most vivid pixel (highest saturation)
        best_sat = 0
        vivid = (avg_r, avg_g, avg_b)
        for r, g, b in filtered:
            h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
            if s > best_sat and v > 0.2:
                best_sat = s
                vivid = (r, g, b)
        
        primary_hex = f"{vivid[0]:02x}{vivid[1]:02x}{vivid[2]:02x}"
        
        # Generate complementary colors
        h, s, v = colorsys.rgb_to_hsv(vivid[0]/255, vivid[1]/255, vivid[2]/255)
        
        # Secondary: lighter version
        sr, sg, sb = colorsys.hsv_to_rgb(h, max(0.1, s * 0.3), min(1.0, v * 1.4 + 0.3))
        secondary_hex = f"{int(sr*255):02x}{int(sg*255):02x}{int(sb*255):02x}"
        
        # Accent: shifted hue, high saturation
        ah, as_, av = (h + 0.08) % 1.0, min(1.0, s * 1.2 + 0.1), min(1.0, v * 1.1 + 0.1)
        ar, ag, ab = colorsys.hsv_to_rgb(ah, as_, av)
        accent_hex = f"{int(ar*255):02x}{int(ag*255):02x}{int(ab*255):02x}"
        
        # Dark: very dark version of primary
        dr, dg, db = colorsys.hsv_to_rgb(h, min(0.6, s * 0.8), 0.12)
        dark_hex = f"{int(dr*255):02x}{int(dg*255):02x}{int(db*255):02x}"
        
        return {
            "primary": primary_hex,
            "secondary": secondary_hex,
            "accent": accent_hex,
            "dark": dark_hex,
            "light": "F8F9FA",
            "textDark": "1A1A2E",
            "textLight": "FFFFFF",
            "textMuted": "6B7280"
        }
    except Exception as e:
        print(f"Color extraction error: {e}")
        return default_colors()

def default_colors():
    return {
        "primary": "1E2761", "secondary": "CADCFC", "accent": "4A90D9",
        "dark": "0F1629", "light": "F8F9FA", "textDark": "1A1A2E",
        "textLight": "FFFFFF", "textMuted": "6B7280"
    }

# ── Claude API ────────────────────────────────────────────────
def generate_slide_content(client_name, company_name, pres_type, tone, key_points, num_slides=12):
    """Use Claude to generate structured slide content"""
    prompt = f"""Generate a professional {pres_type} presentation structure with STRONG visual variety.

Client: {client_name}
Presenting Company: {company_name}
Tone: {tone}
Number of Slides: {num_slides}

Key Points / Requirements:
{key_points}

Return ONLY a valid JSON array of slide objects. Each slide MUST have these fields:
- "layout": one of the layouts below
- "title": slide title
- Additional fields based on layout:

AVAILABLE LAYOUTS:

"title": Opening slide. Fields: subtitle (string)
"agenda": Overview of what's covered. Fields: bullets (array of 5-7 strings)
"content": Standard text slide. Fields: bullets (array of 3-5 strings) OR body (paragraph), optional subtitle
"two_column": Side-by-side comparison. Fields: left_title, left_bullets (array), right_title, right_bullets (array)
"stats": Big number metrics (2-4 cards). Fields: stats (array of {{value, label, description}})
"timeline": Process/timeline steps. Fields: steps (array of {{phase, description, duration}})
"pricing": Investment/tier cards. Fields: tiers (array of {{name, price, features[], highlight bool}})
"team": Team member cards. Fields: members (array of {{name, role, bio}})
"icon_grid": 4-6 feature/service cards with icons. Fields: items (array of {{icon, heading, description}}). icon should be a single emoji.
"comparison": Before vs After or comparison table. Fields: left_label, right_label, rows (array of {{feature, left_value, right_value}})
"quote": Testimonial or key statement. Fields: quote (string), attribution (string), role (string)
"metric_bar": Horizontal progress bars. Fields: metrics (array of {{label, value, max_value, description}}). value and max_value are numbers (e.g. value:85, max_value:100)
"process_flow": Numbered process with arrows. Fields: steps (array of {{number, title, description}})
"checklist": Visual checklist/deliverables. Fields: items (array of strings), subtitle (string)
"big_statement": One powerful sentence in large text. Fields: statement (string), supporting_text (string)
"closing": Thank you slide. Fields: subtitle, contact (string)

RULES:
1. First slide MUST be "title", second MUST be "agenda", last MUST be "closing"
2. CRITICAL: Use at LEAST 6 different layout types. Do NOT repeat the same layout more than twice.
3. ALWAYS include: at least one "stats", one "timeline" or "process_flow", and one of "icon_grid"/"comparison"/"metric_bar"
4. Prefer visual layouts (stats, icon_grid, comparison, metric_bar, process_flow, checklist, quote) over plain "content"
5. Use "content" for maximum 2 slides. Use visual layouts for the rest.
6. Stats should have realistic, specific numbers
7. Bullets should be concise (10-20 words each)
8. Make content specific to the client and key points
9. Return ONLY the JSON array, no other text

Generate exactly {num_slides} slides."""

    response = client.messages.create(
        model=MODEL, max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    return json.loads(text)

# ── PPTX Generation ───────────────────────────────────────────
def create_pptx(slides, colors, client_name, company_name, pres_type, tone, logo_path=None, font_style='aptos'):
    """Generate PPTX using Node.js pptxgenjs"""
    output_id = str(uuid.uuid4())[:8]
    output_path = str(OUTPUT_DIR / f"proposal_{output_id}.pptx")
    
    input_data = {
        "outputPath": output_path,
        "clientName": client_name,
        "companyName": company_name,
        "presentationType": pres_type,
        "tone": tone,
        "slides": slides,
        "colors": colors,
        "logoPath": str(logo_path) if logo_path else None,
        "fontStyle": font_style
    }
    
    script_path = Path(__file__).parent / "generate_pptx.js"
    
    # Find node binary
    import shutil
    node_bin = shutil.which("node")
    if not node_bin:
        # Try common paths
        for p in ["/usr/bin/node", "/usr/local/bin/node", "/nix/store/*/bin/node"]:
            import glob
            matches = glob.glob(p)
            if matches:
                node_bin = matches[0]
                break
    if not node_bin:
        node_bin = "node"
    
    result = subprocess.run(
        [node_bin, str(script_path)],
        input=json.dumps(input_data),
        capture_output=True, text=True, timeout=30
    )
    
    if result.returncode != 0:
        raise Exception(f"PPTX generation failed: {result.stderr}")
    
    return output_path

# ── API Routes ────────────────────────────────────────────────
@app.route('/api/generate', methods=['POST'])
def generate():
    try:
        client_name = request.form.get('client_name', '').strip()
        company_name = request.form.get('company_name', '').strip()
        pres_type = request.form.get('presentation_type', 'Corporate Proposal')
        tone = request.form.get('tone', 'Corporate')
        font_style = request.form.get('font_style', 'aptos')
        key_points = request.form.get('key_points', '').strip()
        num_slides = int(request.form.get('num_slides', 12))
        num_slides = max(6, min(16, num_slides))
        
        if not client_name: return jsonify({"error": "Client name is required"}), 400
        if not key_points: return jsonify({"error": "Key points are required"}), 400
        
        # Handle logo
        logo_path = None
        colors = default_colors()
        if 'logo' in request.files and request.files['logo'].filename:
            logo_file = request.files['logo']
            logo_ext = Path(logo_file.filename).suffix.lower()
            if logo_ext in ('.png', '.jpg', '.jpeg', '.svg', '.webp'):
                logo_id = str(uuid.uuid4())[:8]
                logo_path = UPLOAD_DIR / f"logo_{logo_id}{logo_ext}"
                logo_file.save(str(logo_path))
                if logo_ext != '.svg':
                    colors = extract_colors_from_logo(str(logo_path))
        
        # Generate content with Claude
        slides = generate_slide_content(client_name, company_name, pres_type, tone, key_points, num_slides)
        
        # Generate PPTX
        output_path = create_pptx(slides, colors, client_name, company_name, pres_type, tone, logo_path, font_style)
        
        filename = f"{client_name.replace(' ', '_')}_{pres_type.replace(' ', '_')}.pptx"
        return jsonify({
            "success": True,
            "download_url": f"/api/download/{Path(output_path).name}",
            "filename": filename,
            "slides_count": len(slides),
            "colors": colors
        })
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to generate slide content. Please try again."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/download/<filename>')
def download(filename):
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        return jsonify({"error": "File not found"}), 404
    return send_file(str(filepath), as_attachment=True,
                     download_name=request.args.get('name', filename))

@app.route('/api/preview-colors', methods=['POST'])
def preview_colors():
    """Preview colors from uploaded logo"""
    if 'logo' not in request.files:
        return jsonify(default_colors())
    logo_file = request.files['logo']
    if not logo_file.filename:
        return jsonify(default_colors())
    
    temp_path = UPLOAD_DIR / f"temp_{uuid.uuid4().hex[:8]}{Path(logo_file.filename).suffix}"
    logo_file.save(str(temp_path))
    colors = extract_colors_from_logo(str(temp_path))
    try: os.unlink(str(temp_path))
    except: pass
    return jsonify(colors)

# ── Main Page ─────────────────────────────────────────────────
MAIN_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ProposalSnap — AI Presentation Maker</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--bg:#0B0F1A;--surface:#131829;--border:rgba(255,255,255,0.08);--text:#F0F0F5;
--text2:#8B8FA3;--accent:#6C5CE7;--accent2:#A78BFA;--green:#00D2A0;--red:#FF6B6B;
--radius:14px;--font:'Inter',sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--font);background:var(--bg);color:var(--text);min-height:100vh}
.container{max-width:900px;margin:0 auto;padding:24px 16px}
h1{font-size:32px;font-weight:700;background:linear-gradient(135deg,#6C5CE7,#00D2A0);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:4px}
.subtitle{color:var(--text2);font-size:15px;margin-bottom:32px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:24px;margin-bottom:16px}
.card h3{font-size:16px;font-weight:600;margin-bottom:16px;color:var(--accent2)}
label{display:block;font-size:13px;color:var(--text2);margin-bottom:6px;font-weight:500}
input[type="text"],textarea,select{width:100%;padding:12px 16px;background:var(--bg);
border:1px solid var(--border);border-radius:10px;color:var(--text);font-family:var(--font);
font-size:14px;outline:none;transition:border-color 0.2s}
input:focus,textarea:focus,select:focus{border-color:var(--accent)}
textarea{resize:vertical;min-height:120px;line-height:1.6}
select{cursor:pointer;appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath d='M6 8L1 3h10z' fill='%238B8FA3'/%3E%3C/svg%3E");
background-repeat:no-repeat;background-position:right 12px center}
.row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:600px){.row{grid-template-columns:1fr}}
.row3{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:16px}
@media(max-width:600px){.row3{grid-template-columns:1fr 1fr}}
.btn{padding:14px 28px;border-radius:10px;font-family:var(--font);font-size:15px;font-weight:600;
cursor:pointer;border:none;transition:all 0.2s}
.btn-primary{background:linear-gradient(135deg,#6C5CE7,#5A4BD1);color:white;width:100%}
.btn-primary:hover{transform:translateY(-1px);box-shadow:0 4px 15px rgba(108,92,231,0.4)}
.btn-primary:disabled{opacity:0.5;transform:none;cursor:not-allowed}
.file-upload{border:2px dashed var(--border);border-radius:10px;padding:24px;text-align:center;
cursor:pointer;transition:all 0.2s}
.file-upload:hover{border-color:var(--accent);background:rgba(108,92,231,0.05)}
.file-upload.has-file{border-color:var(--green);background:rgba(0,210,160,0.05)}
.file-upload input{display:none}
.color-preview{display:flex;gap:8px;margin-top:12px;align-items:center}
.color-dot{width:32px;height:32px;border-radius:8px;border:2px solid var(--border)}
.color-label{font-size:11px;color:var(--text2);text-align:center;margin-top:2px}
.status{padding:16px;border-radius:10px;margin-top:16px;display:none}
.status.loading{display:block;background:rgba(108,92,231,0.1);color:var(--accent2)}
.status.success{display:block;background:rgba(0,210,160,0.1);color:var(--green)}
.status.error{display:block;background:rgba(255,107,107,0.1);color:var(--red)}
.download-btn{display:inline-flex;align-items:center;gap:8px;padding:12px 24px;
background:var(--green);color:var(--bg);border-radius:10px;text-decoration:none;
font-weight:600;font-size:14px;margin-top:12px;transition:all 0.2s}
.download-btn:hover{transform:translateY(-1px);box-shadow:0 4px 15px rgba(0,210,160,0.3)}
.spinner{display:inline-block;width:16px;height:16px;border:2px solid rgba(255,255,255,0.3);
border-top-color:var(--accent2);border-radius:50%;animation:spin 0.8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.examples{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}
.example-tag{font-size:11px;padding:4px 10px;background:rgba(108,92,231,0.1);color:var(--accent2);
border-radius:20px;cursor:pointer;border:1px solid transparent;transition:all 0.2s}
.example-tag:hover{border-color:var(--accent);background:rgba(108,92,231,0.2)}
.footer{text-align:center;padding:32px 0;color:var(--text2);font-size:13px}
.counter{text-align:right;font-size:12px;color:var(--text2);margin-top:4px}
</style>
</head>
<body>
<div class="container">
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
<a href="/" style="text-decoration:none;color:inherit"><h1>ProposalSnap</h1></a>
<a href="https://snapsuite.up.railway.app" target="_blank" style="font-size:12px;color:#8B95B0;text-decoration:none;padding:6px 12px;border:1px solid #2A3148;border-radius:6px;font-weight:600;font-family:'DM Sans',sans-serif">← SnapSuite</a>
<div style="position:relative;display:inline-block"><button onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='block'?'none':'block'" style="font-size:14px;background:none;border:1px solid #2A3148;border-radius:6px;padding:5px 10px;color:#8B95B0;cursor:pointer;font-family:'DM Sans',sans-serif" title="Switch App">⊞</button><div style="display:none;position:absolute;right:0;top:32px;background:#141926;border:1px solid #2A3148;border-radius:10px;padding:8px;min-width:180px;z-index:200;box-shadow:0 8px 30px rgba(0,0,0,.5)"><a href="https://invoicesnap.up.railway.app" style="display:block;padding:8px 12px;color:#E8ECF4;text-decoration:none;border-radius:6px;font-size:13px;font-weight:500;font-family:'DM Sans',sans-serif" onmouseover="this.style.background='#2A3148'" onmouseout="this.style.background='none'">📄 InvoiceSnap</a><a href="https://contractsnap-app.up.railway.app" style="display:block;padding:8px 12px;color:#E8ECF4;text-decoration:none;border-radius:6px;font-size:13px;font-weight:500;font-family:'DM Sans',sans-serif" onmouseover="this.style.background='#2A3148'" onmouseout="this.style.background='none'">📋 ContractSnap</a><a href="https://expensesnap.up.railway.app" style="display:block;padding:8px 12px;color:#E8ECF4;text-decoration:none;border-radius:6px;font-size:13px;font-weight:500;font-family:'DM Sans',sans-serif" onmouseover="this.style.background='#2A3148'" onmouseout="this.style.background='none'">📸 ExpenseSnap</a><a href="https://payslipsnap.up.railway.app" style="display:block;padding:8px 12px;color:#E8ECF4;text-decoration:none;border-radius:6px;font-size:13px;font-weight:500;font-family:'DM Sans',sans-serif" onmouseover="this.style.background='#2A3148'" onmouseout="this.style.background='none'">💰 PayslipSnap</a></div></div>
</div>
<p class="subtitle">AI-powered professional presentations in seconds</p>

<div class="card">
<h3>📋 Presentation Details</h3>
<div class="row" style="margin-bottom:16px">
<div><label>Client Name *</label>
<input type="text" id="clientName" placeholder="e.g. Zurich Insurance"></div>
<div><label>Your Company Name</label>
<input type="text" id="companyName" placeholder="e.g. Shakty.AI"></div>
</div>
<div class="row3" style="margin-bottom:16px">
<div><label>Presentation Type</label>
<select id="presType">
<option>Corporate Proposal</option>
<option>Sales Pitch Deck</option>
<option>Training Deck</option>
<option>Project Report</option>
<option>Business Plan</option>
<option>Consulting Engagement</option>
</select></div>
<div><label>Tone</label>
<select id="tone">
<option>Corporate</option>
<option>Creative</option>
<option>Minimal</option>
<option>Bold</option>
<option>Friendly</option>
</select></div>
<div><label>Font Style</label>
<select id="fontStyle">
<option value="aptos">Aptos · Clean Modern</option>
<option value="georgia">Georgia + Calibri · Classic</option>
<option value="arial">Arial Black + Arial · Bold</option>
<option value="trebuchet">Trebuchet + Calibri · Creative</option>
<option value="palatino">Palatino + Garamond · Elegant</option>
<option value="cambria">Cambria + Calibri · Traditional</option>
</select></div>
<div><label>Number of Slides</label>
<select id="numSlides">
<option>8</option>
<option>10</option>
<option selected>12</option>
<option>14</option>
<option>16</option>
</select></div>
</div>
</div>

<div class="card">
<h3>🎨 Logo & Branding</h3>
<p style="color:var(--text2);font-size:13px;margin-bottom:12px">Upload your logo — we'll extract colors to style the entire presentation.</p>
<div class="file-upload" id="logoDropzone" onclick="document.getElementById('logoInput').click()">
<input type="file" id="logoInput" accept=".png,.jpg,.jpeg,.webp,.svg" onchange="handleLogo(this)">
<div id="logoText">📎 Click to upload logo (PNG, JPG, SVG)</div>
</div>
<div class="color-preview" id="colorPreview" style="display:none;">
<div><div class="color-dot" id="cprimary"></div><div class="color-label">Primary</div></div>
<div><div class="color-dot" id="csecondary"></div><div class="color-label">Secondary</div></div>
<div><div class="color-dot" id="caccent"></div><div class="color-label">Accent</div></div>
<div><div class="color-dot" id="cdark"></div><div class="color-label">Dark</div></div>
<div style="flex:1;font-size:12px;color:var(--text2);padding-left:8px">Colors extracted from your logo</div>
</div>
</div>

<div class="card">
<h3>💡 Key Points & Content *</h3>
<p style="color:var(--text2);font-size:13px;margin-bottom:12px">Describe what the presentation should cover. The more detail, the better the output.</p>
<textarea id="keyPoints" placeholder="Example:
- We offer AI-powered expense management for small businesses
- Key differentiator: Receipt scanning with 99% accuracy using Claude AI  
- Target market: Consulting firms with 5-50 employees
- Pricing: $29-99/month depending on team size
- Timeline: 2-week implementation, full training included
- ROI: Save 10 hours/month on expense reporting
- Request: Pilot program starting March 2025"></textarea>
<div class="counter"><span id="charCount">0</span> characters</div>
<div class="examples">
<span class="example-tag" onclick="fillExample('proposal')">💼 Proposal</span>
<span class="example-tag" onclick="fillExample('pitch')">🚀 Pitch Deck</span>
<span class="example-tag" onclick="fillExample('training')">📚 Training</span>
<span class="example-tag" onclick="fillExample('report')">📊 Report</span>
</div>
</div>

<button class="btn btn-primary" id="generateBtn" onclick="generate()">
⚡ Generate Presentation
</button>

<div class="status" id="status"></div>

<div class="footer">
ProposalSnap · Built with Claude AI · Powered by Shakty.AI
</div>
</div>

<script>
const keyPointsEl = document.getElementById('keyPoints');
keyPointsEl.addEventListener('input', () => {
  document.getElementById('charCount').textContent = keyPointsEl.value.length;
});

async function handleLogo(input) {
  if (!input.files.length) return;
  const file = input.files[0];
  document.getElementById('logoText').textContent = `✓ ${file.name}`;
  document.getElementById('logoDropzone').classList.add('has-file');
  
  // Preview colors
  const formData = new FormData();
  formData.append('logo', file);
  try {
    const res = await fetch('/api/preview-colors', { method: 'POST', body: formData });
    const colors = await res.json();
    document.getElementById('cprimary').style.background = '#' + colors.primary;
    document.getElementById('csecondary').style.background = '#' + colors.secondary;
    document.getElementById('caccent').style.background = '#' + colors.accent;
    document.getElementById('cdark').style.background = '#' + colors.dark;
    document.getElementById('colorPreview').style.display = 'flex';
  } catch(e) { console.error(e); }
}

function fillExample(type) {
  const examples = {
    proposal: `Client wants an AI-powered expense management solution
- Receipt scanning with 99% accuracy using Claude AI
- Multi-company support with role-based access
- Real-time currency conversion (3-way: bill, home, USD)
- Key differentiator: works on phone camera, no app install needed
- Target: consulting firms with 5-50 employees
- Pricing: Starter $29/mo, Business $49/mo, Pro $99/mo
- Implementation: 2-week setup, full team training included
- ROI: Save 10+ hours/month on expense reporting per employee
- Security: HTTPS, data isolation, PostgreSQL with daily backups`,
    pitch: `We are building the next generation of AI productivity tools
- Problem: Small businesses waste 20+ hours/month on admin tasks
- Solution: AI agents that automate receipts, invoices, and reporting
- Market size: $50B global expense management market
- Traction: 3 paying clients, $500 MRR in first month
- Technology: Claude AI for extraction, Railway for hosting
- Team: 2 founders with 30+ years combined experience
- Ask: $200K seed round for 12 months runway
- Use of funds: Product development 60%, Sales 25%, Infrastructure 15%`,
    training: `AI Training Program for Finance Team
- Module 1: Introduction to AI in Finance (Copilot, Claude, ChatGPT)
- Module 2: Prompt Engineering for Financial Analysis
- Module 3: Building AI Agents with Copilot Studio
- Module 4: Automating Expense Reporting and Invoice Processing
- Module 5: AI-Powered Financial Dashboards
- Duration: 6 weeks, 2 sessions per week
- Target audience: Finance managers and analysts
- Expected outcomes: 40% reduction in manual tasks
- Certification provided upon completion`,
    report: `Q4 2024 Financial Performance Summary
- Revenue: $2.4M (up 18% YoY)
- New clients: 12 enterprise accounts acquired
- Customer retention: 94% (industry avg: 85%)
- Key wins: Zurich Insurance, ABB Robotics contracts
- Challenges: Exchange rate fluctuations, supply chain delays
- Cost optimization: Reduced operational costs by 15%
- Headcount: Grew team from 45 to 58 employees
- Q1 2025 outlook: Pipeline of $1.8M, targeting 22% growth
- Strategic priorities: AI implementation, GDPR compliance, market expansion`
  };
  keyPointsEl.value = examples[type] || '';
  document.getElementById('charCount').textContent = keyPointsEl.value.length;
}

async function generate() {
  const clientName = document.getElementById('clientName').value.trim();
  const companyName = document.getElementById('companyName').value.trim();
  const presType = document.getElementById('presType').value;
  const tone = document.getElementById('tone').value;
  const fontStyle = document.getElementById('fontStyle').value;
  const keyPoints = document.getElementById('keyPoints').value.trim();
  const numSlides = document.getElementById('numSlides').value;
  
  if (!clientName) { showStatus('Please enter a client name', 'error'); return; }
  if (!keyPoints) { showStatus('Please enter key points for the presentation', 'error'); return; }
  
  const btn = document.getElementById('generateBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Generating presentation...';
  showStatus('🤖 AI is creating your slide content... This takes 15-30 seconds.', 'loading');
  
  const formData = new FormData();
  formData.append('client_name', clientName);
  formData.append('company_name', companyName);
  formData.append('presentation_type', presType);
  formData.append('tone', tone);
  formData.append('font_style', fontStyle);
  formData.append('key_points', keyPoints);
  formData.append('num_slides', numSlides);
  
  const logoInput = document.getElementById('logoInput');
  if (logoInput.files.length) {
    formData.append('logo', logoInput.files[0]);
  }
  
  try {
    const res = await fetch('/api/generate', { method: 'POST', body: formData });
    const data = await res.json();
    
    if (data.success) {
      const downloadUrl = data.download_url + '?name=' + encodeURIComponent(data.filename);
      showStatus(`
        <div>✅ Presentation generated! ${data.slides_count} slides created.</div>
        <a href="${downloadUrl}" class="download-btn">📥 Download ${data.filename}</a>
      `, 'success');
    } else {
      showStatus('❌ ' + (data.error || 'Failed to generate'), 'error');
    }
  } catch(e) {
    showStatus('❌ Connection error: ' + e.message, 'error');
  }
  
  btn.disabled = false;
  btn.innerHTML = '⚡ Generate Presentation';
}

function showStatus(msg, type) {
  const el = document.getElementById('status');
  el.innerHTML = msg;
  el.className = 'status ' + type;
}
</script>
</body></html>"""

@app.route('/')
def index():
    return render_template_string(MAIN_HTML)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n{'='*50}")
    print(f"  🎯 ProposalSnap is running!")
    print(f"{'='*50}")
    print(f"  Open: http://localhost:{port}")
    print(f"{'='*50}\n")
    app.run(host='0.0.0.0', port=port, debug=True)

@app.route('/demo')
def demo():
    hub_url = os.environ.get('HUB_URL', 'https://snapsuite.up.railway.app')
    return render_template_string(DEMO_GALLERY_HTML, hub_url=hub_url)

DEMO_GALLERY_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ProposalSnap — Demo Gallery</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800;900&family=Playfair+Display:wght@600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#06080F;--surface:#0D1117;--card:#131920;--border:#1C2433;--border2:#2A3548;--text:#E2E8F0;--text2:#6B7A90;
--blue:#3B82F6;--green:#4ADE80;--red:#F87171;--orange:#F59E0B;--purple:#A78BFA;--teal:#2DD4BF;--pink:#F472B6;--cyan:#22D3EE;--indigo:#818CF8}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse at 20% 0%,rgba(59,130,246,.06) 0%,transparent 60%),radial-gradient(ellipse at 80% 100%,rgba(167,139,250,.05) 0%,transparent 50%);pointer-events:none;z-index:0}

/* Topbar */
.topbar{position:sticky;top:0;z-index:100;background:rgba(6,8,15,.85);backdrop-filter:blur(24px);border-bottom:1px solid var(--border);padding:14px 32px;display:flex;align-items:center;justify-content:space-between}
.topbar h1{font-size:22px;font-weight:900;color:#fff;letter-spacing:-.5px}
.topbar h1 span{background:linear-gradient(135deg,var(--blue),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.topbar-right{display:flex;gap:8px}
.topbar-right a{font-size:13px;color:var(--text2);text-decoration:none;padding:8px 16px;border-radius:8px;font-weight:600;transition:.2s}
.topbar-right a:hover{color:#fff;background:rgba(255,255,255,.06)}
.topbar-right .cta{background:linear-gradient(135deg,var(--blue),var(--purple));color:#fff;font-weight:700}

/* Hero */
.hero-section{padding:48px 32px 16px;max-width:1200px;margin:0 auto;position:relative;z-index:1}
.hero-section h2{font-size:36px;font-weight:900;color:#fff;letter-spacing:-1.5px;margin-bottom:8px}
.hero-section .sub{font-size:16px;color:var(--text2);line-height:1.6;max-width:600px}
.hero-section .badge{display:inline-flex;align-items:center;gap:6px;padding:6px 14px;background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.15);border-radius:50px;font-size:12px;font-weight:700;color:var(--blue);margin-bottom:16px}
.hero-section .badge .dot{width:6px;height:6px;border-radius:50%;background:var(--green);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}

/* Main */
.main{max-width:1200px;margin:0 auto;padding:32px;position:relative;z-index:1}

/* Proposal section */
.proposal{margin-bottom:48px;position:relative}
.proposal-label{font-family:'JetBrains Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:2px;font-weight:600;margin-bottom:12px}

/* Proposal header card */
.proposal-head{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:28px 32px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;position:relative;overflow:hidden}
.proposal-head::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
.proposal-head.theme-corporate::before{background:linear-gradient(90deg,#e94560,#c62a88,#0f3460)}
.proposal-head.theme-wedding::before{background:linear-gradient(90deg,#f5c6a5,#c62a88,#801336)}
.proposal-head.theme-workshop::before{background:linear-gradient(90deg,#64ffda,#3B82F6,#0a192f)}
.ph-left h3{font-size:22px;font-weight:800;color:#fff;letter-spacing:-.5px;margin-bottom:6px}
.ph-left .ph-meta{font-size:13px;color:var(--text2);display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.ph-left .ph-meta .sep{color:var(--border2)}
.ph-right{text-align:right}
.ph-right .price{font-size:28px;font-weight:900;color:#fff;letter-spacing:-1px;margin-bottom:4px}
.status{display:inline-flex;align-items:center;gap:4px;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:.3px}
.status.sent{background:rgba(59,130,246,.12);color:var(--blue);border:1px solid rgba(59,130,246,.2)}
.status.accepted{background:rgba(74,222,128,.1);color:var(--green);border:1px solid rgba(74,222,128,.2)}
.status.draft{background:rgba(107,122,144,.1);color:var(--text2);border:1px solid rgba(107,122,144,.15)}
.status::before{content:'';width:6px;height:6px;border-radius:50%;background:currentColor}

/* Slides scroll */
.slides-wrapper{position:relative}
.slides-scroll{display:flex;gap:14px;overflow-x:auto;padding:8px 4px 20px;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;scrollbar-width:none}
.slides-scroll::-webkit-scrollbar{display:none}
.slides-scroll::after{content:'';min-width:20px;flex-shrink:0}

/* Individual slide */
.slide{min-width:300px;max-width:300px;aspect-ratio:16/9;border-radius:12px;flex-shrink:0;scroll-snap-align:start;position:relative;overflow:hidden;cursor:default;transition:transform .3s,box-shadow .3s;border:1px solid rgba(255,255,255,.06)}
.slide:hover{transform:translateY(-4px) scale(1.02);box-shadow:0 16px 48px rgba(0,0,0,.5)}
.slide-inner{position:absolute;inset:0;padding:22px 24px;display:flex;flex-direction:column;z-index:2}
.slide-num{position:absolute;top:10px;right:12px;font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:600;opacity:.35;z-index:3}

/* Slide decorative elements */
.slide-deco{position:absolute;inset:0;z-index:1;overflow:hidden;pointer-events:none}
.slide-deco .circle{position:absolute;border-radius:50%;opacity:.08}
.slide-deco .line{position:absolute;height:1px;opacity:.1}
.slide-deco .corner{position:absolute;width:40px;height:40px;opacity:.12}
.slide-deco .corner::before,.slide-deco .corner::after{content:'';position:absolute;background:currentColor}
.slide-deco .corner.tl{top:12px;left:12px}.slide-deco .corner.tl::before{top:0;left:0;width:16px;height:1.5px}.slide-deco .corner.tl::after{top:0;left:0;width:1.5px;height:16px}
.slide-deco .corner.br{bottom:12px;right:12px}.slide-deco .corner.br::before{bottom:0;right:0;width:16px;height:1.5px}.slide-deco .corner.br::after{bottom:0;right:0;width:1.5px;height:16px}
.slide-deco .dots{position:absolute;display:grid;grid-template-columns:repeat(5,4px);gap:8px;opacity:.08}
.slide-deco .dots span{width:4px;height:4px;border-radius:50%;background:currentColor}

/* Slide title styles */
.slide h4{font-family:'Playfair Display',serif;font-weight:800;line-height:1.2;margin-bottom:8px;position:relative}
.slide .slide-label{font-family:'JetBrains Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:2px;opacity:.5;margin-bottom:auto}
.slide p{font-size:11px;line-height:1.65;opacity:.8}
.slide .tag{font-family:'JetBrains Mono',monospace;font-size:8px;padding:3px 8px;border-radius:4px;letter-spacing:1.5px;text-transform:uppercase;margin-top:auto;display:inline-block;width:fit-content}
.slide .divider{width:32px;height:2px;margin:8px 0;border-radius:1px}
.slide .icon-row{display:flex;gap:6px;margin-top:8px}
.slide .icon-row span{width:24px;height:24px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:11px;background:rgba(255,255,255,.1)}

/* Theme: Corporate Navy (Brand Identity) */
.theme-corp{background:linear-gradient(145deg,#0a1628,#162240)}
.theme-corp-alt{background:linear-gradient(145deg,#162240,#0f3460)}
.theme-corp-accent{background:linear-gradient(145deg,#0f3460,#1a1a40)}
.theme-corp-dark{background:linear-gradient(145deg,#0a0f1f,#0a1628)}
.theme-corp h4{color:#e94560;font-size:16px}
.theme-corp p,.theme-corp-alt p,.theme-corp-accent p,.theme-corp-dark p{color:#b8c5d6}
.theme-corp .tag{background:rgba(233,69,96,.15);color:#e94560;border:1px solid rgba(233,69,96,.2)}
.theme-corp .divider,.theme-corp-alt .divider,.theme-corp-accent .divider{background:#e94560}
.theme-corp-alt h4,.theme-corp-accent h4,.theme-corp-dark h4{color:#e94560;font-size:16px}
.theme-corp .slide-deco .circle,.theme-corp-alt .slide-deco .circle{background:#e94560}
.theme-corp .slide-deco .line,.theme-corp-alt .slide-deco .line{background:#e94560}
.theme-corp .slide-deco .corner,.theme-corp-alt .slide-deco .corner,.theme-corp-accent .slide-deco .corner{color:#e94560}
.theme-corp .slide-deco .dots span,.theme-corp-alt .slide-deco .dots span{background:#e94560}

/* Theme: Wedding (Burgundy/Gold) */
.theme-wed{background:linear-gradient(145deg,#1f0a1a,#3d1132)}
.theme-wed-alt{background:linear-gradient(145deg,#3d1132,#5c1a4a)}
.theme-wed-accent{background:linear-gradient(145deg,#2a0e24,#1f0a1a)}
.theme-wed h4,.theme-wed-alt h4,.theme-wed-accent h4{color:#f5c6a5;font-size:16px}
.theme-wed p,.theme-wed-alt p,.theme-wed-accent p{color:#d4a9b8}
.theme-wed .tag{background:rgba(245,198,165,.1);color:#f5c6a5;border:1px solid rgba(245,198,165,.2)}
.theme-wed .divider,.theme-wed-alt .divider{background:linear-gradient(90deg,#f5c6a5,#c62a88)}
.theme-wed .slide-deco .circle,.theme-wed-alt .slide-deco .circle{background:#c62a88}
.theme-wed .slide-deco .corner,.theme-wed-alt .slide-deco .corner,.theme-wed-accent .slide-deco .corner{color:#f5c6a5}
.theme-wed .slide-deco .dots span,.theme-wed-alt .slide-deco .dots span{background:#f5c6a5}

/* Theme: Workshop (Teal/Mint) */
.theme-wk{background:linear-gradient(145deg,#06111f,#0a192f)}
.theme-wk-alt{background:linear-gradient(145deg,#0a192f,#112240)}
.theme-wk-accent{background:linear-gradient(145deg,#112240,#0a192f)}
.theme-wk h4,.theme-wk-alt h4,.theme-wk-accent h4{color:#64ffda;font-size:16px}
.theme-wk p,.theme-wk-alt p,.theme-wk-accent p{color:#8892b0}
.theme-wk .tag{background:rgba(100,255,218,.08);color:#64ffda;border:1px solid rgba(100,255,218,.15)}
.theme-wk .divider,.theme-wk-alt .divider{background:#64ffda}
.theme-wk .slide-deco .circle,.theme-wk-alt .slide-deco .circle{background:#64ffda}
.theme-wk .slide-deco .corner,.theme-wk-alt .slide-deco .corner,.theme-wk-accent .slide-deco .corner{color:#64ffda}
.theme-wk .slide-deco .dots span,.theme-wk-alt .slide-deco .dots span{background:#64ffda}

/* Title slide special */
.slide-title{justify-content:center;align-items:center;text-align:center}
.slide-title h4{font-size:20px!important;margin-bottom:10px}
.slide-title .company-from{font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:1px;opacity:.5;margin-top:8px}

/* End slide special */
.slide-end{justify-content:center;align-items:center;text-align:center}
.slide-end h4{font-size:18px!important}
.slide-end .contact{font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.5px;opacity:.6;margin-top:10px}

/* Slide with metrics */
.metric-row{display:flex;gap:12px;margin-top:10px}
.metric{flex:1;text-align:center;padding:8px 4px;background:rgba(255,255,255,.04);border-radius:6px;border:1px solid rgba(255,255,255,.06)}
.metric .mv{font-size:16px;font-weight:800;color:#fff}
.metric .ml{font-size:8px;text-transform:uppercase;letter-spacing:1px;opacity:.5;margin-top:2px}

/* Timeline visual */
.timeline-row{display:flex;align-items:center;gap:0;margin-top:10px}
.tl-step{flex:1;text-align:center;position:relative;padding-top:12px}
.tl-step::before{content:'';position:absolute;top:4px;left:50%;width:8px;height:8px;border-radius:50%;transform:translateX(-50%)}
.tl-step::after{content:'';position:absolute;top:7px;left:50%;width:100%;height:1.5px;opacity:.2}
.tl-step:last-child::after{display:none}
.tl-step span{font-size:8px;line-height:1.3;display:block;opacity:.6}

/* Bullet list in slides */
.slide-list{list-style:none;padding:0;margin:6px 0}
.slide-list li{font-size:10px;padding:3px 0 3px 14px;position:relative;opacity:.75;line-height:1.5}
.slide-list li::before{content:'';position:absolute;left:0;top:8px;width:5px;height:5px;border-radius:50%}

/* Proposal footer */
.proposal-foot{display:flex;justify-content:space-between;align-items:center;padding:14px 0;margin-top:4px}
.proposal-foot .pf-tags{display:flex;gap:8px}
.proposal-foot .pf-tag{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text2);background:var(--card);border:1px solid var(--border);padding:5px 12px;border-radius:6px;display:flex;align-items:center;gap:5px}
.proposal-foot a{font-size:13px;color:var(--blue);text-decoration:none;font-weight:700;transition:.2s}
.proposal-foot a:hover{color:#fff}

/* Scroll hint */
.scroll-hint{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--text2);margin-bottom:8px}
.scroll-hint .arrow{animation:nudge 2s infinite;display:inline-block}
@keyframes nudge{0%,100%{transform:translateX(0)}50%{transform:translateX(6px)}}

/* Responsive */
@media(max-width:768px){
    .topbar{padding:12px 16px}
    .hero-section,.main{padding-left:16px;padding-right:16px}
    .proposal-head{flex-direction:column;gap:16px;text-align:left}
    .ph-right{text-align:left}
    .slide{min-width:260px;max-width:260px}
}
</style>
</head>
<body>

<div class="topbar">
    <a href="/" style="text-decoration:none;color:inherit"><h1>Proposal<span>Snap</span></h1></a>
    <div class="topbar-right">
        <a href="{{ hub_url }}">← SnapSuite</a>
        <a href="/" class="cta">+ Create New Proposal</a>
    </div>
</div>

<div class="hero-section">
    <div class="badge"><span class="dot"></span> AI-Generated Proposals</div>
    <h2>Sample Proposal Gallery</h2>
    <p class="sub">Each of these professional pitch decks was generated by AI in under 30 seconds. Upload your logo, describe your project, and ProposalSnap handles the rest.</p>
</div>

<div class="main">

<!-- ═══ PROPOSAL 1: Brand Identity ═══ -->
<div class="proposal">
    <div class="proposal-label" style="color:#e94560">● PROPOSAL 01</div>
    <div class="proposal-head theme-corporate">
        <div class="ph-left">
            <h3>Brand Identity Package</h3>
            <div class="ph-meta">
                <span>Bloom Studio → Varnam Artboutique</span>
                <span class="sep">·</span>
                <span>Feb 10, 2026</span>
                <span class="sep">·</span>
                <span>12 slides</span>
            </div>
        </div>
        <div class="ph-right">
            <div class="price">₹1,85,000</div>
            <span class="status sent">Sent</span>
        </div>
    </div>
    <div class="scroll-hint"><span>Scroll slides</span> <span class="arrow">→</span></div>
    <div class="slides-wrapper">
        <div class="slides-scroll">
            <!-- Slide 1: Title -->
            <div class="slide theme-corp">
                <div class="slide-deco">
                    <div class="corner tl" style="color:#e94560"></div>
                    <div class="corner br" style="color:#e94560"></div>
                    <div class="circle" style="width:200px;height:200px;right:-60px;bottom:-60px;background:#e94560"></div>
                    <div class="line" style="width:60%;bottom:30%;left:20%;background:linear-gradient(90deg,transparent,#e94560,transparent)"></div>
                </div>
                <div class="slide-inner slide-title">
                    <span class="tag">CORPORATE PROPOSAL</span>
                    <h4 style="margin-top:12px">Brand Identity<br>Package</h4>
                    <div class="divider" style="margin:8px auto"></div>
                    <p style="font-size:12px;color:#eee">Prepared for <strong>Varnam Artboutique</strong></p>
                    <span class="company-from">BY BLOOM STUDIO</span>
                </div>
                <div class="slide-num">01</div>
            </div>

            <!-- Slide 2: The Challenge -->
            <div class="slide theme-corp-alt">
                <div class="slide-deco">
                    <div class="corner tl" style="color:#e94560"></div>
                    <div class="dots" style="right:16px;bottom:16px;color:#e94560"><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div>
                </div>
                <div class="slide-inner">
                    <span class="slide-label">THE CHALLENGE</span>
                    <h4>Why Rebrand Now?</h4>
                    <div class="divider"></div>
                    <p>Varnam Artboutique is expanding into international markets. Current branding doesn't reflect their premium positioning or rich cultural heritage. Competitors are investing heavily in design.</p>
                    <div class="metric-row">
                        <div class="metric"><div class="mv" style="color:#e94560">73%</div><div class="ml">Need Update</div></div>
                        <div class="metric"><div class="mv" style="color:#e94560">2.4×</div><div class="ml">Brand Recall</div></div>
                    </div>
                </div>
                <div class="slide-num">02</div>
            </div>

            <!-- Slide 3: Our Approach -->
            <div class="slide theme-corp-accent">
                <div class="slide-deco">
                    <div class="corner tl" style="color:#e94560"></div>
                    <div class="corner br" style="color:#e94560"></div>
                    <div class="circle" style="width:120px;height:120px;left:-30px;top:-30px;background:#e94560"></div>
                </div>
                <div class="slide-inner">
                    <span class="slide-label">OUR APPROACH</span>
                    <h4>6-Phase Process</h4>
                    <div class="divider"></div>
                    <ul class="slide-list">
                        <li style="--c:#e94560">Discovery &amp; Brand Audit</li>
                        <li style="--c:#e94560">Concept Development</li>
                        <li style="--c:#e94560">Visual Design System</li>
                        <li style="--c:#e94560">Brand Guidelines</li>
                        <li style="--c:#e94560">Collateral Design</li>
                        <li style="--c:#e94560">Handoff &amp; Training</li>
                    </ul>
                </div>
                <div class="slide-num">03</div>
            </div>

            <!-- Slide 4: Logo -->
            <div class="slide theme-corp">
                <div class="slide-deco">
                    <div class="dots" style="left:16px;top:16px;color:#e94560"><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div>
                    <div class="line" style="width:40%;top:50%;right:0;background:#e94560"></div>
                </div>
                <div class="slide-inner">
                    <span class="slide-label">DELIVERABLE</span>
                    <h4>Logo Redesign</h4>
                    <div class="divider"></div>
                    <p>Modern mark blending Madhubani art motifs with contemporary typography. Primary, secondary, and icon variations.</p>
                    <div class="icon-row">
                        <span>🎨</span><span>✏️</span><span>📐</span>
                    </div>
                </div>
                <div class="slide-num">04</div>
            </div>

            <!-- Slide 5: Color Palette -->
            <div class="slide theme-corp-alt">
                <div class="slide-deco">
                    <div class="corner tl" style="color:#e94560"></div>
                    <div class="circle" style="width:80px;height:80px;right:20px;top:20px;background:#c62a88;opacity:.12"></div>
                    <div class="circle" style="width:60px;height:60px;right:60px;top:50px;background:#e94560;opacity:.1"></div>
                </div>
                <div class="slide-inner">
                    <span class="slide-label">VISUAL SYSTEM</span>
                    <h4>Color Palette</h4>
                    <div class="divider"></div>
                    <p>Rich earth tones paired with vibrant accents inspired by traditional Indian textiles and natural dyes.</p>
                    <div style="display:flex;gap:6px;margin-top:10px">
                        <div style="width:28px;height:28px;border-radius:6px;background:#e94560;border:2px solid rgba(255,255,255,.1)"></div>
                        <div style="width:28px;height:28px;border-radius:6px;background:#c62a88;border:2px solid rgba(255,255,255,.1)"></div>
                        <div style="width:28px;height:28px;border-radius:6px;background:#0f3460;border:2px solid rgba(255,255,255,.1)"></div>
                        <div style="width:28px;height:28px;border-radius:6px;background:#f5c6a5;border:2px solid rgba(255,255,255,.1)"></div>
                        <div style="width:28px;height:28px;border-radius:6px;background:#1a1a2e;border:2px solid rgba(255,255,255,.1)"></div>
                    </div>
                </div>
                <div class="slide-num">05</div>
            </div>

            <!-- Slide 6: Typography -->
            <div class="slide theme-corp-accent">
                <div class="slide-deco">
                    <div class="corner br" style="color:#e94560"></div>
                </div>
                <div class="slide-inner">
                    <span class="slide-label">VISUAL SYSTEM</span>
                    <h4>Typography</h4>
                    <div class="divider"></div>
                    <div style="margin-top:4px">
                        <div style="font-family:'Playfair Display',serif;font-size:18px;color:#fff;font-weight:700">Aa Heading</div>
                        <div style="font-size:10px;opacity:.5;margin-bottom:6px">Playfair Display · Serif</div>
                        <div style="font-family:'DM Sans',sans-serif;font-size:12px;color:#ccc">Aa Body text sample</div>
                        <div style="font-size:10px;opacity:.5;margin-bottom:6px">DM Sans · Sans-serif</div>
                        <div style="font-size:12px;color:#ccc">आ देवनागरी</div>
                        <div style="font-size:10px;opacity:.5">Matching Hindi family</div>
                    </div>
                </div>
                <div class="slide-num">06</div>
            </div>

            <!-- Slide 7: Collateral -->
            <div class="slide theme-corp">
                <div class="slide-deco">
                    <div class="dots" style="right:16px;top:16px;color:#e94560"><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div>
                    <div class="corner tl" style="color:#e94560"></div>
                </div>
                <div class="slide-inner">
                    <span class="slide-label">DELIVERABLES</span>
                    <h4>Collateral Design</h4>
                    <div class="divider"></div>
                    <ul class="slide-list">
                        <li style="--c:#e94560">Business cards &amp; letterhead</li>
                        <li style="--c:#e94560">Packaging inserts &amp; labels</li>
                        <li style="--c:#e94560">Exhibition banners (3 sizes)</li>
                        <li style="--c:#e94560">Social media templates</li>
                        <li style="--c:#e94560">WhatsApp catalog design</li>
                    </ul>
                </div>
                <div class="slide-num">07</div>
            </div>

            <!-- Slide 8: Digital -->
            <div class="slide theme-corp-alt">
                <div class="slide-deco">
                    <div class="corner tl" style="color:#e94560"></div>
                    <div class="corner br" style="color:#e94560"></div>
                </div>
                <div class="slide-inner">
                    <span class="slide-label">DIGITAL</span>
                    <h4>Online Presence</h4>
                    <div class="divider"></div>
                    <p>Website UI kit, email templates, Instagram grid layout, Google Business profile assets, and e-commerce product page templates.</p>
                </div>
                <div class="slide-num">08</div>
            </div>

            <!-- Slide 9: Guidelines -->
            <div class="slide theme-corp-accent">
                <div class="slide-deco">
                    <div class="circle" style="width:160px;height:160px;right:-40px;bottom:-40px;background:#e94560"></div>
                </div>
                <div class="slide-inner">
                    <span class="slide-label">DELIVERABLE</span>
                    <h4>Brand Guidelines</h4>
                    <div class="divider"></div>
                    <p>60-page comprehensive guide: logo usage, do's &amp; don'ts, spacing rules, color specs (CMYK, RGB, Pantone), voice &amp; tone.</p>
                    <div class="metric-row">
                        <div class="metric"><div class="mv" style="color:#e94560">60</div><div class="ml">Pages</div></div>
                        <div class="metric"><div class="mv" style="color:#e94560">3</div><div class="ml">Formats</div></div>
                    </div>
                </div>
                <div class="slide-num">09</div>
            </div>

            <!-- Slide 10: Timeline -->
            <div class="slide theme-corp">
                <div class="slide-deco">
                    <div class="corner tl" style="color:#e94560"></div>
                    <div class="line" style="width:80%;bottom:40px;left:10%;background:#e94560"></div>
                </div>
                <div class="slide-inner">
                    <span class="slide-label">TIMELINE</span>
                    <h4>10-Week Plan</h4>
                    <div class="divider"></div>
                    <div class="timeline-row">
                        <div class="tl-step" style="--c:#e94560"><span>Wk 1-2<br><strong style="color:#e94560">Discovery</strong></span></div>
                        <div class="tl-step" style="--c:#e94560"><span>Wk 3-4<br><strong style="color:#e94560">Concepts</strong></span></div>
                        <div class="tl-step" style="--c:#e94560"><span>Wk 5-6<br><strong style="color:#e94560">Refine</strong></span></div>
                        <div class="tl-step" style="--c:#e94560"><span>Wk 7-8<br><strong style="color:#e94560">Build</strong></span></div>
                        <div class="tl-step" style="--c:#e94560"><span>Wk 9-10<br><strong style="color:#e94560">Handoff</strong></span></div>
                    </div>
                </div>
                <div class="slide-num">10</div>
            </div>

            <!-- Slide 11: Investment -->
            <div class="slide theme-corp-alt">
                <div class="slide-deco">
                    <div class="corner tl" style="color:#e94560"></div>
                    <div class="corner br" style="color:#e94560"></div>
                    <div class="dots" style="left:16px;bottom:16px;color:#e94560"><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div>
                </div>
                <div class="slide-inner">
                    <span class="slide-label">INVESTMENT</span>
                    <h4>₹1,85,000</h4>
                    <div class="divider"></div>
                    <div class="metric-row">
                        <div class="metric"><div class="mv" style="color:#e94560">50%</div><div class="ml">Upfront</div></div>
                        <div class="metric"><div class="mv" style="color:#e94560">25%</div><div class="ml">Concepts</div></div>
                        <div class="metric"><div class="mv" style="color:#e94560">25%</div><div class="ml">Delivery</div></div>
                    </div>
                    <p style="margin-top:8px;font-size:10px">Includes 3 revision rounds per phase</p>
                </div>
                <div class="slide-num">11</div>
            </div>

            <!-- Slide 12: Thank You -->
            <div class="slide theme-corp-dark">
                <div class="slide-deco">
                    <div class="corner tl" style="color:#e94560"></div>
                    <div class="corner br" style="color:#e94560"></div>
                    <div class="circle" style="width:240px;height:240px;left:50%;top:50%;transform:translate(-50%,-50%);background:#e94560;opacity:.04"></div>
                </div>
                <div class="slide-inner slide-end">
                    <h4>Let's Create<br>Something Beautiful</h4>
                    <div class="divider" style="margin:10px auto"></div>
                    <span class="contact">hello@bloomstudio.in<br>+91 98765 43210</span>
                    <span class="tag" style="margin-top:12px">BLOOM STUDIO</span>
                </div>
                <div class="slide-num">12</div>
            </div>
        </div>
    </div>
    <div class="proposal-foot">
        <div class="pf-tags">
            <span class="pf-tag">📄 12 slides</span>
            <span class="pf-tag">🏢 Corporate</span>
            <span class="pf-tag">🔤 Aptos</span>
        </div>
        <a href="/">Recreate this →</a>
    </div>
</div>

<!-- ═══ PROPOSAL 2: Wedding Decor ═══ -->
<div class="proposal">
    <div class="proposal-label" style="color:#f5c6a5">● PROPOSAL 02</div>
    <div class="proposal-head theme-wedding">
        <div class="ph-left">
            <h3>Wedding Decor — Lotus Theme Collection</h3>
            <div class="ph-meta">
                <span>Bloom Studio → Priya &amp; Arjun</span>
                <span class="sep">·</span>
                <span>Jan 22, 2026</span>
                <span class="sep">·</span>
                <span>8 slides</span>
            </div>
        </div>
        <div class="ph-right">
            <div class="price">₹95,000</div>
            <span class="status accepted">Accepted</span>
        </div>
    </div>
    <div class="scroll-hint"><span>Scroll slides</span> <span class="arrow">→</span></div>
    <div class="slides-wrapper">
        <div class="slides-scroll">
            <div class="slide theme-wed">
                <div class="slide-deco">
                    <div class="corner tl" style="color:#f5c6a5"></div>
                    <div class="corner br" style="color:#f5c6a5"></div>
                    <div class="circle" style="width:180px;height:180px;right:-50px;bottom:-50px;background:#c62a88"></div>
                </div>
                <div class="slide-inner slide-title">
                    <span class="tag">CREATIVE PITCH</span>
                    <h4 style="color:#f5c6a5;margin-top:12px">Lotus Theme<br>Collection</h4>
                    <div class="divider" style="background:linear-gradient(90deg,#f5c6a5,#c62a88);margin:8px auto"></div>
                    <p style="color:#eee;font-size:12px">A bespoke wedding experience for <strong>Priya &amp; Arjun</strong></p>
                    <span class="company-from" style="color:#d4a9b8">BY BLOOM STUDIO</span>
                </div>
                <div class="slide-num">01</div>
            </div>
            <div class="slide theme-wed-alt">
                <div class="slide-deco"><div class="corner tl" style="color:#f5c6a5"></div><div class="dots" style="right:16px;bottom:16px;color:#f5c6a5"><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div></div>
                <div class="slide-inner">
                    <span class="slide-label" style="color:#f5c6a5">YOUR VISION</span>
                    <h4>Modern Tradition</h4>
                    <div class="divider"></div>
                    <p>A celebration that honors tradition while feeling intimate, modern, and uniquely yours. Lotus symbolism woven throughout every detail.</p>
                </div>
                <div class="slide-num">02</div>
            </div>
            <div class="slide theme-wed-accent">
                <div class="slide-deco"><div class="corner tl" style="color:#f5c6a5"></div><div class="corner br" style="color:#f5c6a5"></div></div>
                <div class="slide-inner">
                    <span class="slide-label" style="color:#f5c6a5">CENTREPIECE</span>
                    <h4>Mandap Design</h4>
                    <div class="divider" style="background:linear-gradient(90deg,#f5c6a5,#c62a88)"></div>
                    <p>Hand-carved wooden structure with cascading lotus garlands, silk draping in ivory and blush, and hanging brass diyas creating warm, ambient glow.</p>
                </div>
                <div class="slide-num">03</div>
            </div>
            <div class="slide theme-wed">
                <div class="slide-deco"><div class="circle" style="width:100px;height:100px;left:-30px;top:-30px;background:#c62a88"></div></div>
                <div class="slide-inner">
                    <span class="slide-label" style="color:#f5c6a5">DETAILS</span>
                    <h4>Table Settings</h4>
                    <div class="divider" style="background:linear-gradient(90deg,#f5c6a5,#c62a88)"></div>
                    <ul class="slide-list">
                        <li style="--c:#f5c6a5">Brass lotus candle holders</li>
                        <li style="--c:#f5c6a5">Hand-painted menu cards</li>
                        <li style="--c:#f5c6a5">Silk Rajasthani block-print runners</li>
                        <li style="--c:#f5c6a5">Fresh flower rangoli</li>
                    </ul>
                </div>
                <div class="slide-num">04</div>
            </div>
            <div class="slide theme-wed-alt">
                <div class="slide-deco"><div class="corner tl" style="color:#f5c6a5"></div></div>
                <div class="slide-inner">
                    <span class="slide-label" style="color:#f5c6a5">ENTRANCE</span>
                    <h4>Welcome Arch</h4>
                    <div class="divider" style="background:linear-gradient(90deg,#f5c6a5,#c62a88)"></div>
                    <p>12-foot arch with woven jasmine and marigold base, oversized paper lotus blooms, and warm LED fairy lights creating a magical first impression.</p>
                </div>
                <div class="slide-num">05</div>
            </div>
            <div class="slide theme-wed-accent">
                <div class="slide-deco"><div class="dots" style="left:16px;bottom:16px;color:#f5c6a5"><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div></div>
                <div class="slide-inner">
                    <span class="slide-label" style="color:#f5c6a5">AMBIENCE</span>
                    <h4>Lighting Design</h4>
                    <div class="divider" style="background:linear-gradient(90deg,#f5c6a5,#c62a88)"></div>
                    <p>Warm amber uplighting, floating lotus candles in water features, vintage brass lanterns along pathways, and canopy fairy lights.</p>
                </div>
                <div class="slide-num">06</div>
            </div>
            <div class="slide theme-wed">
                <div class="slide-deco"><div class="corner tl" style="color:#f5c6a5"></div><div class="corner br" style="color:#f5c6a5"></div></div>
                <div class="slide-inner">
                    <span class="slide-label" style="color:#f5c6a5">INVESTMENT</span>
                    <h4>₹95,000</h4>
                    <div class="divider" style="background:linear-gradient(90deg,#f5c6a5,#c62a88)"></div>
                    <p>Complete package including setup, all materials, lighting, day-of coordination, and breakdown. Travel within Jaipur included.</p>
                    <div class="metric-row">
                        <div class="metric"><div class="mv" style="color:#f5c6a5">40%</div><div class="ml">Booking</div></div>
                        <div class="metric"><div class="mv" style="color:#f5c6a5">60%</div><div class="ml">Event Day</div></div>
                    </div>
                </div>
                <div class="slide-num">07</div>
            </div>
            <div class="slide theme-wed-accent">
                <div class="slide-deco">
                    <div class="corner tl" style="color:#f5c6a5"></div><div class="corner br" style="color:#f5c6a5"></div>
                    <div class="circle" style="width:200px;height:200px;left:50%;top:50%;transform:translate(-50%,-50%);background:#c62a88;opacity:.06"></div>
                </div>
                <div class="slide-inner slide-end">
                    <h4 style="color:#f5c6a5">Let's Make Your<br>Day Magical ✨</h4>
                    <div class="divider" style="background:linear-gradient(90deg,#f5c6a5,#c62a88);margin:10px auto"></div>
                    <span class="contact" style="color:#d4a9b8">hello@bloomstudio.in<br>+91 98765 43210</span>
                </div>
                <div class="slide-num">08</div>
            </div>
        </div>
    </div>
    <div class="proposal-foot">
        <div class="pf-tags">
            <span class="pf-tag">📄 8 slides</span>
            <span class="pf-tag">💒 Creative Pitch</span>
            <span class="pf-tag">🌸 Warm Tone</span>
        </div>
        <a href="/">Recreate this →</a>
    </div>
</div>

<!-- ═══ PROPOSAL 3: Corporate Workshop ═══ -->
<div class="proposal">
    <div class="proposal-label" style="color:#64ffda">● PROPOSAL 03</div>
    <div class="proposal-head theme-workshop">
        <div class="ph-left">
            <h3>Corporate Art Workshop — Q1 Team Building</h3>
            <div class="ph-meta">
                <span>Bloom Studio → TechNova Solutions</span>
                <span class="sep">·</span>
                <span>Feb 14, 2026</span>
                <span class="sep">·</span>
                <span>6 slides</span>
            </div>
        </div>
        <div class="ph-right">
            <div class="price">₹45,000</div>
            <span class="status draft">Draft</span>
        </div>
    </div>
    <div class="scroll-hint"><span>Scroll slides</span> <span class="arrow">→</span></div>
    <div class="slides-wrapper">
        <div class="slides-scroll">
            <div class="slide theme-wk">
                <div class="slide-deco">
                    <div class="corner tl" style="color:#64ffda"></div>
                    <div class="corner br" style="color:#64ffda"></div>
                    <div class="circle" style="width:180px;height:180px;right:-50px;bottom:-50px;background:#64ffda"></div>
                </div>
                <div class="slide-inner slide-title">
                    <span class="tag">CORPORATE PROPOSAL</span>
                    <h4 style="color:#64ffda;margin-top:12px">Art &amp; Team<br>Workshop</h4>
                    <div class="divider" style="background:#64ffda;margin:8px auto"></div>
                    <p style="color:#ccd6f6;font-size:12px">Prepared for <strong>TechNova Solutions</strong></p>
                    <span class="company-from" style="color:#64ffda">Q1 TEAM BUILDING</span>
                </div>
                <div class="slide-num">01</div>
            </div>
            <div class="slide theme-wk-alt">
                <div class="slide-deco"><div class="corner tl" style="color:#64ffda"></div><div class="dots" style="right:16px;bottom:16px;color:#64ffda"><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div></div>
                <div class="slide-inner">
                    <span class="slide-label" style="color:#64ffda">WHY ART?</span>
                    <h4>Creative Impact</h4>
                    <div class="divider" style="background:#64ffda"></div>
                    <p>Creative activities boost lateral thinking, reduce stress, and build trust between team members in ways traditional offsites can't match.</p>
                    <div class="metric-row">
                        <div class="metric"><div class="mv" style="color:#64ffda">40%</div><div class="ml">Creativity ↑</div></div>
                        <div class="metric"><div class="mv" style="color:#64ffda">67%</div><div class="ml">Team Trust ↑</div></div>
                    </div>
                </div>
                <div class="slide-num">02</div>
            </div>
            <div class="slide theme-wk-accent">
                <div class="slide-deco"><div class="corner tl" style="color:#64ffda"></div><div class="corner br" style="color:#64ffda"></div></div>
                <div class="slide-inner">
                    <span class="slide-label" style="color:#64ffda">THE EXPERIENCE</span>
                    <h4>3-Hour Session</h4>
                    <div class="divider" style="background:#64ffda"></div>
                    <div class="timeline-row">
                        <div class="tl-step"><span>45 min<br><strong style="color:#64ffda">Basics</strong></span></div>
                        <div class="tl-step"><span>60 min<br><strong style="color:#64ffda">Guided</strong></span></div>
                        <div class="tl-step"><span>75 min<br><strong style="color:#64ffda">Mural</strong></span></div>
                        <div class="tl-step"><span>Gallery<br><strong style="color:#64ffda">Walk</strong></span></div>
                    </div>
                </div>
                <div class="slide-num">03</div>
            </div>
            <div class="slide theme-wk">
                <div class="slide-deco"><div class="circle" style="width:120px;height:120px;left:-30px;bottom:-30px;background:#64ffda"></div></div>
                <div class="slide-inner">
                    <span class="slide-label" style="color:#64ffda">INCLUDED</span>
                    <h4>What's Provided</h4>
                    <div class="divider" style="background:#64ffda"></div>
                    <ul class="slide-list">
                        <li style="--c:#64ffda">All materials (brushes, paints, canvas)</li>
                        <li style="--c:#64ffda">2 professional art instructors</li>
                        <li style="--c:#64ffda">Aprons for all participants</li>
                        <li style="--c:#64ffda">4×6ft collaborative canvas</li>
                        <li style="--c:#64ffda">Framing for individual works</li>
                    </ul>
                </div>
                <div class="slide-num">04</div>
            </div>
            <div class="slide theme-wk-alt">
                <div class="slide-deco"><div class="corner tl" style="color:#64ffda"></div><div class="corner br" style="color:#64ffda"></div></div>
                <div class="slide-inner">
                    <span class="slide-label" style="color:#64ffda">INVESTMENT</span>
                    <h4>₹45,000</h4>
                    <div class="divider" style="background:#64ffda"></div>
                    <p>For up to 25 participants. Includes all materials, instruction, venue setup, and a finished mural for your office wall.</p>
                    <div class="metric-row">
                        <div class="metric"><div class="mv" style="color:#64ffda">25</div><div class="ml">Max People</div></div>
                        <div class="metric"><div class="mv" style="color:#64ffda">3hr</div><div class="ml">Duration</div></div>
                    </div>
                </div>
                <div class="slide-num">05</div>
            </div>
            <div class="slide theme-wk-accent">
                <div class="slide-deco">
                    <div class="corner tl" style="color:#64ffda"></div><div class="corner br" style="color:#64ffda"></div>
                    <div class="circle" style="width:200px;height:200px;left:50%;top:50%;transform:translate(-50%,-50%);background:#64ffda;opacity:.04"></div>
                </div>
                <div class="slide-inner slide-end">
                    <h4 style="color:#64ffda">Let's Create<br>Together 🎨</h4>
                    <div class="divider" style="background:#64ffda;margin:10px auto"></div>
                    <span class="contact" style="color:#8892b0">hello@bloomstudio.in<br>+91 98765 43210</span>
                    <span class="tag" style="margin-top:12px">BLOOM STUDIO</span>
                </div>
                <div class="slide-num">06</div>
            </div>
        </div>
    </div>
    <div class="proposal-foot">
        <div class="pf-tags">
            <span class="pf-tag">📄 6 slides</span>
            <span class="pf-tag">🏢 Corporate</span>
            <span class="pf-tag">🎨 Creative</span>
        </div>
        <a href="/">Recreate this →</a>
    </div>
</div>

</div>

<style>
.slide-list li::before{background:var(--c, #888)}
.tl-step::before{background:var(--c, #888)}
.tl-step::after{background:var(--c, #888)}
</style>
</body></html>'''
