"""Rebuild the deterministic 27-frame rocket animation. Pillow, numpy, scipy required."""
from pathlib import Path
import json, math, hashlib, zipfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
SIZE, SS, FPS = 512, 3, 24
HI = SIZE * SS
LANCZOS = Image.Resampling.LANCZOS

def smooth(t):
    t = np.clip(t, 0, 1)
    return t*t*(3-2*t)

def clean_master(source):
    im = Image.open(source).convert('RGBA')
    a = np.array(im)
    mask = a[:,:,3] > 180
    labels, n = ndi.label(mask)
    counts = np.bincount(labels.ravel()); counts[0] = 0
    mask = labels == counts.argmax()
    mask = ndi.binary_opening(mask, iterations=4)
    mask = ndi.binary_closing(mask, iterations=5)
    mask = ndi.binary_fill_holes(mask)
    mask = ndi.binary_erosion(mask, iterations=1)
    alpha = np.round(ndi.gaussian_filter(mask.astype(float), 0.95)*255).astype(np.uint8)
    alpha[alpha < 2] = 0
    # Extend nearby solid sprite colors through the antialiased perimeter.
    core = mask & (a[:,:,3] >= 245)
    _, indices = ndi.distance_transform_edt(~core, return_indices=True)
    edge = (alpha > 0) & ~core
    a[edge,:3] = a[indices[0][edge], indices[1][edge], :3]
    a[:,:,3] = alpha; a[alpha == 0,:3] = 0
    ys,xs = np.where(alpha > 0)
    bottom = ys.max()+1; top = ys.min()
    nozzle = alpha[max(top,bottom-26):bottom].astype(float)
    axis = int(round((nozzle.sum(0)*np.arange(alpha.shape[1])).sum()/nozzle.sum()))
    halfwidth = max(axis-xs.min(), xs.max()-axis)+1
    result = Image.fromarray(a).crop((axis-halfwidth, top, axis+halfwidth, bottom))
    result.save(ROOT/'source/rocket_master.png')
    return result

def place(canvas, sprite, cx, cy, height, opacity=1):
    h = max(1,round(height*SS)); w = max(1,round(h*sprite.width/sprite.height))
    resized = sprite.resize((w,h), LANCZOS)
    if opacity != 1:
        resized.putalpha(resized.getchannel('A').point(lambda v: round(v*opacity)))
    canvas.alpha_composite(resized, (round(cx*SS-w/2), round(cy*SS-h/2)))

def glow(canvas, cx, cy, rx, ry, power):
    if power <= 0: return
    w,h = max(2,int(rx*SS*6)), max(2,int(ry*SS*6))
    y,x = np.mgrid[0:h,0:w]
    d = ((x-w/2)/(rx*SS))**2 + ((y-h/2)/(ry*SS))**2
    alpha = np.exp(-d*1.6)*power*255
    arr = np.zeros((h,w,4),dtype=np.uint8)
    arr[:,:,:3]=(255,135,28); arr[:,:,3] = np.clip(alpha,0,255).astype(np.uint8)
    canvas.alpha_composite(Image.fromarray(arr),(round(cx*SS-w/2),round(cy*SS-h/2)))

def flame(canvas, x, y, length, width, intensity, frame):
    if length <= 0 or intensity <= 0: return
    pad=12
    w = int((width*2.5+pad*2)*SS); h = int((length+pad*2)*SS)
    yy,xx=np.mgrid[0:h,0:w]
    v=(yy/SS-pad)/length
    t=np.clip(v,0,1)
    profile=(0.68+0.58*np.sin(np.pi*t))*np.power(1-t,0.72)
    profile *= 1+0.035*np.sin(16*t-frame*.55)*np.sin(np.pi*t)
    radius = np.maximum(.03,profile*width*.5)
    distance=np.abs(xx/SS-w/SS/2)/radius
    coverage=np.clip((1-distance)*radius*SS+.5,0,1)
    coverage *= np.clip(v*length*SS+1,0,1)*(v<1)
    heat=np.clip((1-distance)*1.35,0,1)*(1-.65*t)
    stops=np.array([0,.25,.6,1.0])
    colors=np.array([[255,67,7],[255,128,8],[255,212,37],[255,253,193]])
    arr=np.zeros((h,w,4),dtype=np.uint8)
    for c in range(3): arr[:,:,c]=np.interp(heat,stops,colors[:,c]).astype(np.uint8)
    arr[:,:,3]=np.clip(coverage*255*intensity,0,255).astype(np.uint8)
    layer=Image.fromarray(arr)
    halo=layer.copy(); halo.putalpha(halo.getchannel('A').point(lambda a:int(a*.28)))
    halo=halo.filter(ImageFilter.GaussianBlur(3.5*SS))
    at=(round(x*SS-w/2),round((y-pad)*SS))
    canvas.alpha_composite(halo,at); canvas.alpha_composite(layer,at)
    # A smaller ivory-yellow inner jet gives the flame depth.
    core=np.clip((1-np.abs(xx/SS-w/SS/2)/(radius*.40))*radius*SS+.5,0,1)
    core*=np.clip((.68-v)*length*SS,0,1)*np.clip(v*length*SS+1,0,1)
    core*=np.clip(1-t/.72,0,1)*.85*intensity
    arr[:,:,:3]=[255,255,213];arr[:,:,3]=(core*255).astype(np.uint8)
    canvas.alpha_composite(Image.fromarray(arr),at)

