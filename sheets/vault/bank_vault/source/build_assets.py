"""A fixed vault shell, independently rotating wheel and projective hinged door."""
from asset_utils import *

RAW=(825,887)
DOOR=[(146,222),(584,222),(630,263),(630,677),(590,714),(146,714),(130,697),(130,241)]
RECT=(130,222,630,714)
CX,CY=362,466

def poly_mask(size,points,blur=0):
    m=Image.new('L',size);ImageDraw.Draw(m).polygon(points,fill=255)
    return m.filter(ImageFilter.GaussianBlur(blur)) if blur else m

def opacity(im,amount):
    ar=np.array(im);ar[:,:,3]=np.round(ar[:,:,3].astype(float)*amount).astype(np.uint8);ar[ar[:,:,3]==0,:3]=0
    return Image.fromarray(ar)

def warp_quad(im,quad):
    # Map a texture to a projected 3D face with a single homography.
    w,h=im.size;src=[(0,0),(w,0),(w,h),(0,h)];A=[];B=[]
    for (x,y),(u,v) in zip(quad,src):
        A.extend([[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]]);B.extend([u,v])
    co=np.linalg.solve(np.asarray(A,float),np.asarray(B,float))
    return im.convert('RGBa').transform((HI,HI),Image.Transform.PERSPECTIVE,tuple(co),resample=Image.Resampling.BICUBIC).convert('RGBA')

