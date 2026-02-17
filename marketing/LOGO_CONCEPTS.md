# BlackBoxAF Logo Concepts

## Design Brief
**Color Palette** (from ckingmuzic.com):
- Primary: Black (#000000)
- Accent: Orange (#F08734) - THE signature color
- Neutral: Gray (#8E8E8E)
- Background: Very Dark Gray (#171717)

**Typography**: Teko (bold, geometric) + Lato (clean sans-serif)

**Mood**: Modern, bold, minimalist, tech-forward

---

## Concept 1: The Pattern Matrix (Recommended)

```
╔═══════╗
║ █▓▒░  ║   B L A C K B O X  A F
╚═══════╝
```

**Visual Elements**:
- Square box (represents "black box" + pattern "blocks")
- Gradient pattern blocks inside (█▓▒░) - symbolizes extraction/transformation
- Orange border, dark gray fill
- Geometric, tech-forward

**SVG Version** (icon.svg):
```svg
<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
  <!-- Outer box - orange accent -->
  <rect x="20" y="20" width="160" height="160"
        fill="#171717" stroke="#F08734" stroke-width="6" rx="8"/>

  <!-- Pattern blocks - descending opacity (extraction metaphor) -->
  <rect x="40" y="50" width="35" height="35" fill="#F08734" opacity="1.0"/>
  <rect x="80" y="50" width="35" height="35" fill="#F08734" opacity="0.7"/>
  <rect x="120" y="50" width="35" height="35" fill="#F08734" opacity="0.4"/>

  <!-- Second row - offset -->
  <rect x="60" y="95" width="35" height="35" fill="#8E8E8E" opacity="0.8"/>
  <rect x="100" y="95" width="35" height="35" fill="#8E8E8E" opacity="0.5"/>

  <!-- Bottom row - faded (anonymized) -->
  <rect x="40" y="135" width="35" height="35" fill="#8E8E8E" opacity="0.3"/>
  <rect x="80" y="135" width="35" height="35" fill="#8E8E8E" opacity="0.2"/>
  <rect x="120" y="135" width="35" height="35" fill="#8E8E8E" opacity="0.1"/>
</svg>
```

**Meaning**: Patterns start bright (extracted), get processed (middle), become anonymized (faded gray at bottom). The descending gradient tells the whole story.

---

## Concept 2: The Flow Connector

```
  ┌─┐
  │█│ ───→ ○ ───→ ◇
  └─┘
```

**Visual Elements**:
- Decision diamond + circle + rectangle (classic flow symbols)
- Connected with arrows
- Orange shapes, dark background
- Direct reference to Salesforce flow patterns

**Use Case**: More literal (shows "we extract flows"), but less abstract/memorable than Concept 1.

---

## Concept 3: The Data Transform

```
[ClientPay__c] ──→ [Brand_A__c]
```

**Visual Elements**:
- Left: colorful/detailed (raw metadata)
- Arrow: transformation
- Right: simplified/grayscale (anonymized)
- Two-sided logo showing before/after

**Use Case**: Educational (explains anonymization), but too literal for branding.

---

## Recommended: Concept 1 (Pattern Matrix)

**Why it works**:
1. **Matches your site aesthetic** - orange accent (#F08734), dark backgrounds, geometric
2. **Tells the story** - bright patterns → processed → anonymized (top to bottom)
3. **Scalable** - looks good at 16px (favicon) and 512px (splash screen)
4. **Memorable** - simple geometric form, not cluttered
5. **Professional** - clean, modern, technical

---

## File Deliverables

I'll create:
1. `icon.svg` - Full color vector logo (for website, GitHub)
2. `icon-16.png` - Favicon (16x16)
3. `icon-32.png` - Favicon (32x32)
4. `icon-256.png` - App icon (256x256)
5. `icon.ico` - Windows icon (multi-resolution)
6. `logo-horizontal.svg` - Logo + "BlackBoxAF" text (for headers)

All using:
- Orange: #F08734
- Dark Gray: #171717
- Light Gray: #8E8E8E
- Teko Bold for text

---

## Usage

### Website (PageCloud):
```html
<img src="blackboxaf-logo.svg" alt="BlackBoxAF" width="120" height="120">
```

### GitHub README:
```markdown
<div align="center">
  <img src="docs/logo.svg" alt="BlackBoxAF" width="200"/>
</div>
```

### Favicon (in HTML):
```html
<link rel="icon" type="image/x-icon" href="/favicon.ico">
```

---

## Next Steps

1. I'll generate the SVG files with the exact color codes
2. Convert to PNG at various sizes (ImageMagick or Inkscape)
3. Bundle into icon.ico for Windows .exe
4. Add to build_exe.py so the .exe has a proper icon

Want me to generate all the files now?