def cloud_sprite():
    w,h=320,230
    yy,xx=np.mgrid[0:h,0:w]; x=(xx-w/2)/w; y=(yy-h/2)/w
    lobes=[(-.24,.05,.16),(-.12,-.035,.20),(.025,-.10,.205),(.19,-.035,.17),(.29,.065,.13),(.065,.10,.20)]
    d=np.stack([np.sqrt((x-cx)**2+(y-cy)**2)-r for cx,cy,r in lobes])
    # Smooth union keeps soft dimensional lobes without hard circles.
    k=48; field=-np.log(np.exp(-k*d).sum(axis=0))/k
    alpha=np.clip(-field*w+.5,0,1)
    gy,gx=np.gradient(field)
    light=np.clip(.60-gx*110-gy*170+(1-y)*.08,0,1)
    edge=np.clip(-field/.075,0,1)
    arr=np.zeros((h,w,4),dtype=np.uint8)
    dark=np.array([100,111,143]); bright=np.array([232,235,248])
    shade=np.clip(.23+.62*light+.09*edge,0,1)
    arr[:,:,:3]=(dark+(bright-dark)*shade[:,:,None]).astype(np.uint8)
    arr[:,:,3]=(alpha*255).astype(np.uint8)
    return Image.fromarray(arr)

def transform(f):
    height=236+38*smooth(f/8)
    if f <= 8: lift=0.
    elif f <= 17: lift=14*((f-8)/9)**3
    else:
        t=f-17
        lift=14+(42/9)*t+7.5*t*t
    return float(height), float(256-lift)

def render(master,cloud,f):
    canvas=Image.new('RGBA',(HI,HI))
    height,cy=transform(f); nozzle=cy+height/2-5
    # Persistent, symmetric smoke particles remain at the launch region.
    fade=1-smooth((f-21)/6)
    for birth in [11.5,13,14.5,16,17.5,19]:
        age=f-birth
        if age < 0: continue
        opacity=float(smooth(age/2)*fade*.53)
        for sign in [-1,1]:
            cx=256+sign*(12+age*5.2)
            py=432+age*.25+math.sin(birth)*5
            ph=17+min(age,11)*5.0
            place(canvas,cloud,cx,py,ph,opacity)
    if f>=18:
        for birth in [18,19.5,21,22.5]:
            age=f-birth
            if age<0: continue
            bh,by=transform(birth)
            py=by+bh/2+50+age*3
            opacity=float(smooth(age/1.5)*(1-smooth((f-22)/5))*.26)
            for sign in [-1,1]:
                place(canvas,cloud,256+sign*(8+age*3),py,14+age*4,opacity)
    charge=float(smooth(f/8))
    if f <= 8:
        glow(canvas,256,nozzle+1,19,10,.21*charge)
        length=0.
    else:
        ignition=float(smooth((f-8)/9))
        length=7+88*ignition if f<=17 else 95+8*(f-17)
        strength=float((.55+.45*ignition)*(1-smooth((f-23)/3)))
        glow(canvas,256,nozzle+13,25+ignition*7,16+ignition*9,.32*strength)
        flame(canvas,256,nozzle,length,54+8*ignition,strength,f)
    # A tiny shutter trail softens the fast exit without changing the artwork.
    if f>=20 and f<=24:
        th,ty=transform(f-.14)
        place(canvas,master,256,ty,th,.08)
    place(canvas,master,256,cy,height)
    canvas=canvas.resize((SIZE,SIZE),LANCZOS)
    arr=np.array(canvas);arr[arr[:,:,3]==0,:3]=0
    return Image.fromarray(arr),{'index':f+1,'rocketCenterX':256,'rocketCenterY':round(cy,6),'rocketHeight':round(height,6),'rotation':0,'flameLength':round(length,3),'rocketVisible':cy+height/2>0}

