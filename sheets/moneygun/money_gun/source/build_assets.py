"""Build transparent cash-gun idle and firing sprites from one master."""
from asset_utils import *

class GunRig:
    def __init__(self):
        self.master=Image.open(ROOT/'source/money_gun_master.png').convert('RGBA')
        self.bill=Image.open(ROOT/'source/banknote.png').convert('RGBA')
        self.bill=self.bill.crop(self.bill.getbbox())
        self.box=self.master.getbbox();self.scale=310/(self.box[3]-self.box[1]);self.ox=61;self.oy=130
        crop=self.master.crop(self.box)
        sprite=crop.resize((round(crop.width*self.scale*SS),310*SS),R)
        self.base=Image.new('RGBA',(HI,HI));self.base.alpha_composite(sprite,(self.ox*SS,self.oy*SS))
        self.muzzle=self.point(1091,397)
        mask=Image.new('L',(HI,HI));d=ImageDraw.Draw(mask)
        d.polygon([tuple(v*SS for v in self.point(x,y)) for x,y in [(995,370),(1185,315),(1192,406),(1008,465)]],fill=255)
        self.mouth=mask.filter(ImageFilter.GaussianBlur(.35*SS))
        save(self.base.resize((S,S),R),ROOT/'source/money_gun_neutral_512.png')
        save(self.mouth,ROOT/'source/ejection_window_mask.png')

    def point(self,x,y):
        return np.array([self.ox+(x-self.box[0])*self.scale,self.oy+(y-self.box[1])*self.scale])

    def transform(self,rec):
        angle=math.radians(rec['angleDegrees']);c,s=math.cos(angle),math.sin(angle)
        mat=np.array([[c,-s],[s,c]])*rec['scale']
        pivot=np.array([218,300]);offset=pivot+np.array([rec['xOffset'],rec['yOffset']])-mat@pivot
        inv=np.linalg.inv(mat);shift=-inv@offset*SS
        coeff=(inv[0,0],inv[0,1],shift[0],inv[1,0],inv[1,1],shift[1])
        body=self.base.convert('RGBa').transform((HI,HI),Image.Transform.AFFINE,coeff,resample=Image.Resampling.BICUBIC).convert('RGBA')
        mask=self.mouth.transform((HI,HI),Image.Transform.AFFINE,coeff,resample=Image.Resampling.BICUBIC)
        muzzle=mat@self.muzzle+offset
        return body,mask,muzzle

    def flying_bill(self,age,j):
        width=(53+4*math.sin(j*1.7))*(1+.016*age)
        height=(12+7*abs(math.cos(age*.70+j*.4)))*(1+.010*age)
        bill=self.bill.resize((round(width*SS),round(height*SS)),R)
        angle=22+(j%4-1.5)*6+math.sin(age*.8+j)*21+age*(1 if j%2 else -1)*3
        bill=bill.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True)
        ar=np.array(bill);ar[:,:,3]=np.round(ar[:,:,3].astype(float)*(1-float(smooth((age-6)/4)))).astype(np.uint8)
        ar[ar[:,:,3]==0,:3]=0
        return Image.fromarray(ar)

    def render(self,kind,f):
        rec=motion(kind,f);body,mouth,muzzle=self.transform(rec)
        notes=Image.new('RGBA',(HI,HI));active=[]
        if kind=='fire':
            for j in range(14):
                birth=6+j*.88;age=f-birth
                if not 0<=age<10:continue
                launch=motion('fire',birth)
                theta=math.radians(launch['angleDegrees']);c,s=math.cos(theta),math.sin(theta)
                mat=np.array([[c,-s],[s,c]])*launch['scale'];pivot=np.array([218,300])
                start=mat@(self.muzzle-pivot)+pivot+np.array([launch['xOffset'],launch['yOffset']])
                x=start[0]+age*(10.2+(j%4)*.8)
                y=start[1]-age*(14+(j%5)*1.5)+.25*age*age
                im=self.flying_bill(age,j)
                notes.alpha_composite(im,(round(x*SS-im.width/2),round(y*SS-im.height/2)))
                active.append({'id':j,'age':round(age,4),'x':round(x,4),'y':round(y,4)})
            # Cash is visible inside the opening and outside the silhouette.
            # This keeps the gold lip and red housing in front during ejection.
            ar=np.array(notes);mask=np.maximum(1-np.array(body)[:,:,3]/255,np.array(mouth)/255)
            ar[:,:,3]=np.round(ar[:,:,3]*mask).astype(np.uint8);ar[ar[:,:,3]==0,:3]=0
            notes=Image.fromarray(ar)
        body.alpha_composite(notes)
        out=np.array(body.resize((S,S),R));out[:,:,3]=np.round(out[:,:,3].astype(float)*rec['opacity']).astype(np.uint8);out[out[:,:,3]==0,:3]=0
        rec['visibleBanknotes']=active
        return Image.fromarray(out),rec

