"""Image quality checks: WCAG contrast, CIEDE2000 palette distance, OCR boxes.
Logo verification remains human-review unless a configured reference image is available.
"""
from __future__ import annotations
from pathlib import Path
import math


def hex_rgb(value: str):
    value=value.strip().lstrip('#')
    if len(value)==3: value=''.join(ch*2 for ch in value)
    if len(value)!=6: raise ValueError('Expected #RGB or #RRGGBB')
    return tuple(int(value[i:i+2],16) for i in (0,2,4))

def _srgb_to_linear(v):
    v=v/255
    return v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4

def contrast_ratio(a: str, b: str) -> float:
    def lum(c):
        r,g,bl=[_srgb_to_linear(v) for v in hex_rgb(c)]
        return .2126*r+.7152*g+.0722*bl
    l1,l2=sorted((lum(a),lum(b)),reverse=True)
    return (l1+.05)/(l2+.05)

def _rgb_lab(rgb):
    r,g,b=[_srgb_to_linear(v) for v in rgb]
    x=(r*.4124+g*.3576+b*.1805)/.95047
    y=(r*.2126+g*.7152+b*.0722)/1.00000
    z=(r*.0193+g*.1192+b*.9505)/1.08883
    def f(t): return t**(1/3) if t>0.008856 else 7.787*t+16/116
    fx,fy,fz=f(x),f(y),f(z)
    return (116*fy-16,500*(fx-fy),200*(fy-fz))

def delta_e_2000(hex1: str, hex2: str) -> float:
    # CIEDE2000 implementation (Sharma et al.); Lab values use D65/2-degree conversion above.
    L1,a1,b1=_rgb_lab(hex_rgb(hex1)); L2,a2,b2=_rgb_lab(hex_rgb(hex2))
    C1=math.hypot(a1,b1); C2=math.hypot(a2,b2); Cbar=(C1+C2)/2
    G=.5*(1-math.sqrt(Cbar**7/(Cbar**7+25**7)))
    ap1=(1+G)*a1; ap2=(1+G)*a2
    cp1=math.hypot(ap1,b1); cp2=math.hypot(ap2,b2)
    def hue(a,b):
        h=math.degrees(math.atan2(b,a))
        return h+360 if h<0 else h
    hp1=hue(ap1,b1) if cp1 else 0; hp2=hue(ap2,b2) if cp2 else 0
    dL=L2-L1; dC=cp2-cp1
    if not cp1*cp2: dh=0
    elif abs(hp2-hp1)<=180: dh=hp2-hp1
    elif hp2-hp1>180: dh=hp2-hp1-360
    else: dh=hp2-hp1+360
    dH=2*math.sqrt(cp1*cp2)*math.sin(math.radians(dh/2))
    Lbar=(L1+L2)/2; cpbar=(cp1+cp2)/2
    if not cp1*cp2: hpbar=hp1+hp2
    elif abs(hp1-hp2)<=180: hpbar=(hp1+hp2)/2
    elif hp1+hp2<360: hpbar=(hp1+hp2+360)/2
    else: hpbar=(hp1+hp2-360)/2
    T=1-.17*math.cos(math.radians(hpbar-30))+.24*math.cos(math.radians(2*hpbar))+.32*math.cos(math.radians(3*hpbar+6))-.20*math.cos(math.radians(4*hpbar-63))
    dtheta=30*math.exp(-((hpbar-275)/25)**2)
    Rc=2*math.sqrt(cpbar**7/(cpbar**7+25**7))
    Sl=1+.015*(Lbar-50)**2/math.sqrt(20+(Lbar-50)**2); Sc=1+.045*cpbar; Sh=1+.015*cpbar*T
    Rt=-math.sin(math.radians(2*dtheta))*Rc
    return math.sqrt((dL/Sl)**2+(dC/Sc)**2+(dH/Sh)**2+Rt*(dC/Sc)*(dH/Sh))

