"""Stationary monitor with deterministic animated display graphics."""
from asset_utils import *

SCREEN=[(329,204),(1159,198),(1141,647),(333,641)]
PATCH=[(335,199),(1158,194),(1165,202),(1148,649),(1140,656),(333,651),(324,644),(323,209)]
UI_W,UI_H=1000,540

def poly_mask(size,points,blur=0):
    m=Image.new('L',size);ImageDraw.Draw(m).polygon(points,fill=255)
    return m.filter(ImageFilter.GaussianBlur(blur)) if blur else m

def final_alpha(im,amount=1.):
    ar=np.array(im);ar[:,:,3]=np.round(ar[:,:,3].astype(float)*amount).astype(np.uint8);ar[ar[:,:,3]==0,:3]=0
    return Image.fromarray(ar)

class TerminalRig:
    def __init__(self):
        self.master=Image.open(ROOT/'source/terminal_master.png').convert('RGBA')
        blank=Image.open(ROOT/'source/blank_screen_plate.png').convert('RGBA')
        self.box=self.master.getbbox();self.scale=380/(self.box[2]-self.box[0]);self.ox=66;self.oy=92
        self.mask=poly_mask(self.master.size,PATCH,1.0)
        fixed=self.master.copy();fixed.paste(blank,(0,0),self.mask)
        fixed.putalpha(self.master.getchannel('A'))
        self.base=self.normalize(fixed)
        save(fixed,ROOT/'source/fixed_monitor_blank_screen.png')
        self.quad=[self.point(x,y)*SS for x,y in SCREEN]
        self.coeffs=self.homography()
        boundmask=Image.new('L',(HI,HI));d=ImageDraw.Draw(boundmask);d.polygon([tuple(p) for p in self.quad],fill=255)
        self.guard=boundmask.resize((S,S),Image.Resampling.NEAREST).filter(ImageFilter.MaxFilter(13))
        save(self.guard,ROOT/'source/animated_screen_region.png')

    def point(self,x,y):
        return np.array([self.ox+(x-self.box[0])*self.scale,self.oy+(y-self.box[1])*self.scale])

    def normalize(self,im):
        crop=im.crop(self.box);height=round(crop.height*self.scale*SS)
        sprite=crop.resize((380*SS,height),R)
        out=Image.new('RGBA',(HI,HI));out.alpha_composite(sprite,(self.ox*SS,self.oy*SS));return out

    def homography(self):
        src=[(0,0),(UI_W,0),(UI_W,UI_H),(0,UI_H)];A=[];B=[]
        for (x,y),(u,v) in zip(self.quad,src):
            A.extend([[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]]);B.extend([u,v])
        return tuple(np.linalg.solve(np.asarray(A,float),np.asarray(B,float)))

    def display(self,kind,f,rec):
        t=(f%N)/N;phase=math.tau*t;pulse=rec['screenPulse'];rise=rec['priceRise']
        im=Image.new('RGBA',(UI_W,UI_H));d=ImageDraw.Draw(im)
        if pulse>0:d.rounded_rectangle((1,1,UI_W-2,UI_H-2),radius=12,fill=(50,133,65,round(13*pulse)))
        # The faint grid is fixed. Small price ticks travel left across it.
        for x in (72,256,440,624,808):d.line((x,35,x,505),fill=(57,100,68,93),width=2)
        for y in (85,178,271,364,457):d.line((12,y,799,y),fill=(57,100,68,93),width=2)
        u=np.linspace(0,1,231)
        knots=np.array([0,.05,.11,.18,.24,.29,.35,.42,.49,.56,.63,.70,.77,.83,.89,.95,1.])
        values=np.array([.50,.52,.57,.56,.62,.64,.60,.55,.47,.50,.54,.56,.61,.57,.62,.64,.59])
        baseline=np.interp(u,knots,values)*UI_H
        ticker=u*784+92*t
        triangular=2*np.abs(2*((ticker/46)%1)-1)-1
        tick=6*triangular+3*np.sin(math.tau*ticker/92)
        lift=87*rise*smooth((u-.52)/.48)
        ys=baseline+tick-lift
        points=[(12+float(x)*784,float(y)) for x,y in zip(u,ys)]
        color=(round(90+39*pulse),round(174+35*pulse),round(94+31*pulse),255)
        d.line(points,fill=color,width=5,joint='curve')
        # The latest point becomes slightly brighter during the modest win.
        if pulse>0:
            xx,yy=points[-1];rr=2.3+1.1*pulse
            d.ellipse((xx-rr,yy-rr,xx+rr,yy+rr),fill=(160,224,145,round(180*pulse)))
        lengths=[]
        for j,base in enumerate([145,119,110,81]):
            change=(7-j*.8)*(math.sin(phase+j*.7)-math.sin(j*.7))
            width=base+change+rise*(8-j)
            y=95+j*65
            d.rectangle((839,y,839+width,y+23),fill=(round(67+20*pulse),round(131+25*pulse),round(73+18*pulse),255))
            lengths.append(round(width,5))
        rec['tickScrollPx']=round(92*t,6);rec['barWidths']=lengths
        rec['lastPriceY']=round(float(ys[-1]),5)
        return im

    def render(self,kind,f):
        rec=motion(kind,f);ui=self.display(kind,f,rec)
        projected=ui.convert('RGBa').transform((HI,HI),Image.Transform.PERSPECTIVE,self.coeffs,resample=Image.Resampling.BICUBIC).convert('RGBA')
        out=self.base.copy();out.alpha_composite(projected)
        out=final_alpha(out.resize((S,S),R),rec['opacity'])
        return out,rec

