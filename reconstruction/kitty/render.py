"""Binary orthographic occupancy and a deterministic Cyrillic Ш printer tile."""
import math
from PIL import Image, ImageDraw
from .geometry import apply, yaw, hull

WIDTH, HEIGHT = 960,600


def projected(solids, angle=18, width=WIDTH, height=HEIGHT, shift=0., span=5.2):
    rotation = yaw(math.radians(angle))
    scale = width/span
    result = []
    for name, vertices in solids:
        p = [apply(rotation,v) for v in vertices]
        result.append((name,hull([(width/2+(v[1]+shift)*scale,height*.82-v[2]*scale) for v in p])))
    return result


def render(solids, mode='paper', angle=18, shift=0., span=5.2):
    size = (WIDTH,HEIGHT) if mode=='silhouette' else (160,100)
    mask = Image.new('L',size,0)
    draw = ImageDraw.Draw(mask)
    for name, polygon in projected(solids,angle,*size,shift,span):
        if len(polygon)>=3:draw.polygon(polygon,fill=255)
    if mode=='silhouette':return Image.eval(mask,lambda p:255-p).convert('RGB')
    result = Image.new('RGB',(WIDTH,HEIGHT),'#f5f1e7')
    draw = ImageDraw.Draw(result)
    for y in range(100):
        for x in range(160):
            inside = mask.getpixel((x,y))>0
            if inside == (mode=='ink'):
                # A 5x5 raster Ш in a 6x6 character cell. No tonal shading.
                xx, yy = 6*x,6*y
                for dx in (0,2,4):draw.line((xx+dx,yy,xx+dx,yy+4),fill='#343731')
                draw.line((xx,yy+4,xx+4,yy+4),fill='#343731')
    return result
