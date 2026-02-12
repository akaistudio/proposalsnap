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
from flask import Flask, request, jsonify, send_file, render_template_string

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
    prompt = f"""Generate a professional {pres_type} presentation structure.

Client: {client_name}
Presenting Company: {company_name}
Tone: {tone}
Number of Slides: {num_slides}

Key Points / Requirements:
{key_points}

Return ONLY a valid JSON array of slide objects. Each slide MUST have these fields:
- "layout": one of "title", "agenda", "content", "two_column", "stats", "timeline", "pricing", "team", "closing"
- "title": slide title
- Additional fields based on layout:

For "title": subtitle (string)
For "agenda": bullets (array of strings, 5-7 items)
For "content": bullets (array of 3-5 strings) OR body (paragraph text), optional subtitle
For "two_column": left_title, left_bullets (array), right_title, right_bullets (array)
For "stats": stats (array of objects with value, label, description)
For "timeline": steps (array of objects with phase, description, duration)
For "pricing": tiers (array of objects with name, price, features array, highlight boolean)
For "team": members (array of objects with name, role, bio)
For "closing": subtitle, contact (string)

RULES:
1. First slide MUST be layout "title"
2. Second slide MUST be layout "agenda"
3. Last slide MUST be layout "closing"
4. Include at least one "stats" slide and one "timeline" slide
5. Mix different layouts — do NOT use "content" for every slide
6. Bullets should be concise but informative (10-20 words each)
7. Stats should have realistic, specific numbers
8. Make content specific to the client and key points provided
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
def create_pptx(slides, colors, client_name, company_name, pres_type, tone, logo_path=None):
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
        "logoPath": str(logo_path) if logo_path else None
    }
    
    script_path = Path(__file__).parent / "generate_pptx.js"
    result = subprocess.run(
        ["node", str(script_path)],
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
        output_path = create_pptx(slides, colors, client_name, company_name, pres_type, tone, logo_path)
        
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
.row3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}
@media(max-width:600px){.row3{grid-template-columns:1fr}}
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
<h1>ProposalSnap</h1>
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
