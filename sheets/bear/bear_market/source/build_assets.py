"""Single-master bear idle and articulated roar. Python + Pillow + NumPy + SciPy."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi
import numpy as np
import math, io, os, json, hashlib, zipfile

ROOT=Path(__file__).resolve().parents[1]
S=512; SS=2; HI=S*SS; N=27; FPS=24
R=Image.Resampling.LANCZOS

def write_bytes(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.writing');tmp.write_bytes(data);os.replace(tmp,path)

def save(im,path,**kw):
    b=io.BytesIO();im.save(b,format={'.png':'PNG','.apng':'PNG','.gif':'GIF','.jpg':'JPEG'}[Path(path).suffix],**kw)
    write_bytes(path,b.getvalue())

def smooth(t):
    t=np.clip(t,0,1);return t*t*(3-2*t)

def clean(im):
    ar=np.array(im.convert('RGBA'))
    labels,_=ndi.label(ar[:,:,3]>180);counts=np.bincount(labels.ravel());counts[0]=0
    mask=labels==counts.argmax();mask=ndi.binary_opening(mask,iterations=2)
    mask=ndi.binary_closing(mask,iterations=2);mask=ndi.binary_erosion(mask,iterations=1)
    alpha=np.round(ndi.gaussian_filter(mask.astype(float),.8)*255).astype(np.uint8);alpha[alpha<2]=0
    core=mask&(ar[:,:,3]>=245);_,idx=ndi.distance_transform_edt(~core,return_indices=True)
    edge=(alpha>0)&~core;ar[edge,:3]=ar[idx[0][edge],idx[1][edge],:3]
    ar[:,:,3]=alpha;ar[alpha==0,:3]=0
    return Image.fromarray(ar)

class BearRig:
    def __init__(self):
        self.master=Image.open(ROOT/'source/bear_master.png').convert('RGBA')
        self.roar=Image.open(ROOT/'source/bear_roar_keypose.png').convert('RGBA')
        self.box=self.master.getbbox();self.scale=360/(self.box[3]-self.box[1])
        self.ox=256-(615-self.box[0])*self.scale;self.oy=76
        self.width=round((self.box[2]-self.box[0])*self.scale*SS)
        mask=Image.new('L',self.roar.size);d=ImageDraw.Draw(mask)
        d.polygon([(516,267),(545,262),(567,273),(650,273),(682,263),(708,272),(717,405),(690,470),(621,502),(552,477),(510,410)],fill=255)
        mask=mask.filter(ImageFilter.GaussianBlur(6))
        # Only the generated open mouth is used. Eyes, fur, silhouette and body
        # in every frame come from the original master.
        self.patch=self.roar.copy();self.patch.putalpha(mask)
        save(self.patch,ROOT/'source/roar_mouth_layer.png')
        self.patch_ar=np.array(self.patch).astype(np.float32)
        self.patch_ar[:,:,3]/=255;self.patch_ar[:,:,:3]*=self.patch_ar[:,:,3,None]
        self.y,self.x=np.mgrid[0:HI,0:HI].astype(np.float32);self.y/=SS;self.x/=SS
        self.planted=smooth((426-self.y)/65)
        self.head=smooth((230-self.y)/68)
        self.chest=np.exp(-(((self.x-256)/110)**2+((self.y-256)/95)**2))*self.planted
        self.shoulders=np.exp(-(((self.x-256)/145)**2+((self.y-206)/48)**2))
        self.arms=np.exp(-((self.y-323)/71)**2)*(np.exp(-((self.x-112)/37)**2)+np.exp(-((self.x-396)/37)**2))

    def normalize(self,im):
        crop=im.crop(self.box).resize((self.width,360*SS),R)
        out=Image.new('RGBA',(HI,HI));out.alpha_composite(crop,(round(self.ox*SS),round(self.oy*SS)))
        return out

    def mouth(self,opening):
        if opening<=0:return self.normalize(self.master)
        # A piecewise jaw rig preserves upper/lower lip thickness while the
        # cavity opens between them. No whole-character crossfade.
        opening=max(.0001,float(opening))
        x0,x1,y0,y1=490,736,255,510
        yy,xx=np.mgrid[y0:y1,x0:x1].astype(np.float32)
        target=[255,275,295-17*opening,295+140*opening,397+103*opening,510]
        source=[255,263,278,435,500,510]
        srcy=np.interp(yy,target,source).astype(np.float32)
        out=np.stack([ndi.map_coordinates(self.patch_ar[:,:,c],[srcy,xx],order=1,mode='constant',cval=0,prefilter=False) for c in range(4)],axis=-1)
        a=out[:,:,3];valid=a>1e-6;out[valid,:3]/=a[valid,None]
        out[:,:,3]=a*255*smooth(opening/.20)
        patch=Image.fromarray(np.round(np.clip(out,0,255)).astype(np.uint8))
        raw=self.master.copy();raw.alpha_composite(patch,(x0,y0))
        return self.normalize(raw)

    def render(self,kind,f):
        rec=motion(kind,f);base=self.mouth(rec['jawOpen'])
        ar=np.array(base).astype(np.float32);ar[:,:,3]/=255;ar[:,:,:3]*=ar[:,:,3,None]
        x,y=self.x,self.y;b=rec['breath'];c=rec['crouch'];power=rec['roarStrength']
        dx=(x-256)*(.012*b+.035*power)*self.chest
        dx+=(x-256)*.018*power*self.shoulders
        dx+=np.sign(x-256)*(14*power-2*c)*self.arms
        dx+=rec['headSway']*self.head
        dy=(-2.4*b+8*c-13*power)*self.chest
        dy+=(8*c-17*power+rec['roarVibration'])*self.head
        dy+=(-7*power+2*c)*self.arms
        # Local palm flex, with feet fixed to their baseline.
        palms=np.exp(-((y-342)/20)**2)*(np.exp(-((x-115)/24)**2)+np.exp(-((x-398)/24)**2))
        dy-=rec['pawFlex']*palms
        coords=[(y-dy)*SS,(x-dx)*SS]
        out=np.stack([ndi.map_coordinates(ar[:,:,ch],coords,order=1,mode='constant',cval=0,prefilter=False) for ch in range(4)],axis=-1)
        a=out[:,:,3];valid=a>1e-7;out[valid,:3]/=a[valid,None];out[:,:,3]=a*255
        body=Image.fromarray(np.round(np.clip(out,0,255)).astype(np.uint8))
        back,front=effects(f) if kind=='roar' else (Image.new('RGBA',(HI,HI)),Image.new('RGBA',(HI,HI)))
        back.alpha_composite(body);back.alpha_composite(front)
        final=np.array(back.resize((S,S),R));final[:,:,3]=np.round(final[:,:,3].astype(float)*rec['opacity']).astype(np.uint8)
        final[final[:,:,3]==0,:3]=0
        return Image.fromarray(final),rec

def motion(kind,f):
    p=math.tau*f/N
    if kind=='idle':
        return {'frame':f+1,'jawOpen':0.,'breath':math.sin(p),'headSway':.55*math.sin(p),'crouch':0.,'roarStrength':0.,'roarVibration':0.,'pawFlex':1.7*(1-math.cos(p))/2,'opacity':1.}
    crouch=float(smooth(f/6))*(1-float(smooth((f-6)/4)))
    strength=float(smooth((f-6)/5))*(1-float(smooth((f-18)/5)))
    jaw=float(smooth((f-7)/4))*(1-float(smooth((f-18)/4)))
    jaw*=1-.025*math.sin(max(0,f-11)*1.3)**2
    return {'frame':f+1,'jawOpen':jaw,'breath':.35*math.sin(p),'headSway':0.,'crouch':crouch,'roarStrength':strength,'roarVibration':.65*math.sin((f-11)*2.2)*strength,'pawFlex':3*strength,'opacity':1-float(smooth((f-22)/4))}

def cash_note(age,j):
    w,h=19*SS,10*SS;im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im)
    d.rounded_rectangle((1,1,w-2,h-2),radius=2*SS,fill=(73,137,94,255),outline=(183,220,151,255),width=SS)
    d.rectangle((3*SS,2*SS,w-3*SS,h-2*SS),outline=(139,191,121,255),width=SS)
    d.ellipse((w//2-3*SS,2*SS,w//2+3*SS,h-2*SS),fill=(163,206,132,255))
    im=im.rotate((-1 if j%2 else 1)*(j*24+age*13),resample=Image.Resampling.BICUBIC,expand=True)
    a=np.array(im);a[:,:,3]=np.round(a[:,:,3].astype(float)*max(0,1-age/13)**.7).astype(np.uint8)
    return Image.fromarray(a)

def effects(f):
    back=Image.new('RGBA',(HI,HI));front=Image.new('RGBA',(HI,HI))
    age=f-11
    if age<0:return back,front
    # The shockwave has transparent space inside it; no rectangular glow.
    for delay in (0,2):
        t=age-delay
        if 0<=t<=9:
            radius=100+15*t;life=1-float(smooth((t-3)/7))
            ring=Image.new('RGBA',(HI,HI));d=ImageDraw.Draw(ring)
            box=((256-radius)*SS,(250-radius*.77)*SS,(256+radius)*SS,(250+radius*.77)*SS)
            d.ellipse(box,outline=(255,36,53,round(185*life)),width=max(SS,round((7-t*.45)*SS)))
            back.alpha_composite(ring.filter(ImageFilter.GaussianBlur(2.7*SS)))
            d.ellipse(box,outline=(255,91,81,round(180*life)),width=SS)
            back.alpha_composite(ring)
    if 0<=age<13:
        for j in range(8):
            side=-1 if j%2==0 else 1
            x=256+side*(70+age*(9.2+(j%3)*.8))
            y=235+(j//2)*24-age*(6.7-j*.32)+.60*age*age
            im=cash_note(age,j);front.alpha_composite(im,(round(x*SS-im.width/2),round(y*SS-im.height/2)))
    return back,front

def export(kind,frames,records):
    dest=ROOT/kind;dest.mkdir(parents=True,exist_ok=True);names=[];meta={}
    atlas=Image.new('RGBA',(4608,1536))
    for i,im in enumerate(frames):
        name=f'bear_{kind}_{i+1:02}.png';names.append(name);save(im,dest/'frames'/name,compress_level=6)
        x,y=i%9*S,i//9*S;atlas.paste(im,(x,y))
        meta[name]={'frame':{'x':x,'y':y,'w':S,'h':S},'rotated':False,'trimmed':False,'spriteSourceSize':{'x':0,'y':0,'w':S,'h':S},'sourceSize':{'w':S,'h':S},'pivot':{'x':.5,'y':.5}}
    save(atlas,dest/f'bear_{kind}_atlas_9x3.png',compress_level=6)
    for k in range(3):
        sheet=Image.new('RGBA',(1536,1536))
        for j in range(9):sheet.paste(frames[k*9+j],(j%3*S,j//3*S))
        save(sheet,dest/f'sheets/bear_{kind}_sheet_{k+1:02}.png',compress_level=6)
    (dest/f'bear_{kind}_atlas_9x3.json').write_text(json.dumps({'frames':meta,'animations':{f'bear_{kind}':names},'meta':{'image':f'bear_{kind}_atlas_9x3.png','format':'RGBA8888','size':{'w':4608,'h':1536},'scale':'1','frameRate':FPS,'loop':kind=='idle'}},indent=2))
    (dest/'motion.json').write_text(json.dumps({'fps':FPS,'durationMs':1125,'loop':kind=='idle','frames':records},indent=2))
    save(frames[0],dest/f'bear_{kind}.apng',save_all=True,append_images=frames[1:],duration=[42,41,42]*9,loop=0 if kind=='idle' else 1,blend=0,disposal=0)

def validate(kind,frames):
    dest=ROOT/kind;atlas=Image.open(dest/f'bear_{kind}_atlas_9x3.png');assert atlas.size==(4608,1536) and atlas.mode=='RGBA'
    apng=Image.open(dest/f'bear_{kind}.apng');assert apng.n_frames==N
    rows=[];duration=0
    for i,ref in enumerate(frames):
        im=Image.open(dest/f'frames/bear_{kind}_{i+1:02}.png');a=np.array(im)
        assert im.mode=='RGBA' and im.size==(S,S) and np.array_equal(a,np.array(ref))
        alpha=a[:,:,3];assert alpha.min()==0
        assert not np.any(a[alpha==0,:3]);assert not np.any(alpha[[0,-1],:]) and not np.any(alpha[:,[0,-1]])
        if kind=='idle' or i<26:assert alpha.max()>0 and np.any((alpha>0)&(alpha<255))
        x,y=i%9*S,i//9*S;assert np.array_equal(np.array(atlas.crop((x,y,x+S,y+S))),a)
        sheet=Image.open(dest/f'sheets/bear_{kind}_sheet_{i//9+1:02}.png');assert sheet.size==(1536,1536) and sheet.mode=='RGBA'
        j=i%9;x,y=j%3*S,j//3*S;assert np.array_equal(np.array(sheet.crop((x,y,x+S,y+S))),a)
        apng.seek(i);duration+=apng.info['duration'];assert np.array_equal(np.array(apng.convert('RGBA')),a)
        rows.append({'frame':i+1,'bounds':im.getbbox(),'transparentPixels':int((alpha==0).sum()),'partialAlphaPixels':int(((alpha>0)&(alpha<255)).sum())})
    assert duration==1125 and len({hashlib.sha256(np.array(f).tobytes()).hexdigest() for f in frames})==N
    if kind=='roar':assert not np.any(np.array(frames[-1]))
    return {'passed':True,'frames':N,'frameSize':[512,512],'atlasSize':[4608,1536],'smallSheets':3,'alphaVerified':True,'noEdgeClipping':True,'pixelExactAtlasesSheetsAPNG':True,'finalFrameBlank':kind=='roar','durationMs':duration,'perFrame':rows}

def previews(allframes):
    seq=allframes['idle']+allframes['roar'];out=[]
    for im in seq:
        row=Image.new('RGB',(800,400))
        for j,color in enumerate(['#0a0e19','#472067']):
            tile=Image.new('RGBA',(400,400),color);tile.alpha_composite(im.resize((400,400),R));row.paste(tile,(j*400,0))
        out.append(row)
    save(out[0],ROOT/'preview/bear_idle_then_roar.gif',save_all=True,append_images=out[1:],duration=[50]*27+[60]*26+[650],loop=0,disposal=2)
    for kind,frames in allframes.items():
        contact=Image.new('RGB',(1350,510),'#0a0e19');d=ImageDraw.Draw(contact)
        for i,im in enumerate(frames):
            x,y=i%9*150,i//9*170;thumb=im.resize((150,150),R);contact.paste(thumb,(x,y+20),thumb);d.text((x+6,y+4),f'{i+1:02}',fill='#bcc6d5')
        save(contact,ROOT.parent/f'qa/bear_{kind}_contact.jpg',quality=94)

def main():
    rig=BearRig();allframes={};report={}
    save(rig.normalize(rig.master).resize((S,S),R),ROOT/'source/bear_neutral_512.png')
    for kind in ('idle','roar'):
        frames=[];records=[]
        for f in range(N):
            im,rec=rig.render(kind,f);frames.append(im);records.append(rec)
        allframes[kind]=frames;export(kind,frames,records);report[kind]=validate(kind,frames)
        print(f'{kind}: all 27 frames, atlases, sheets and APNG verified',flush=True)
    assert np.array_equal(np.array(allframes['idle'][0]),np.array(allframes['roar'][0]))
    wrapped,_=rig.render('idle',27);assert np.array_equal(np.array(wrapped),np.array(allframes['idle'][0]))
    report['idleSeamlessWrap']=True;report['idleToRoarExactEntryMatch']=True
    report['masterSha256']=hashlib.sha256((ROOT/'source/bear_master.png').read_bytes()).hexdigest()
    (ROOT/'validation.json').write_text(json.dumps(report,indent=2));previews(allframes)
    (ROOT/'README.txt').write_text('BEAR MARKET — IDLE + ROAR\n\n54 transparent RGBA frames total: 27 idle + 27 roar, 512 x 512 each.\n24 fps, 1.125 seconds per animation.\n\nEach animation includes a 4608 x 1536 atlas (9 columns x 3 rows), three\n1536 x 1536 sheets (3 x 3), individual PNGs, JSON atlas and RGBA APNG.\nRead left to right, then top to bottom. Keep the full 512 x 512 canvas.\n\nIdle loops continuously. Roar plays once: anticipation, jaw opens,\nchest and paws rise, red shockwaves and cash scatter, then recovery\nand fade. Roar frame 27 is entirely transparent RGBA zero.\nRoar frame 01 matches idle frame 01. Start roar after idle wraps,\nor blend to its first frame in your game.\n\nOriginal bear colors, eyes and body are unchanged. Only the mouth\nregion uses the matching generated roar keypose. All intermediate\nframes use the same source art with deterministic local deformation.\n\npreview/bear_idle_then_roar.gif shows both animations on dark and\npurple test tiles at slower review speed. Test backgrounds are NOT\nin the production PNGs or APNGs. No audio is included.\n\nsource/build_assets.py rebuilds exports using Python, Pillow, NumPy,\nand SciPy. Generated master, keypose, isolated mouth, prompts and\nmotion records are included. validation.json records actual alpha,\nframe count, canvas dimensions, blank finish, APNG and atlas checks.\n')
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED,compresslevel=4) as z:
        for p in sorted(ROOT.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.writing'):z.write(p,p.relative_to(ROOT.parent))
    path=ROOT.parent/'bear_market_animation_pack.zip';write_bytes(path,buf.getvalue())
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for name in z.namelist():
            if name.endswith('.png'):Image.open(io.BytesIO(z.read(name))).load()
    print(f'ZIP integrity verified: {path.stat().st_size:,} bytes',flush=True)

if __name__=='__main__':main()