class VaultRig:
    def __init__(self):
        self.original=Image.open(ROOT/'source/vault_master.png').convert('RGBA')
        self.plate=Image.open(ROOT/'source/door_without_wheel.png').convert('RGBA')
        interior=Image.open(ROOT/'source/cash_interior.png').convert('RGBA')
        self.box=self.original.getbbox();self.scale=330/(self.box[3]-self.box[1]);self.ox=86;self.oy=78
        self.shell=self.original.copy();self.door_mask=poly_mask(RAW,DOOR,.35)
        self.shell.paste(interior,(0,0),self.door_mask)
        self.shell_canvas=self.normalize(self.shell)
        self.wheel=Image.open(ROOT/'source/wheel.png').convert('RGBA')
        yy,xx=np.mgrid[0:RAW[1],0:RAW[0]];radius=np.sqrt(((xx-CX)/181)**2+((yy-CY)/187)**2)
        self.fixed_wheel=self.wheel.copy();wa=np.array(self.wheel)
        fixed=(radius>.765)|(radius<.345);wa[:,:,3]=np.where(fixed,wa[:,:,3],0);wa[wa[:,:,3]==0,:3]=0
        self.fixed_wheel=Image.fromarray(wa)
        self.spokes=self.wheel.copy();sp=np.array(self.wheel);sp[:,:,3]=np.where((radius<.83)&(radius>.25),sp[:,:,3],0);sp[sp[:,:,3]==0,:3]=0;self.spokes=Image.fromarray(sp)
        # Silver edge material comes from the original outer frame.
        self.edge_material=self.original.crop((646,270,672,666)).resize((54*SS,492*SS),R)
        d=ImageDraw.Draw(self.edge_material)
        for y in (90,246,402):
            d.ellipse((16*SS,(y-13)*SS,43*SS,(y+13)*SS),fill=(47,54,65,255),outline=(180,185,191,255),width=2*SS)
        self.foreground=self.original.copy();hm=Image.new('L',RAW);hd=ImageDraw.Draw(hm)
        hd.rounded_rectangle((77,276,136,393),radius=9,fill=255);hd.rounded_rectangle((77,546,136,664),radius=9,fill=255)
        self.foreground.putalpha(Image.fromarray(np.minimum(np.array(hm),np.array(self.original)[:,:,3])))
        self.hinges_canvas=self.normalize(self.foreground)
        save(self.shell,ROOT/'source/fixed_shell_with_cash.png');save(self.fixed_wheel,ROOT/'source/wheel_rim_and_hub.png');save(self.spokes,ROOT/'source/wheel_spokes.png')
        save(self.foreground,ROOT/'source/fixed_hinges.png')
        save(self.edge_material,ROOT/'source/door_edge_material.png')
        self.y,self.x=np.mgrid[0:HI,0:HI].astype(np.float32);self.x/=SS;self.y/=SS

    def point(self,x,y):
        return np.array([self.ox+(x-self.box[0])*self.scale,self.oy+(y-self.box[1])*self.scale])

    def normalize(self,im):
        crop=im.crop(self.box);crop=crop.resize((round(crop.width*self.scale*SS),330*SS),R)
        out=Image.new('RGBA',(HI,HI));out.alpha_composite(crop,(round(self.ox*SS),round(self.oy*SS)));return out

    def make_door(self,wheel_angle):
        a=math.radians(wheel_angle);c,s=math.cos(a),math.sin(a)
        # Rotation in the wheel's own slightly elliptical front plane.
        sx=181/187;mat=np.array([[c,-s*sx],[s/sx,c]])
        center=np.array([CX,CY]);inv=np.linalg.inv(mat);off=center-inv@center
        co=(inv[0,0],inv[0,1],off[0],inv[1,0],inv[1,1],off[1])
        rotating=self.spokes.convert('RGBa').transform(RAW,Image.Transform.AFFINE,co,resample=Image.Resampling.BICUBIC).convert('RGBA')
        door=self.plate.copy();door.alpha_composite(rotating);door.alpha_composite(self.fixed_wheel);door.putalpha(self.door_mask)
        return door.crop(RECT).resize((500*SS,492*SS),R)

    def project(self,x,y,z,angle):
        # Local x runs across the door, y down it; z is door thickness.
        a=math.radians(angle);c,s=math.cos(a),math.sin(a)
        wx=x*c-z*s;wz=x*s+z*c
        perspective=1/(1-wz/4200)
        px=130+(wx-.213*wz)*perspective
        py=222+246+(y-246+.14*wz)*perspective
        return self.point(px,py)*SS

    def render(self,kind,f):
        rec=motion(kind,f);body=self.shell_canvas.copy()
        opening=rec['doorDegrees'];door=self.make_door(rec['wheelDegrees'])
        if opening>.01:
            side_quad=[self.project(500,41,0,opening),self.project(500,41,-50,opening),self.project(500,455,-50,opening),self.project(500,455,0,opening)]
            material=self.edge_material.copy()
            if rec['boltExtension']>0:
                caps=Image.new('RGBA',material.size);cd=ImageDraw.Draw(caps)
                for yy in (90,246,402):
                    cd.ellipse((17*SS,(yy-12)*SS,42*SS,(yy+12)*SS),fill=(166,172,181,255),outline=(229,232,235,255),width=SS)
                    cd.arc((19*SS,(yy-10)*SS,40*SS,(yy+10)*SS),185,285,fill=(245,247,249,255),width=SS)
                material.alpha_composite(opacity(caps,rec['boltExtension']))
            material=material.crop((0,41*SS,material.width,455*SS))
            side=warp_quad(material,side_quad)
            body.alpha_composite(opacity(side,float(smooth(opening/3))))
        quad=[self.project(0,0,0,opening),self.project(500,0,0,opening),self.project(500,492,0,opening),self.project(0,492,0,opening)]
        body.alpha_composite(warp_quad(door,quad));body.alpha_composite(self.hinges_canvas)
        ar=np.array(body).astype(np.float32)
        if kind=='idle':
            t=(f%N)/N;strength=.075*math.sin(math.pi*t)**2
            band=np.exp(-((self.x+.2*(self.y-256)-(-80+660*t))/25)**2)
            amt=strength*band;ambient=1+.012*math.sin(math.tau*t)
        else:
            ambient=1+.012*math.sin(math.tau*f/N)
            # A restrained warm sweep celebrates the revealed money.
            t=float(np.clip((f-18)/5,0,1));strength=.055*math.sin(math.pi*t)**2 if 18<=f<=23 else 0
            band=np.exp(-((self.x-(210+170*t))/33)**2);amt=strength*band
        ar[:,:,:3]=np.minimum(ar[:,:,:3]*ambient,255)
        ar[:,:,:3]=ar[:,:,:3]*(1-amt[:,:,None])+np.array([255,236,176])*amt[:,:,None]
        ar[ar[:,:,3]==0,:3]=0
        out=Image.fromarray(np.round(ar).astype(np.uint8)).resize((S,S),R)
        out=opacity(out,rec['opacity']);return out,rec

