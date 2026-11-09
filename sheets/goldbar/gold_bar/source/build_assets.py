"""One-master rigid gold bar: seamless idle and 27-frame drop-and-shine."""
from asset_utils import *

class GoldRig:
    def __init__(self):
        self.master=Image.open(ROOT/'source/gold_bar_master.png').convert('RGBA')
        self.box=self.master.getbbox();self.scale=360/(self.box[2]-self.box[0])
        crop=self.master.crop(self.box);self.height=round(crop.height*self.scale*SS)
        self.ox=76;self.oy=280-self.height/SS/2
        sprite=crop.resize((360*SS,self.height),R)
        self.base=Image.new('RGBA',(HI,HI));self.base.alpha_composite(sprite,(self.ox*SS,round(self.oy*SS)))
        self.ar=np.array(self.base).astype(np.float32)
        self.y,self.x=np.mgrid[0:HI,0:HI].astype(np.float32);self.x/=SS;self.y/=SS
        face=Image.new('L',(HI,HI));d=ImageDraw.Draw(face)
        d.polygon([tuple(round(c*SS) for c in self.point(x,y)) for x,y in [(298,399),(1270,29),(1510,150),(1514,175),(550,542),(519,545),(311,426)]],fill=255)
        self.face=np.array(face.filter(ImageFilter.GaussianBlur(2.0*SS))).astype(np.float32)/255
        alpha=self.ar[:,:,3]/255
        eroded=ndi.grey_erosion(alpha,size=(9,9))
        self.rim=np.clip((alpha-eroded)*2.0,0,1)
        save(self.base.resize((S,S),R),ROOT/'source/gold_bar_neutral_512.png')
        save(face,ROOT/'source/top_face_light_mask.png')

    def point(self,x,y):
        return np.array([self.ox+(x-self.box[0])*self.scale,self.oy+(y-self.box[1])*self.scale])

    def lighting(self,kind,f,rec):
        ar=self.ar.copy()
        if kind=='idle':
            t=(f%N)/N;p=math.tau*t
            center=-60+650*t
            strength=.26*math.sin(math.pi*t)**2
            ambient=1+.009*math.sin(p)
        else:
            t=float(np.clip((f-18)/5,0,1))
            center=-60+650*t
            strength=.65*math.sin(math.pi*t)**.65 if 18<=f<=23 else 0.
            ambient=1+.003*math.sin(math.tau*f/N)
        u=self.x+.25*(self.y-280)
        band=np.exp(-((u-center)/27)**2)
        amount=band*strength*(.24+.67*self.face+.3*self.rim)
        amount=np.clip(amount,0,.8)
        ar[:,:,:3]=np.minimum(ar[:,:,:3]*ambient,255)
        ar[:,:,:3]=ar[:,:,:3]*(1-amount[:,:,None])+np.array([255,246,192])*amount[:,:,None]
        ar[ar[:,:,3]==0,:3]=0
        rec['reflectionCenterX']=round(center,5);rec['reflectionStrength']=round(strength,6)
        return Image.fromarray(np.round(ar).astype(np.uint8))

    def body(self,lit,rec):
        angle=math.radians(rec['angleDegrees']);c,s=math.cos(angle),math.sin(angle)
        mat=np.array([[c,-s],[s,c]])
        pivot=np.array([256,345]);offset=pivot+np.array([0,rec['yOffset']])-mat@pivot
        inv=mat.T;shift=-inv@offset*SS
        coeff=(inv[0,0],inv[0,1],shift[0],inv[1,0],inv[1,1],shift[1])
        return lit.convert('RGBa').transform((HI,HI),Image.Transform.AFFINE,coeff,resample=Image.Resampling.BICUBIC).convert('RGBA')

    def sparks(self,f):
        layer=Image.new('RGBA',(HI,HI));age=f-11
        if not 0<=age<=5:return layer
        d=ImageDraw.Draw(layer);life=(1-age/6)**1.6
        for k,contact in enumerate([(470,870),(1617,432)]):
            x0,y0=self.point(*contact)
            for j in range(4):
                angle=math.radians(205+j*37+k*19)
                distance=3+age*(2.5+j*.6)
                x=x0+math.cos(angle)*distance;y=y0+math.sin(angle)*distance+age*age*.32
                length=2.8*(1-age/7)
                d.line((x*SS,y*SS,(x-math.cos(angle)*length)*SS,(y-math.sin(angle)*length)*SS),fill=(255,211+8*j,103+20*j,round(225*life)),width=SS)
            if age<2:
                rad=3.2-age
                d.polygon([(x0*SS,(y0-rad*2)*SS),((x0+rad*.5)*SS,(y0-rad*.4)*SS),((x0+rad*1.7)*SS,y0*SS),((x0+rad*.5)*SS,(y0+rad*.4)*SS),(x0*SS,(y0+rad*2)*SS),((x0-rad*.5)*SS,(y0+rad*.4)*SS),((x0-rad*1.7)*SS,y0*SS),((x0-rad*.5)*SS,(y0-rad*.4)*SS)],fill=(255,243,184,round(210*life)))
        return layer

    def render(self,kind,f):
        rec=motion(kind,f);lit=self.lighting(kind,f,rec);out=self.body(lit,rec)
        if kind=='impact':out.alpha_composite(self.sparks(f))
        ar=np.array(out.resize((S,S),R));ar[:,:,3]=np.round(ar[:,:,3].astype(float)*rec['opacity']).astype(np.uint8);ar[ar[:,:,3]==0,:3]=0
        return Image.fromarray(ar),rec