def atlas_json():
    frames={}
    for f in range(27):
        frames[f'rocket_{f+1:02}.png']={'frame':{'x':(f%9)*512,'y':(f//9)*512,'w':512,'h':512},'rotated':False,'trimmed':False,'spriteSourceSize':{'x':0,'y':0,'w':512,'h':512},'sourceSize':{'w':512,'h':512},'pivot':{'x':.5,'y':.5}}
    return {'frames':frames,'animations':{'rocket_launch':list(frames)},'meta':{'app':'Deterministic single-master animation','version':'1.0','image':'rocket_atlas_9x3.png','format':'RGBA8888','size':{'w':4608,'h':1536},'scale':'1','frameRate':FPS}}

def main():
    for p in ['frames','sheets','source','preview']: (ROOT/p).mkdir(exist_ok=True)
    source=ROOT/'source/rocket_master.png'
    master=Image.open(source).convert('RGBA') if source.exists() else clean_master(ROOT/'source/generated_master_original.png')
    cloud=cloud_sprite(); frames=[]; motion=[]
    for f in range(27):
        im,record=render(master,cloud,f); im.save(ROOT/f'frames/rocket_{f+1:02}.png',compress_level=9)
        frames.append(im);motion.append(record)
        print(f'Rendered {f+1:02}/27',flush=True)
    atlas=Image.new('RGBA',(4608,1536))
    for i,im in enumerate(frames): atlas.paste(im,((i%9)*512,(i//9)*512))
    atlas.save(ROOT/'rocket_atlas_9x3.png',compress_level=9)
    for part in range(3):
        sheet=Image.new('RGBA',(1536,1536))
        for i in range(9): sheet.paste(frames[part*9+i],((i%3)*512,(i//3)*512))
        sheet.save(ROOT/f'sheets/rocket_sheet_{part+1:02}_frames_{part*9+1:02}-{part*9+9:02}.png',compress_level=9)
    (ROOT/'rocket_atlas_9x3.json').write_text(json.dumps(atlas_json(),indent=2))
    (ROOT/'source/motion.json').write_text(json.dumps({'fps':FPS,'durationMs':1125,'frames':motion},indent=2))
    durations=[42,41,42]*9
    frames[0].save(ROOT/'preview/rocket_launch.apng',save_all=True,append_images=frames[1:],duration=durations,loop=0,disposal=0,blend=0)
    frames[0].save(ROOT/'preview/rocket_launch.webp',save_all=True,append_images=frames[1:],duration=durations,loop=0,lossless=True,method=6)
    # Review-only colored backgrounds; these are never in production sprites.
    review=[]
    for im in frames:
        row=Image.new('RGB',(768,384),(7,12,22))
        for side,color in enumerate([(7,12,22),(80,25,128)]):
            tile=Image.new('RGBA',(384,384),color+(255,));tile.alpha_composite(im.resize((384,384),LANCZOS));row.paste(tile,(side*384,0))
        review.append(row)
    review[0].save(ROOT/'preview/rocket_on_dark_and_purple.gif',save_all=True,append_images=review[1:],duration=[40]*27,loop=0,disposal=2)
    contact=Image.new('RGB',(9*200,3*218),(13,18,32));draw=ImageDraw.Draw(contact)
    for i,im in enumerate(frames):
        x,y=(i%9)*200,(i//9)*218
        contact.paste(im.resize((196,196),LANCZOS),(x+2,y+20),im.resize((196,196),LANCZOS))
        draw.text((x+8,y+4),f'{i+1:02}',fill=(160,175,200))
    contact.save(ROOT.parent/'qa/contact_sheet.jpg',quality=95)
    cloud.save(ROOT.parent/'qa/smoke_reference.png')
    print('Exports complete',flush=True)

if __name__=='__main__': main()