def motion(kind,f):
    if kind=='idle':
        p=math.tau*f/N
        return {'frame':f+1,'angleDegrees':.7*math.sin(p),'scale':1+.006*math.sin(p),'xOffset':0.,'yOffset':1.8*math.sin(p),'opacity':1.}
    charge=float(smooth(f/5))*(1-float(smooth((f-5)/2)))
    firing=float(smooth((f-4)/3))*(1-float(smooth((f-18)/3)))
    pulse=(.5+.5*math.sin((f-6)*math.tau/3))*firing
    settle=.5*float(smooth((f-18)/3))*(1-float(smooth((f-21)/3)))
    return {'frame':f+1,'angleDegrees':1.2*charge-2.4*firing-1.1*pulse,'scale':1+.014*charge,'xOffset':-3.5*pulse,'yOffset':2.2*charge+1.4*pulse+settle,'opacity':1-float(smooth((f-22)/4))}

def main():
    rig=GunRig();allframes={};report={}
    for kind in ('idle','fire'):
        frames=[];records=[]
        for f in range(N):
            im,rec=rig.render(kind,f);frames.append(im);records.append(rec)
        allframes[kind]=frames;export(kind,frames,records);report[kind]=validate(kind,frames)
        print(f'{kind}: 27 transparent frames, sheets and APNG verified',flush=True)
    assert np.array_equal(np.array(allframes['idle'][0]),np.array(allframes['fire'][0]))
    wrapped,_=rig.render('idle',27);assert np.array_equal(np.array(wrapped),np.array(allframes['idle'][0]))
    report['idleSeamlessWrap']=True;report['idleToFireExactEntryMatch']=True
    report['masterSha256']=hashlib.sha256((ROOT/'source/money_gun_master.png').read_bytes()).hexdigest()
    (ROOT/'validation.json').write_text(json.dumps(report,indent=2));previews(allframes)
    (ROOT/'README.txt').write_text('MONEY GUN — IDLE + CASH BURST\n\n54 transparent RGBA PNG frames: 27 idle + 27 fire, 512 x 512 each.\n24 fps, 1.125 seconds per clip.\n\nEach clip includes a 4608 x 1536 atlas (9 columns x 3 rows), three\n1536 x 1536 sheets (3 x 3), individual PNGs, JSON atlas and RGBA APNG.\nRead left to right, then top to bottom. Use full 512 x 512 cells\nwith centered pivot; disable trimming.\n\nIdle loops with a gentle float and tilt. Fire plays once: wind-up,\nrecoil and a continuous burst of 14 fluttering notes, followed by\nsettling and fade. Fire frame 27 is fully transparent RGBA zero.\nFire frame 01 matches idle frame 01. Switch after the idle wraps or\nblend to the first fire frame in the engine.\n\nThe same gun artwork is used in every frame. Banknotes reuse one\nmatching isolated bill. Notes emerge from a masked front opening.\nNo logos, numbers or portraits appear on the artwork. No audio.\n\npreview/money_gun_idle_then_roar.gif shows both clips at slower\nreview speed on dark and purple test backgrounds. Those backgrounds\nare not in the production PNGs or APNGs.\n\nRebuild with Python, Pillow, NumPy and SciPy: python source/build_assets.py\nSource masters, renderer, generation prompts and motion data included.\nvalidation.json records alpha, dimensions, exact atlas/APNG matching,\nseamless idle wrap and the blank final firing frame.\n')
    old=ROOT/'preview/money_gun_idle_then_roar.gif';new=ROOT/'preview/money_gun_idle_then_fire.gif'
    if old.exists():os.replace(old,new)
    readme=ROOT/'README.txt';readme.write_text(readme.read_text().replace('idle_then_roar','idle_then_fire'))
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED,compresslevel=4) as z:
        for p in sorted(ROOT.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.writing'):z.write(p,p.relative_to(ROOT.parent))
    path=ROOT.parent/'money_gun_animation_pack.zip';write_bytes(path,b.getvalue())
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for name in z.namelist():
            if name.endswith('.png'):Image.open(io.BytesIO(z.read(name))).load()
    print(f'ZIP integrity verified: {path.stat().st_size:,} bytes',flush=True)

if __name__=='__main__':main()
