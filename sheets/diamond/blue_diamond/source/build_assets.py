"""One fixed diamond master with a transparent contour glow and facet sheen."""
from asset_utils import *

class DiamondRig:
    def __init__(self):
        self.master=Image.open(ROOT/'source/diamond_master.png').convert('RGBA')
        self.box=self.master.getbbox();crop=self.master.crop(self.box)
        self.scale=336/crop.width;self.height=round(crop.height*self.scale*SS)
        sprite=crop.resize((336*SS,self.height),R)
        self.base=Image.new('RGBA',(HI,HI));self.base.alpha_composite(sprite,(88*SS,round(256*SS-self.height/2)))
        self.ar=np.array(self.base).astype(np.float32);self.alpha=self.ar[:,:,3]/255
        solid=self.alpha>.5
        self.distance=ndi.distance_transform_edt(~solid)/SS
        inside=ndi.distance_transform_edt(solid)/SS
        self.rim=np.exp(-(inside/2.0)**2)*solid
        self.y,self.x=np.mgrid[0:HI,0:HI].astype(np.float32);self.x/=SS;self.y/=SS
        save(self.base.resize((S,S),R),ROOT/'source/diamond_neutral_512.png')
        self.opaque=ndi.binary_erosion(np.array(self.base.resize((S,S),R))[:,:,3]==255,iterations=2)

    def render(self,kind,f):
        rec=motion(kind,f);power=rec['glowIntensity'];t=(f%N)/N;phase=math.tau*t
        width=8+14*power
        halo_alpha=np.clip(.58*power*np.exp(-(self.distance/width)**2)+.26*power*np.exp(-(self.distance/4)**2),0,1)
        halo=np.zeros((HI,HI,4),np.uint8)
        halo[:,:,:3]=np.array([52+39*power,157+45*power,255]).astype(np.uint8)
        halo[:,:,3]=np.round(halo_alpha*255).astype(np.uint8);halo[halo[:,:,3]<2]=0
        layer=Image.fromarray(halo)
        beam_x=60+392*t
        beam=np.exp(-((self.x+.24*(self.y-256)-beam_x)/17)**2)
        sweep=(.07 if kind=='idle' else .06+.22*power)*math.sin(math.pi*t)**2
        mix=np.clip(.055*power+.15*power*self.rim+beam*sweep,0,.40)
        body=self.ar.copy()
        lit=np.minimum(body[:,:,:3]*(1+.075*power+.012*math.sin(phase)),255)
        body[:,:,:3]=lit*(1-mix[:,:,None])+np.array([213,253,255])*mix[:,:,None]
        body[body[:,:,3]==0,:3]=0
        layer.alpha_composite(Image.fromarray(np.round(body).astype(np.uint8)))
        out=np.array(layer.resize((S,S),R));out[:,:,3]=np.round(out[:,:,3].astype(float)*rec['opacity']).astype(np.uint8)
        out[out[:,:,3]==0,:3]=0
        rec['glowWidthPx']=round(width,6);rec['lightSweepX']=round(beam_x,5);rec['lightSweepStrength']=round(sweep,6)
        return Image.fromarray(out),rec

def motion(kind,f):
    t=(f%N)/N
    if kind=='idle':
        power=.10+.04*math.sin(math.tau*t);fade=1.
    else:
        power=.10+.90*float(smooth(f/12))*(1-float(smooth((f-16)/7)))
        fade=1-float(smooth((f-23)/3))
    return {'frame':f+1,'glowIntensity':power,'opacity':fade,'centerX':256,'centerY':256,'diamondWidth':336,'rotation':0,'scale':1}

def main():
    rig=DiamondRig();allframes={};report={}
    for kind in ('idle','glow'):
        frames=[];records=[]
        for f in range(N):
            im,rec=rig.render(kind,f);frames.append(im);records.append(rec)
            if rec['opacity']==1:assert np.all(np.array(im)[:,:,3][rig.opaque]==255)
        allframes[kind]=frames;export(kind,frames,records);report[kind]=validate(kind,frames)
        print(f'{kind}: 27 RGBA frames, atlas, sheets and APNG verified',flush=True)
    assert np.array_equal(np.array(allframes['idle'][0]),np.array(allframes['glow'][0]))
    wrapped,_=rig.render('idle',27);assert np.array_equal(np.array(wrapped),np.array(allframes['idle'][0]))
    report['idleSeamlessWrap']=True;report['idleToGlowExactEntryMatch']=True
    report['fixedMasterNoRotationScalingOrDeformation']=True
    report['opaqueDiamondCorePreservedUntilFade']=True
    report['masterSha256']=hashlib.sha256((ROOT/'source/diamond_master.png').read_bytes()).hexdigest()
    (ROOT/'validation.json').write_text(json.dumps(report,indent=2));previews(allframes)
    save(allframes['idle'][0],ROOT/'diamond_still.png')
    (ROOT/'README.txt').write_text('BLUE DIAMOND — IDLE + GLOW\n\n54 transparent RGBA PNG frames: 27 idle + 27 glow, 512 x 512 each.\n24 fps, 1.125 seconds per clip.\n\nEach clip includes a 4608 x 1536 atlas (9 columns x 3 rows), three\n1536 x 1536 sheets (3 x 3), individual PNGs, atlas JSON, motion JSON\nand RGBA APNG. Read left to right, top to bottom. Preserve the full\n512 x 512 cells with a centered pivot. Do not trim the frames.\n\nIdle loops with a restrained cyan glow and subtle facet sheen.\nGlow is a one-shot win: light builds over frames 01-13, peaks\nover 14-17, and softens over 18-24. Frames 25-27 fade the whole\nsymbol. Final frame 27 is entirely transparent RGBA zero.\n\nThe diamond illustration is fixed throughout: no translation,\nrotation, scaling, warping or independently redrawn frames. Only\nlighting changes. Glow follows the gemstone contour with real\npartial alpha and transparent pixels beyond it; no background fill.\nUse ordinary source-over alpha blending in the game engine.\n\nGlow frame 01 exactly matches idle frame 01. Transition after\nthe idle wraps, or blend to the entry lighting in your engine.\n\npreview/diamond_idle_then_glow.gif shows both clips at slower\nreview speed on dark and purple tiles. These test backgrounds\nare not in the production PNGs or APNGs. No audio is included.\n\nRebuild: python source/build_assets.py\nRequires Python, Pillow, NumPy and SciPy. Source master, prompt,\nrenderer, neutral still and animation records included.\nvalidation.json records alpha, canvas sizes, frame count, exact\natlas/APNG matching, seamless idle wrap and the blank last frame.\n')
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED,compresslevel=4) as z:
        for p in sorted(ROOT.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.writing'):z.write(p,p.relative_to(ROOT.parent))
    path=ROOT.parent/'blue_diamond_animation_pack.zip';write_bytes(path,buf.getvalue())
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for name in z.namelist():
            if name.endswith('.png'):Image.open(io.BytesIO(z.read(name))).load()
    print(f'ZIP integrity verified: {path.stat().st_size:,} bytes',flush=True)

if __name__=='__main__':main()