def motion(kind,f):
    if kind=='idle':return {'frame':f+1,'wheelDegrees':0.,'doorDegrees':0.,'boltExtension':1.,'opacity':1.}
    t=float(np.clip(f/8,0,1));wheel=180*(1-(1-t)**2)
    door=60*float(smooth((f-9)/8))
    return {'frame':f+1,'wheelDegrees':round(wheel,6),'doorDegrees':round(door,6),'boltExtension':1-float(smooth((f-8)/3)),'opacity':1-float(smooth((f-23)/3))}

def main():
    rig=VaultRig();allframes={};report={}
    for kind in ('idle','unlock'):
        frames=[];records=[]
        for f in range(N):
            im,rec=rig.render(kind,f);frames.append(im);records.append(rec)
        allframes[kind]=frames;export(kind,frames,records);report[kind]=validate(kind,frames)
        print(f'{kind}: 27 RGBA frames, atlas, sheets and APNG verified',flush=True)
    assert np.array_equal(np.array(allframes['idle'][0]),np.array(allframes['unlock'][0]))
    wrapped,_=rig.render('idle',27);assert np.array_equal(np.array(wrapped),np.array(allframes['idle'][0]))
    report['idleSeamlessWrap']=True;report['idleToUnlockExactEntryMatch']=True
    report['fixedShellAndCash']=True;report['independentWheelAndHingedDoor']=True
    report['masterSha256']=hashlib.sha256((ROOT/'source/vault_master.png').read_bytes()).hexdigest()
    (ROOT/'validation.json').write_text(json.dumps(report,indent=2));previews(allframes)
    save(allframes['idle'][0],ROOT/'bank_vault_closed.png')
    save(allframes['unlock'][18],ROOT/'bank_vault_open.png')
    (ROOT/'README.txt').write_text('BANK VAULT — IDLE + UNLOCK\n\n54 transparent RGBA PNG frames: 27 idle + 27 unlock, 512 x 512 each.\n24 fps, 1.125 seconds per clip.\n\nEach clip includes a 4608 x 1536 atlas (9 columns x 3 rows), three\n1536 x 1536 sheets (3 x 3), individual PNGs, atlas JSON, motion JSON\nand RGBA APNG. Read left to right, top to bottom. Keep full cells\nand use a centered pivot; do not trim frames.\n\nIdle: closed vault with a restrained reflection. Loops continuously.\nUnlock: frames 01-09 turn the wheel through 180 degrees and slow\nto a stop; 10-18 open the door on its fixed left hinge; 19-24 hold\nthe open cash reveal; 25-27 fade. Final frame is RGBA zero.\nThe bolts retract inside the frame before the door swings; bolt\nsockets are visible on the thick door edge. Money stays inside.\n\nThe fixed shell comes from the approved concept. Generated clean\ndoor and cash layers are composited into it. The same door and\nwheel parts are transformed in every frame: no independent redraws.\nDoor movement uses a perspective hinge projection, not a crossfade.\n\nUnlock frame 01 exactly matches idle frame 01. Switch at the idle\nwrap or blend to the closed pose. Closed/open stills included.\npreview/bank_vault_idle_then_unlock.gif is a slower review preview\non dark and purple tiles; those backgrounds are not in production\nPNGs or APNGs. No audio is included.\n\nRebuild: python source/build_assets.py\nRequires Python, Pillow, NumPy and SciPy. Original reference,\ncomponent artwork, masks, renderer and motion data included.\nvalidation.json records actual alpha, dimensions, exact atlas/APNG\nmatching, loop entry matching and the fully blank last frame.\n')
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED,compresslevel=4) as z:
        for p in sorted(ROOT.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.writing'):z.write(p,p.relative_to(ROOT.parent))
    path=ROOT.parent/'bank_vault_animation_pack.zip';write_bytes(path,buf.getvalue())
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for name in z.namelist():
            if name.endswith('.png'):Image.open(io.BytesIO(z.read(name))).load()
    print(f'ZIP integrity verified: {path.stat().st_size:,} bytes',flush=True)

if __name__=='__main__':main()