def motion(kind,f):
    if kind=='idle':return {'frame':f+1,'yOffset':0.,'angleDegrees':0.,'scale':1.,'opacity':1.}
    if f<=5:
        lift=float(smooth(f/5));y=-26*lift;angle=-.8*lift
    elif f<=11:
        t=(f-5)/6;y=-26*(1-t**2.8);angle=-.8*(1-t**2)
    elif f<=17:
        t=(f-11)/6;y=-8.0*math.sin(math.pi*t);angle=.36*math.sin(math.tau*t)*(1-t)
    else:
        y=0.;angle=0.
    fade=1-float(smooth((f-23)/3))
    return {'frame':f+1,'yOffset':round(y,7),'angleDegrees':round(angle,7),'scale':1.,'opacity':fade}

def main():
    rig=GoldRig();allframes={};report={}
    for kind in ('idle','impact'):
        frames=[];records=[]
        for f in range(N):
            im,rec=rig.render(kind,f);frames.append(im);records.append(rec)
        allframes[kind]=frames;export(kind,frames,records);report[kind]=validate(kind,frames)
        print(f'{kind}: 27 RGBA frames, atlases, sheets and APNG verified',flush=True)
    assert np.array_equal(np.array(allframes['idle'][0]),np.array(allframes['impact'][0]))
    wrapped,_=rig.render('idle',27);assert np.array_equal(np.array(wrapped),np.array(allframes['idle'][0]))
    report['idleSeamlessWrap']=True;report['idleToImpactExactEntryMatch']=True;report['rigidMotionOnly']=True
    report['masterSha256']=hashlib.sha256((ROOT/'source/gold_bar_master.png').read_bytes()).hexdigest()
    (ROOT/'validation.json').write_text(json.dumps(report,indent=2));previews(allframes)
    (ROOT/'README.txt').write_text('PLAIN GOLD BAR — IDLE + DROP AND SHINE\n\n54 transparent RGBA PNG frames: 27 idle + 27 impact, 512 x 512 each.\n24 fps, 1.125 seconds per animation. No numbers, stamps or logos.\n\nEach animation includes a 4608 x 1536 atlas (9 columns x 3 rows),\nthree 1536 x 1536 sheets (3 x 3), individual PNGs, atlas JSON,\nmotion JSON and an RGBA APNG. Read left to right, top to bottom.\nUse full 512 x 512 cells with centered pivot. Do not trim cells.\n\nIdle: a stationary rigid bar with a subtle moving reflection. Loops.\nImpact: frames 01-06 lift, 07-12 accelerate down to contact,\n13-18 make one small bounce and settle, 19-24 sweep the highlight,\n25-27 fade. Impact frame 27 is entirely transparent RGBA zero.\nNo squash, stretching, redesign or independent frame generation.\nImpact frame 01 exactly matches idle frame 01; transition at the\nidle wrap or blend to the entry pose in your game engine.\n\npreview/gold_bar_idle_then_impact.gif shows both clips at slower\nreview speed on dark and purple tiles. Test backgrounds are not\nin production PNGs or APNGs. No audio is included.\n\nThe source image is the approved plain-bar illustration. Source\nmaster, rigid renderer, masks and motion data are included.\nRebuild: python source/build_assets.py\nRequires Python, Pillow, NumPy and SciPy.\nvalidation.json records alpha, dimensions, frame count, exact\natlas/APNG matching, seamless idle wrap and the blank finish.\n')
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED,compresslevel=4) as z:
        for p in sorted(ROOT.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.writing'):z.write(p,p.relative_to(ROOT.parent))
    path=ROOT.parent/'gold_bar_animation_pack.zip';write_bytes(path,b.getvalue())
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for name in z.namelist():
            if name.endswith('.png'):Image.open(io.BytesIO(z.read(name))).load()
    print(f'ZIP integrity verified: {path.stat().st_size:,} bytes',flush=True)

if __name__=='__main__':main()
