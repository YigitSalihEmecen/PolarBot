import os
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
FONT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'fonts','CormorantGaramond.ttf')
def wordmark(text,x,y,size,weight=500,tracking=0.12,fill='#141413'):
    """Text as SVG outline paths (no font needed by the viewer). Returns (svg, width)."""
    f=instantiateVariableFont(TTFont(FONT),{'wght':weight})
    gs=f.getGlyphSet(); cmap=f.getBestCmap(); k=size/f['head'].unitsPerEm
    d='';cx=0.0
    for ch in text:
        g=cmap[ord(ch)]; pen=SVGPathPen(gs)
        gs[g].draw(TransformPen(pen,(k,0,0,-k,x+cx,y)))
        d+=pen.getCommands(); cx+=gs[g].width*k+tracking*size
    w=cx-tracking*size
    return f'<path d="{d}" fill="{fill}"/>',w
