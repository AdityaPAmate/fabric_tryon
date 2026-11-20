"""Extract a bounded long-side band; never rotate the whole product as a border."""
from math import hypot

import numpy as np
from PIL import Image,ImageDraw
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
    sample=image.copy();sample.thumbnail((768,960))
    width,height=sample.size
    cached={side:_candidates(sample,side) for side in (False,True)}
    # A tightly photographed saree can end at the image edge: its strongest
    # visible line is then the INNER trim boundary, not the outer cloth edge.
    pixels=np.asarray(sample,dtype=np.float32)
    rows=slice(round(.18*height),round(.58*height))
    body=np.median(pixels[rows,round(.4*width):round(.6*width)].reshape(-1,3),axis=0)
    for right in (False,True):
        lines,middle,floor=cached[right]
        for line in lines[:12]:
            score,anchor,slope=line
            if score<floor or (anchor<.82*width if right else anchor>.18*width):
                continue
            ys=np.arange(rows.start,rows.stop)
            boundary=np.rint(anchor+slope*(ys-middle)).astype(int)
            outside=[];inside=[]
            for y,x in zip(ys,boundary):
                if not 4<x<width-4:continue
                outer=pixels[y,x+2:width] if right else pixels[y,0:x-1]
                inner=pixels[y,max(0,x-25):x-2] if right else pixels[y,x+2:min(width,x+25)]
                if len(outer) and len(inner):outside.append(np.median(outer,axis=0));inside.append(np.median(inner,axis=0))
            if not outside:continue
            outer=np.median(outside,axis=0);inner=np.median(inside,axis=0)
            # Reject a neutral floor/background strip. A real clipped trim
            # differs from the body while its inward neighbour resembles it.
            if np.ptp(outer)<25 or np.linalg.norm(outer-body)<45 or np.linalg.norm(inner-body)+25>=np.linalg.norm(outer-body):
                continue
            top,bottom=.18*height,.58*height
            x0=anchor+slope*(top-middle);x1=anchor+slope*(bottom-middle)
            quad=([(x0+1,top),(x1+1,bottom),(width-1,bottom),(width-1,top)] if right else
                  [(1,top),(1,bottom),(x1-1,bottom),(x0-1,top)])
            sx,sy=image.width/width,image.height/height
            return [(x*sx,y*sy) for x,y in quad],{'selection':'detected_edge_touching_band',
                'inner_score':round(score,3),'side':'right' if right else 'left'}
    for minimum_gap,right in ((.055,False),(.055,True),(.025,False),(.025,True)):
        lines,middle,floor=cached[right]
        if not lines or lines[0][0]<floor:
            continue
        outer=lines[0]
        inner=[]
        for line in lines:
            gap=(outer[1]-line[1]) if right else (line[1]-outer[1])
            if minimum_gap*width<=gap<=.18*width and abs(line[2]-outer[2])<=.20 and line[0]>=floor*.5:
                slope_gap=outer[2]-line[2] if right else line[2]-outer[2]
                ends=[gap+slope_gap*(y-middle) for y in (.18*height,.58*height)]
                # Reject crossing/nearly collapsed bands. Rectifying those would
                # stretch a few source pixels into a broad, blurred wedge.
                if min(ends)>=3 and max(ends)/min(ends)<=2.5:
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


def _rotation(options,side):
    value=options.get('fabric_border_rotation','auto')
    if value=='auto':return 180 if side=='right' else 0
    if type(value) is int and value in (0,180):return value
    raise BorderSelectionRequired('Border orientation must be auto, 0 or 180.')


