"""Extract a bounded long-side band; never rotate the whole product as a border."""
from math import hypot

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter


class BorderSelectionRequired(ValueError):
    failure_type = 'border_selection_required'

    def __init__(self,message):
        super().__init__(message)
        self.diagnostics={'kind':self.failure_type,'message':message,
                          'action':'Select the actual side-border region in the optional Saree border crop field.'}


def _candidates(sample, right=False):
    pixels=np.asarray(sample,dtype=np.float32)
    height,width=pixels.shape[:2]
    smooth=gaussian_filter(pixels,(1.2,1.2,0))
    edges=np.linalg.norm(np.diff(smooth,axis=1),axis=2)
    edges=np.pad(edges,((0,0),(0,1)))
    ys=np.linspace(.12*height,.61*height,70).astype(int)
    middle=float(ys.mean())
    anchors=np.arange(round((.57 if right else .04)*width),round((.96 if right else .43)*width))
    if len(anchors)==0:
        return [],middle,0
    candidates=[]
    for slope in np.linspace(-.6,.6,61):
        xs=np.rint(anchors[None,:]+slope*(ys[:,None]-middle)).astype(int)
        valid=(xs>=1)&(xs<width-1)
        values=edges[ys[:,None],np.clip(xs,0,width-1)]
        scores=(.5*np.percentile(values,25,axis=0)+.5*np.minimum(values,45).mean(axis=0))*valid.mean(axis=0)
        for index in np.argsort(scores)[-12:]:
            if valid[:,index].mean()>.95:
                candidates.append((float(scores[index]),float(anchors[index]),float(slope)))
    floor=max(7,float(np.median(edges[:,anchors]))*2.5)
    return sorted(candidates,reverse=True),middle,floor


def _auto_quad(image):
    sample=image.copy();sample.thumbnail((512,640))
    width,height=sample.size
    for minimum_gap,right in ((.055,False),(.055,True),(.025,False),(.025,True)):
        lines,middle,floor=_candidates(sample,right)
        if not lines or lines[0][0]<floor:
            continue
        outer=lines[0]
        inner=[]
        for line in lines:
            gap=(outer[1]-line[1]) if right else (line[1]-outer[1])
            if minimum_gap*width<=gap<=.18*width and abs(line[2]-outer[2])<=.20 and line[0]>=floor*.5:
                inner.append(line)
        if not inner:
            continue
        inside=max(inner)
        top,bottom=.18*height,.58*height
        def x(line,y):return line[1]+line[2]*(y-middle)
        first,last=(inside,outer) if right else (outer,inside)
        quad=[(x(first,top)+1,top),(x(first,bottom)+1,bottom),
              (x(last,bottom)-1,bottom),(x(last,top)-1,top)]
        if min(quad[3][0]-quad[0][0],quad[2][0]-quad[1][0])<3:
            continue
        if any(not (0<=a<width and 0<=b<height) for a,b in quad):
            continue
        scale_x,scale_y=image.width/width,image.height/height
        return [(a*scale_x,b*scale_y) for a,b in quad],{
            'selection':'detected_long_edge_pair','outer_score':round(outer[0],3),
            'inner_score':round(inside[0],3),'side':'right' if right else 'left'}
    return None,None


def _rectify(image,quad):
    width=max(2,round((hypot(quad[3][0]-quad[0][0],quad[3][1]-quad[0][1])+
                       hypot(quad[2][0]-quad[1][0],quad[2][1]-quad[1][1]))/2))
    height=max(2,round((hypot(quad[1][0]-quad[0][0],quad[1][1]-quad[0][1])+
                        hypot(quad[2][0]-quad[3][0],quad[2][1]-quad[3][1]))/2))
    return image.transform((width,height),Image.Transform.QUAD,
        tuple(value for point in quad for value in point),resample=Image.Resampling.BICUBIC)


def extract_band(image,options):
    box=options.get('fabric_border_crop_box')
    if box is not None:
        if (not isinstance(box,(list,tuple)) or len(box)!=4 or
            any(type(value) is not int for value in box) or
            not 0<=box[0]<box[2]<=image.width or not 0<=box[1]<box[3]<=image.height):
            raise BorderSelectionRequired('The selected border crop must be inside the source photograph.')
        strip=image.crop(box)
        if strip.width>strip.height:
            strip=strip.transpose(Image.Transpose.ROTATE_90)
        return strip,{'selection':'explicit_crop','source_crop_box':list(box)}
    rotated=image.width>image.height
    original_width=image.width
    oriented=image.transpose(Image.Transpose.ROTATE_90) if rotated else image
    quad,metadata=_auto_quad(oriented)
    if quad is None:
        # A plain swatch cannot supply unseen ornament. Show only a plain source
        # edge, explicitly marked, instead of pretending a design was extracted.
        sample=oriented.copy();sample.thumbnail((128,128))
        if float(np.std(np.asarray(sample,dtype=np.float32),axis=(0,1)).max())<3:
            width=min(oriented.width,max(1,round(oriented.width*.12)))
            return oriented.crop((0,0,width,oriented.height)),{'selection':'plain_source_edge'}
        raise BorderSelectionRequired('Select the real long-side border with fabric_border_crop_box.')
    strip=_rectify(oriented,quad)
    original_quad=[(original_width-1-y,x) for x,y in quad] if rotated else quad
    return strip,{**metadata,'source_quad':[[round(x,3),round(y,3)] for x,y in original_quad]}


def render_band(strip,size):
    """Only extracted-band pixels enter this diagonal detail photograph."""
    length=hypot(size[0]-1,size[1]-1)
    desired_width=.46*min(size)
    wanted_height=max(strip.width*length/desired_width,length/4)
    if strip.height>wanted_height:
        top=round((strip.height-wanted_height)/2)
        strip=strip.crop((0,top,strip.width,min(strip.height,top+round(wanted_height))))
    width,height=size[0]-1,size[1]-1
    scale=length/max(1,strip.height-1)
    denominator=length*scale
    matrix=(height/denominator,-width/denominator,(strip.width-1)/2,
            width/denominator,height/denominator,0)
    return strip.transform(size,Image.Transform.AFFINE,matrix,
        resample=Image.Resampling.BICUBIC,fillcolor=(235,235,235))
