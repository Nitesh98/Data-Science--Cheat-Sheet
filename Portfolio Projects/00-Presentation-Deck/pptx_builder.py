"""
Minimal, dependency-free .pptx builder (Python stdlib only: zipfile + string
templating). Used because this sandbox can't install pptxgenjs or
python-pptx (no npm/pip registry access). Produces a real, valid OOXML
16:9 presentation: solid-fill shapes, text boxes, and "charts" built from
proportionally-sized rectangles (since hand-writing native PowerPoint
chart XML + embedded workbook parts by hand is far more error-prone than
this, for no visual benefit in a static portfolio deck).

Coordinates are in inches; converted to EMU (914400 per inch) internally.
"""
import html
import zipfile

EMU_PER_IN = 914400
SLIDE_W_IN = 13.333
SLIDE_H_IN = 7.5


def _emu(inches):
    return str(round(inches * EMU_PER_IN))


def _esc(text):
    return html.escape(str(text), quote=True)


class Slide:
    def __init__(self, bg_color):
        self.bg_color = bg_color
        self.shapes_xml = []
        self._id = 1

    def _next_id(self):
        self._id += 1
        return self._id

    def add_rect(self, x, y, w, h, fill=None, line_color=None, line_w=0, radius=False, shadow=False):
        geom = "roundRect" if radius else "rect"
        fill_xml = f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>' if fill else '<a:noFill/>'
        line_xml = (f'<a:ln w="{round(line_w*12700)}"><a:solidFill><a:srgbClr val="{line_color}"/></a:solidFill></a:ln>'
                    if line_color else '<a:ln><a:noFill/></a:ln>')
        shadow_xml = ('<a:effectLst><a:outerShdw blurRad="90000" dist="30000" dir="5400000" rotWithShape="0">'
                      '<a:srgbClr val="000000"><a:alpha val="25000"/></a:srgbClr></a:outerShdw></a:effectLst>'
                      if shadow else '')
        sid = self._next_id()
        self.shapes_xml.append(f'''
<p:sp>
  <p:nvSpPr><p:cNvPr id="{sid}" name="Rect{sid}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{_emu(x)}" y="{_emu(y)}"/><a:ext cx="{_emu(w)}" cy="{_emu(h)}"/></a:xfrm>
    <a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom>
    {fill_xml}
    {line_xml}
    {shadow_xml}
  </p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody>
</p:sp>''')

    def add_ellipse(self, x, y, w, h, fill, text=None, text_color="FFFFFF", size=14, bold=True):
        sid = self._next_id()
        text_xml = self._para(text, size, text_color, bold, align="ctr") if text else '<a:p/>'
        self.shapes_xml.append(f'''
<p:sp>
  <p:nvSpPr><p:cNvPr id="{sid}" name="Ellipse{sid}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{_emu(x)}" y="{_emu(y)}"/><a:ext cx="{_emu(w)}" cy="{_emu(h)}"/></a:xfrm>
    <a:prstGeom prst="ellipse"><a:avLst/></a:prstGeom>
    <a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>
    <a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody><a:bodyPr anchor="ctr"/><a:lstStyle/>{text_xml}</p:txBody>
</p:sp>''')

    def _para(self, text, size, color, bold, align="l"):
        b = "1" if bold else "0"
        return (f'<a:p><a:pPr algn="{align}"/><a:r>'
                f'<a:rPr lang="en-US" sz="{int(size*100)}" b="{b}" dirty="0">'
                f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
                f'<a:latin typeface="Calibri"/></a:rPr>'
                f'<a:t>{_esc(text)}</a:t></a:r></a:p>')

    def add_textbox(self, x, y, w, h, lines, align="l", anchor="t", wrap=True, margin=0.0):
        """lines: list of (text, size, color, bold) tuples, one per paragraph."""
        wrap_attr = "square" if wrap else "none"
        paras = "".join(self._para(t, s, c, b, align) for (t, s, c, b) in lines)
        m = round(margin * EMU_PER_IN)
        sid = self._next_id()
        self.shapes_xml.append(f'''
<p:sp>
  <p:nvSpPr><p:cNvPr id="{sid}" name="Text{sid}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{_emu(x)}" y="{_emu(y)}"/><a:ext cx="{_emu(w)}" cy="{_emu(h)}"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
    <a:noFill/>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="{wrap_attr}" anchor="{anchor}" lIns="{m}" tIns="{m}" rIns="{m}" bIns="{m}"/>
    <a:lstStyle/>
    {paras}
  </p:txBody>
</p:sp>''')

    def add_bar_chart(self, x, y, w, h, labels, values, color, value_fmt=None, label_color="52514E",
                       value_color="0B0B0B", baseline_color="C3C2B7", highlight_idx=None, highlight_color=None):
        """A simple column chart drawn from plain rectangles -- no native chart part."""
        value_fmt = value_fmt or (lambda v: f"{v:g}")
        n = len(labels)
        gap = 0.15
        band = (w - gap * (n - 1)) / n
        bar_w = band * 0.62
        max_v = max(values) if values else 1
        plot_h = h - 0.55  # reserve space for category labels + value labels
        # baseline
        self.add_rect(x, y + plot_h, w, 0.02, fill=baseline_color)
        for i, (lab, val) in enumerate(zip(labels, values)):
            bx = x + i * (band + gap) + (band - bar_w) / 2
            bar_h = max(0.05, plot_h * (val / max_v)) if max_v else 0.05
            by = y + plot_h - bar_h
            fill = highlight_color if (highlight_idx is not None and i == highlight_idx and highlight_color) else color
            self.add_rect(bx, by, bar_w, bar_h, fill=fill)
            self.add_textbox(bx - 0.15, by - 0.32, bar_w + 0.3, 0.3, [(value_fmt(val), 11, value_color, True)], align="ctr", anchor="b")
            self.add_textbox(bx - 0.2, y + plot_h + 0.05, bar_w + 0.4, 0.45, [(lab, 10, label_color, False)], align="ctr", anchor="t")

    def to_xml(self):
        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg><p:bgPr><a:solidFill><a:srgbClr val="{self.bg_color}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      {"".join(self.shapes_xml)}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>'''