def analyze_image(path: Path, palette: list[str] | None = None, logo_reference: Path | None = None) -> dict:
    from PIL import Image, ImageStat
    import pytesseract
    with Image.open(path) as source:
        image=source.convert('RGB')
        width,height=image.size
        thumb=image.copy(); thumb.thumbnail((120,120))
        colors=thumb.getcolors(maxcolors=14400) or []
        colors.sort(reverse=True)
        dominant=['#%02X%02X%02X'%rgb for _,rgb in colors[:8]]
        palette=palette or []
        color_checks=[]
        for color in dominant[:5]:
            if palette:
                nearest=min(palette,key=lambda p:delta_e_2000(color,p))
                distance=delta_e_2000(color,nearest)
                color_checks.append({'observed':color,'nearest_brand_color':nearest,'delta_e_2000':round(distance,2),'status':'pass' if distance<=10 else 'review' if distance<=20 else 'fail'})
        data=pytesseract.image_to_data(image,output_type=pytesseract.Output.DICT,config='--psm 11',timeout=15)
        boxes=[]
        for i,raw in enumerate(data.get('text',[])):
            text=raw.strip()
            if not text: continue
            try: confidence=float(data['conf'][i])
            except (ValueError,TypeError): confidence=-1
            if confidence<0: continue
            boxes.append({'text':text,'confidence':round(confidence/100,3),'x':int(data['left'][i]),'y':int(data['top'][i]),'width':int(data['width'][i]),'height':int(data['height'][i])})
        # Estimate contrast from OCR text boxes against a narrow surrounding border. This is a screen,
        # not a substitute for a human contrast audit because anti-aliasing and mixed backgrounds affect it.
        contrast_checks=[]
        for box in boxes:
            x,y,w,h=box['x'],box['y'],box['width'],box['height']
            if w<2 or h<2: continue
            pad=max(2,min(8,int(min(w,h)*0.12)))
            left=max(0,x-pad); top=max(0,y-pad); right=min(width,x+w+pad); bottom=min(height,y+h+pad)
            border=[]
            for px in range(left,right):
                for py in (top,min(bottom-1,top+h+pad),max(top,y-pad),min(bottom-1,y+h+pad-1)):
                    if 0<=py<height and not (x<=px<x+w and y<=py<y+h): border.append(image.getpixel((px,py)))
            if not border: continue
            bg=tuple(sorted(channel)[len(channel)//2] for channel in zip(*border))
            crop=list(image.crop((x,y,min(width,x+w),min(height,y+h))).getdata())
            if not crop: continue
            luminance=lambda rgb: .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]
            ordered=sorted(crop,key=luminance)
            n=max(1,len(ordered)//5)
            dark=tuple(round(sum(px[c] for px in ordered[:n])/n) for c in range(3))
            light=tuple(round(sum(px[c] for px in ordered[-n:])/n) for c in range(3))
            tohex=lambda rgb:'#%02X%02X%02X'%rgb
            ratios=[contrast_ratio(tohex(bg),tohex(dark)),contrast_ratio(tohex(bg),tohex(light))]
            estimated=max(ratios)
            contrast_checks.append({'text':box['text'],'ratio':round(estimated,2),'status':'pass' if estimated>=4.5 else 'fail','method':'estimated OCR box vs surrounding border'})
        if contrast_checks:
            failed=[c for c in contrast_checks if c['status']=='fail']
            contrast={'status':'fail' if failed else 'pass','minimum_estimated_ratio':min(c['ratio'] for c in contrast_checks),'threshold':4.5,'checks':contrast_checks,'message':'Estimated contrast from OCR boxes and nearby pixels; confirm visually before publication.'}
        else:
            contrast={'status':'needs_human_review','message':'No OCR text boxes were available to estimate contrast. Manual contrast review is required.'}
        logo={'status':'needs_human_review','message':'No configured reference logo image was available for comparison.'}
        if logo_reference and logo_reference.exists():
            with Image.open(logo_reference) as ref:
                ref=ref.convert('RGB').resize((64,64))
                probe=image.copy(); probe.thumbnail((64,64)); probe=probe.resize((64,64))
                import PIL.ImageChops as ImageChops
                diff=ImageStat.Stat(ImageChops.difference(ref,probe)).mean
                score=sum(diff)/3
                logo={'status':'possible_match' if score<18 else 'needs_human_review','mean_rgb_difference':round(score,2),'message':'Pixel comparison is only a rough screen; placement and scale may differ. Human confirmation required.'}
        return {'width':width,'height':height,'dominant_colors':dominant,'palette_checks':color_checks,'ocr_boxes':boxes,'ocr_text':' '.join(b['text'] for b in boxes),'contrast':contrast,'logo_check':logo,'overall_status':'needs_human_review' if not boxes or not palette or logo['status']!='pass' or contrast['status']!='pass' or any(c['status']!='pass' for c in color_checks) else 'review','failure_policy':'Any failed/unavailable image check routes the creative to human review; it never auto-approves.'}