def motion(kind,f):
    if kind=='idle':return {'frame':f+1,'priceRise':0.,'screenPulse':0.,'opacity':1.,'monitorX':0.,'monitorY':0.,'monitorRotation':0.,'monitorScale':1.}
    rise=float(smooth((f-6)/8))*(1-.12*float(smooth((f-18)/4)))
    pulse=float(smooth((f-8)/6))*(1-float(smooth((f-16)/6)))
    return {'frame':f+1,'priceRise':rise,'screenPulse':pulse,'opacity':1-float(smooth((f-23)/3)),'monitorX':0.,'monitorY':0.,'monitorRotation':0.,'monitorScale':1.}

def check_stationary_case(frames,guard,kind):
    outside=np.array(guard)==0;first=np.array(frames[0]);a0=first[:,:,3]
    for i,im in enumerate(frames):
        a=np.array(im)
        if kind=='idle' or i<=23:
            assert np.array_equal(a[outside],first[outside]),f'Case changed outside display at {kind} {i+1}'
            assert np.array_equal(a[:,:,3],a0),f'Silhouette moved at {kind} {i+1}'

def main():
    rig=TerminalRig();allframes={};report={}
    for kind in ('idle','win'):
        frames=[];records=[]
        for f in range(N):
            im,rec=rig.render(kind,f);frames.append(im);records.append(rec)
        check_stationary_case(frames,rig.guard,kind)
        allframes[kind]=frames;export(kind,frames,records);report[kind]=validate(kind,frames)
        print(f'{kind}: 27 RGBA frames, static casing, atlas, sheets and APNG verified',flush=True)
    assert np.array_equal(np.array(allframes['idle'][0]),np.array(allframes['win'][0]))
    wrapped,_=rig.render('idle',27);assert np.array_equal(np.array(wrapped),np.array(allframes['idle'][0]))
    report['idleSeamlessWrap']=True;report['idleToWinExactEntryMatch']=True
    report['casePixelsUnchangedOutsideDisplayUntilFade']=True;report['fixedSilhouetteUntilFade']=True
    report['masterSha256']=hashlib.sha256((ROOT/'source/terminal_master.png').read_bytes()).hexdigest()
    (ROOT/'validation.json').write_text(json.dumps(report,indent=2));previews(allframes)
    save(allframes['idle'][0],ROOT/'trading_terminal_still.png')
    (ROOT/'README.txt').write_text('TRADING TERMINAL — IDLE + MODEST WIN\n\n54 transparent RGBA PNG frames: 27 idle + 27 win, 512 x 512 each.\n24 fps, 1.125 seconds per animation.\n\nEach animation includes a 4608 x 1536 atlas (9 columns x 3 rows),\nthree 1536 x 1536 sheets (3 x 3), individual PNGs, atlas JSON,\nmotion JSON and RGBA APNG. Read left to right, top to bottom.\nKeep full cells and use a centered pivot. Do not trim frames.\n\nIdle: small scrolling price ticks and subtle data-bar updates.\nThe monitor casing and stand remain exactly still.\nWin: the right end of the chart rises moderately, the display\nbriefly brightens, then settles at its higher level. Frames 25-27\nfade the complete symbol. Frame 27 is entirely transparent RGBA zero.\nAll chart data is fictional decorative animation, not market data.\n\nThe approved monitor artwork is reused in every frame. A generated\nblank display is composited into the original casing; all graph\nanimation is deterministic and clipped inside the screen. No\nindependent redraws, movement or color changes to the monitor case.\n\nWin frame 01 exactly matches idle frame 01. Switch after the idle\nwrap or blend to its entry frame in the engine.\npreview/trading_terminal_idle_then_win.gif shows both clips at\nslower review speed on dark and purple tiles. Test backgrounds\nare not in production PNGs or APNGs. No audio is included.\n\nRebuild: python source/build_assets.py\nRequires Python, Pillow, NumPy and SciPy. Source artwork, renderer,\nmasks, screen-plate prompt and motion data included.\nvalidation.json records alpha, dimensions, exact atlas/APNG matching,\nstationary case pixels and silhouette, loop entry, and blank finish.\n')
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED,compresslevel=4) as z:
        for p in sorted(ROOT.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.writing'):z.write(p,p.relative_to(ROOT.parent))
    path=ROOT.parent/'trading_terminal_animation_pack.zip';write_bytes(path,buf.getvalue())
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for name in z.namelist():
            if name.endswith('.png'):Image.open(io.BytesIO(z.read(name))).load()
    print(f'ZIP integrity verified: {path.stat().st_size:,} bytes',flush=True)

if __name__=='__main__':main()