class Presentation:
    def __init__(self):
        self.slides = []

    def add_slide(self, bg_color="FFFFFF"):
        s = Slide(bg_color)
        self.slides.append(s)
        return s

    def save(self, path):
        n = len(self.slides)
        content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
  <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
  ''' + "\n".join(
            f'<Override PartName="/ppt/slides/slide{i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
            for i in range(n)) + '''
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>'''

        root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''

        sld_id_lst = "\n".join(f'<p:sldId id="{256+i}" r:id="rId{i+10}"/>' for i in range(n))
        presentation_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
  <p:sldIdLst>{sld_id_lst}</p:sldIdLst>
  <p:sldSz cx="{_emu(SLIDE_W_IN)}" cy="{_emu(SLIDE_H_IN)}" type="screen16x9"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>'''

        pres_rels_items = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>']
        pres_rels_items += [
            f'<Relationship Id="rId{i+10}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i+1}.xml"/>'
            for i in range(n)
        ]
        presentation_rels = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {"".join(pres_rels_items)}
</Relationships>'''

        theme_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Portfolio">
  <a:themeElements>
    <a:clrScheme name="Portfolio">
      <a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>
      <a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>
      <a:dk2><a:srgbClr val="1E2761"/></a:dk2>
      <a:lt2><a:srgbClr val="CADCFC"/></a:lt2>
      <a:accent1><a:srgbClr val="1E2761"/></a:accent1>
      <a:accent2><a:srgbClr val="CADCFC"/></a:accent2>
      <a:accent3><a:srgbClr val="FFFFFF"/></a:accent3>
      <a:accent4><a:srgbClr val="52514E"/></a:accent4>
      <a:accent5><a:srgbClr val="0CA30C"/></a:accent5>
      <a:accent6><a:srgbClr val="D03B3B"/></a:accent6>
      <a:hlink><a:srgbClr val="1E2761"/></a:hlink>
      <a:folHlink><a:srgbClr val="CADCFC"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="Portfolio">
      <a:majorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>
      <a:minorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>
    </a:fontScheme>
    <a:fmtScheme name="Portfolio">
      <a:fillStyleLst>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
      </a:fillStyleLst>
      <a:lnStyleLst>
        <a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
        <a:ln w="12700"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
        <a:ln w="19050"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
      </a:lnStyleLst>
      <a:effectStyleLst>
        <a:effectStyle><a:effectLst/></a:effectStyle>
        <a:effectStyle><a:effectLst/></a:effectStyle>
        <a:effectStyle><a:effectLst/></a:effectStyle>
      </a:effectStyleLst>
      <a:bgFillStyleLst>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
      </a:bgFillStyleLst>
    </a:fmtScheme>
  </a:themeElements>
</a:theme>'''

        slide_master_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
             xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
             xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
    </p:spTree>
  </p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
</p:sldMaster>'''

        slide_master_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>'''

        slide_layout_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
             xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
             xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
  <p:cSld name="Blank">
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>'''

        slide_layout_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>'''

        slide_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>'''

        core_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                    xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/"
                    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Portfolio Projects</dc:title>
  <dc:creator>Portfolio</dc:creator>
</cp:coreProperties>'''

        app_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
            xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>python-stdlib-pptx-builder</Application>
  <Slides>{n}</Slides>
</Properties>'''

        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", content_types)
            z.writestr("_rels/.rels", root_rels)
            z.writestr("ppt/presentation.xml", presentation_xml)
            z.writestr("ppt/_rels/presentation.xml.rels", presentation_rels)
            z.writestr("ppt/theme/theme1.xml", theme_xml)
            z.writestr("ppt/slideMasters/slideMaster1.xml", slide_master_xml)
            z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", slide_master_rels)
            z.writestr("ppt/slideLayouts/slideLayout1.xml", slide_layout_xml)
            z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", slide_layout_rels)
            z.writestr("docProps/core.xml", core_xml)
            z.writestr("docProps/app.xml", app_xml)
            for i, slide in enumerate(self.slides):
                z.writestr(f"ppt/slides/slide{i+1}.xml", slide.to_xml())
                z.writestr(f"ppt/slides/_rels/slide{i+1}.xml.rels", slide_rels)