def extract_band(image,options):
    box=options.get('fabric_border_crop_box')
    if box is not None:
        if (not isinstance(box,(list,tuple)) or len(box)!=4 or
            any(type(value) is not int for value in box) or
            not 0<=box[0]<box[2]<=image.width or not 0<=box[1]<box[3]<=image.height):
            raise BorderSelectionRequired('The selected border crop must be inside the source photograph.')
        strip=image.crop(box)
        side='right' if (box[1]+box[3]>image.height if strip.width>strip.height else box[0]+box[2]>image.width) else 'left'
        if strip.width>strip.height:
            strip=strip.transpose(Image.Transpose.ROTATE_90)
        rotation=_rotation(options,side)
        if rotation:strip=strip.transpose(Image.Transpose.ROTATE_180)
        return strip,{'selection':'explicit_crop','source_crop_box':list(box),
                      'side':side,'orientation_rotation':rotation}
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
    rotation=_rotation(options,metadata['side'])
    if rotation:strip=strip.transpose(Image.Transpose.ROTATE_180)
    original_quad=[(original_width-1-y,x) for x,y in quad] if rotated else quad
    return strip,{**metadata,'source_quad':[[round(x,3),round(y,3)] for x,y in original_quad],
                  'orientation_rotation':rotation}


def render_band(strip,size):
    """Only extracted-band pixels enter this diagonal detail photograph."""
    length=hypot(size[0]-1,size[1]-1)
    desired_width=.65*min(size)
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


def render_from_source(image,strip,metadata,size):
    """Compose rectification and diagonal placement, sampling original pixels once."""
    quad=metadata.get('source_quad')
    if quad is None:
        box=metadata.get('source_crop_box')
        if not box:return render_band(strip,size)
        left,top,right,bottom=box
        quad=[(left,top),(left,bottom-1),(right-1,bottom-1),(right-1,top)]
        if right-left>bottom-top:
            quad=[quad[3],quad[0],quad[1],quad[2]]
    quad=np.asarray(quad,dtype=float)
    if metadata.get('orientation_rotation')==180:quad=quad[[2,3,0,1]]
    native_width=(np.linalg.norm(quad[3]-quad[0])+np.linalg.norm(quad[2]-quad[1]))/2
    native_height=(np.linalg.norm(quad[1]-quad[0])+np.linalg.norm(quad[2]-quad[3]))/2
    if min(native_width,native_height)<1:return render_band(strip,size)
    width,height=size[0]-1,size[1]-1
    length=hypot(width,height)
    scale=max(length/native_height,min(4,.65*min(size)/native_width))
    fraction=min(1,length/(scale*native_height));start=(1-fraction)/2;end=1-start
    source=np.array([quad[0]*(1-start)+quad[1]*start,quad[0]*(1-end)+quad[1]*end,
                     quad[3]*(1-end)+quad[2]*end,quad[3]*(1-start)+quad[2]*start])
    normal=np.array([height,-width])/length*native_width*scale/2
    target=np.array([-normal,np.array([width,height])-normal,
                     np.array([width,height])+normal,normal])
    equations=[];values=[]
    for (u,v),(x,y) in zip(target,source):
        equations.extend([[u,v,1,0,0,0,-u*x,-v*x],[0,0,0,u,v,1,-u*y,-v*y]])
        values.extend([x,y])
    coefficients=np.linalg.solve(np.asarray(equations),np.asarray(values))
    rendered=image.transform(size,Image.Transform.PERSPECTIVE,tuple(coefficients),
                              resample=Image.Resampling.BICUBIC)
    # Antialias only the mask at final size; LANCZOS is supported by resize,
    # unlike Pillow's affine/perspective transform calls.
    mask=Image.new('L',(size[0]*2,size[1]*2),0)
    ImageDraw.Draw(mask).polygon([tuple(point*2) for point in target],fill=255)
    mask=mask.resize(size,Image.Resampling.LANCZOS)
    metadata.update(native_strip_size=[round(native_width),round(native_height)],
                    source_sampling_passes=1,display_scale=round(scale,3),
                    display_segment=[round(float(start),5),round(float(end),5)])
    return Image.composite(rendered,Image.new('RGB',size,(235,235,235)),mask)
