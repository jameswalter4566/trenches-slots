"""Bull transformation and forward charge. Requires Pillow, NumPy, SciPy."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi
import numpy as np
import math, io, os, json, hashlib, zipfile

ROOT=Path(__file__).resolve().parents[1]
SIZE=512; SS=2; HI=1024; COUNT=27; FPS=24; R=Image.Resampling.LANCZOS

def save(im,path,**kw):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    b=io.BytesIO();im.save(b,format={'.png':'PNG','.apng':'PNG','.gif':'GIF','.jpg':'JPEG'}[path.suffix],**kw)
    tmp=path.with_name(path.name+'.writing');tmp.write_bytes(b.getvalue());os.replace(tmp,path)

def smooth(t):
    t=np.clip(t,0,1);return t*t*(3-2*t)

def clean(image):
    a=np.array(image.convert('RGBA'));labels,_=ndi.label(a[:,:,3]>180)
    counts=np.bincount(labels.ravel());counts[0]=0;mask=labels==counts.argmax()
    mask=ndi.binary_opening(mask,iterations=2);mask=ndi.binary_fill_holes(ndi.binary_closing(mask,iterations=3))
    mask=ndi.binary_erosion(mask,iterations=1)
    alpha=np.round(ndi.gaussian_filter(mask.astype(float),.85)*255).astype(np.uint8);alpha[alpha<2]=0
    core=mask&(a[:,:,3]>245);_,idx=ndi.distance_transform_edt(~core,return_indices=True)
    edge=(alpha>0)&~core;a[edge,:3]=a[idx[0][edge],idx[1][edge],:3]
    a[:,:,3]=alpha;a[alpha==0,:3]=0
    return Image.fromarray(a)

def prepare(original_master,dark_source,idle_first):
    master=Image.open(original_master).convert('RGBA');box=master.getbbox();crop=master.crop(box)
    scale=336/crop.height;sprite=crop.resize((round(crop.width*scale*SS),336*SS),R)
    brown=Image.new('RGBA',(HI,HI));brown.alpha_composite(sprite,(round((256-(620-box[0])*scale)*SS),78*SS))
    dark=clean(Image.open(dark_source));save(dark,ROOT/'source/dark_master.png')
    # Match extents, then retain the original silhouette for the color transition.
    bb=brown.getbbox();aligned=Image.new('RGBA',(HI,HI))
    aligned.paste(dark.crop(dark.getbbox()).resize((bb[2]-bb[0],bb[3]-bb[1]),R),(bb[0],bb[1]))
    da=np.array(aligned);ba=np.array(brown);solid=da[:,:,3]>180
    _,idx=ndi.distance_transform_edt(~solid,return_indices=True)
    edge=(ba[:,:,3]>0)&~solid;da[edge,:3]=da[idx[0][edge],idx[1][edge],:3]
    da[:,:,3]=ba[:,:,3];da[da[:,:,3]==0,:3]=0
    save(brown,ROOT/'source/brown_aligned.png');save(Image.fromarray(da),ROOT/'source/dark_aligned.png')
    save(Image.open(idle_first).convert('RGBA'),ROOT/'source/idle_entry_frame.png')

def state(f):
    change=float(smooth(f/12));eyes=float(smooth((f-3)/9))
    u=max(0,(f-14)/11);scale=1+1.5*u*u;travel=850*u*u*u
    crouch=float(smooth((f-2)/10))*(1-.35*float(smooth((f-14)/5)))
    return change,eyes,scale,travel,crouch

def warp(brown,dark,f):
    change,eyes,scale,travel,crouch=state(f)
    mix=brown*(1-change)+dark*change
    yy,xx=np.mgrid[0:HI,0:HI].astype(np.float32);lx=xx/SS;ly=yy/SS
    # Soft red eye reflections are carried along with the face deformation.
    glow=np.zeros((HI,HI),np.float32)
    for ex,ey in [(228,167),(282,167)]:glow+=np.exp(-(((lx-ex)/10)**2+((ly-ey)/8)**2))*eyes*.23
    mix[:,:,:3]=mix[:,:,:3]*(1-glow[:,:,None])+np.array([255,25,8])*glow[:,:,None]
    mix[:,:,:3]*=mix[:,:,3,None]
    x=256+(lx-256)/scale;y=245+(ly-245-travel)/scale
    head=smooth((270-y)/85);chest=np.exp(-(((x-255)/98)**2+((y-285)/90)**2))*smooth((385-y)/40)
    dx=(x-256)*.022*crouch*head
    dy=(14-(y-230)*.045)*crouch*head+6*crouch*chest
    q=(f-7)/7;tap=8*math.sin(math.pi*q)**4 if 0<q<1 else 0
    dy-=tap*np.exp(-(((x-172)/19)**2+((y-397)/36)**2))
    stride=float(smooth((f-14)/2));phase=(f-14)*1.12
    for cx,cy,offset in [(172,390,0),(296,390,math.pi),(225,378,math.pi),(355,378,0)]:
        k=math.sin(phase+offset);leg=np.exp(-(((x-cx)/20)**2+((y-cy)/42)**2))
        dy-=stride*max(0,k)*12*leg;dx+=stride*k*2.5*leg
    dy-=stride*abs(math.sin(phase))*2.4*chest
    tail=np.exp(-(((x-372)/25)**2+((y-235)/61)**2));dx+=math.sin(f*.55)*3*crouch*tail
    coords=np.array([(y-dy)*SS,(x-dx)*SS],np.float32);out=np.empty_like(mix)
    for ch in range(4):out[:,:,ch]=ndi.map_coordinates(mix[:,:,ch],coords,order=1,mode='constant',cval=0,prefilter=False)
    alpha=out[:,:,3];visible=alpha>1e-7;out[visible,:3]/=alpha[visible,None]
    out[:,:,3]=alpha*255;out=np.round(np.clip(out,0,255)).astype(np.uint8);out[out[:,:,3]==0,:3]=0
    rec={'frame':f+1,'darkTransition':round(change,6),'redEyes':round(eyes,6),'scale':round(scale,6),'forwardTravelY':round(travel,6),'headLowering':round(crouch,6),'bullVisiblePixels':int(np.count_nonzero(out[:,:,3]))}
    return Image.fromarray(out),rec

def dust(f):
    out=Image.new('RGBA',(HI,HI));fade=1-float(smooth((f-22)/4))
    for birth in [14,16,18,20]:
        age=f-birth
        if age<0:continue
        strength=float(smooth(age/2))*fade*.30
        if strength<=0:continue
        for sign in [-1,1]:
            cx=256+sign*(65+age*5);cy=410+age*.65;r=12+age*2.1
            w,h=round(r*3.4*SS),round(r*2.6*SS);yy,xx=np.mgrid[0:h,0:w]
            x=(xx-w/2)/(r*SS);y=(yy-h/2)/(r*SS)
            density=np.zeros((h,w),np.float32)
            for ox,oy,s in [(-.55,.12,.64),(-.12,-.18,.80),(.55,.04,.61)]:
                density+=np.exp(-2.9*(((x-ox)/s)**2+((y-oy)/s)**2))
            a=np.zeros((h,w,4),np.uint8);a[:,:,:3]=[166,156,153]
            a[:,:,3]=np.clip(density*strength*255,0,150).astype(np.uint8)
            out.alpha_composite(Image.fromarray(a),(round(cx*SS-w/2),round(cy*SS-h/2)))
    return out

def main():
    brown=np.array(Image.open(ROOT/'source/brown_aligned.png')).astype(np.float32);brown[:,:,3]/=255
    dark=np.array(Image.open(ROOT/'source/dark_aligned.png')).astype(np.float32);dark[:,:,3]/=255
    frames=[];records=[]
    for f in range(COUNT):
        bull,rec=warp(brown,dark,f);canvas=dust(f);canvas.alpha_composite(bull)
        im=canvas.resize((SIZE,SIZE),R);a=np.array(im);a[a[:,:,3]==0,:3]=0;im=Image.fromarray(a)
        if f==0:im=Image.open(ROOT/'source/idle_entry_frame.png').convert('RGBA')
        if f==26:assert not np.any(np.array(im)), 'Last frame must be blank after full exit.'
        frames.append(im);records.append(rec);save(im,ROOT/f'frames/bull_charge_{f+1:02}.png',compress_level=6)
    print('27 charge frames rendered',flush=True)
    atlas=Image.new('RGBA',(4608,1536));fm={}
    for i,im in enumerate(frames):
        x,y=i%9*512,i//9*512;atlas.paste(im,(x,y))
        fm[f'bull_charge_{i+1:02}.png']={'frame':{'x':x,'y':y,'w':512,'h':512},'rotated':False,'trimmed':False,'spriteSourceSize':{'x':0,'y':0,'w':512,'h':512},'sourceSize':{'w':512,'h':512},'pivot':{'x':.5,'y':.5}}
    save(atlas,ROOT/'bull_charge_atlas_9x3.png',compress_level=6)
    for k in range(3):
        sh=Image.new('RGBA',(1536,1536))
        for j in range(9):sh.paste(frames[k*9+j],(j%3*512,j//3*512))
        save(sh,ROOT/f'sheets/bull_charge_sheet_{k+1:02}.png',compress_level=6)
    (ROOT/'bull_charge_atlas_9x3.json').write_text(json.dumps({'frames':fm,'animations':{'bull_charge':list(fm)},'meta':{'image':'bull_charge_atlas_9x3.png','format':'RGBA8888','size':{'w':4608,'h':1536},'scale':'1','frameRate':24}},indent=2))
    (ROOT/'source/motion.json').write_text(json.dumps({'fps':24,'durationMs':1125,'loop':False,'frames':records},indent=2))
    save(frames[0],ROOT/'bull_charge.apng',save_all=True,append_images=frames[1:],duration=[42,41,42]*9,loop=1,blend=0,disposal=0)
    preview=[]
    for im in frames:
        row=Image.new('RGB',(720,360))
        for j,bg in enumerate(['#090d18','#4b1b75']):
            tile=Image.new('RGBA',(360,360),bg);tile.alpha_composite(im.resize((360,360),R));row.paste(tile,(j*360,0))
        preview.append(row)
    save(preview[0],ROOT/'preview/bull_charge_dark_and_purple.gif',save_all=True,append_images=preview[1:],duration=[60]*26+[800],loop=0,disposal=2)
    contact=Image.new('RGB',(9*160,3*180),'#0b101c');dr=ImageDraw.Draw(contact)
    for i,im in enumerate(frames):
        x,y=i%9*160,i//9*180;thumb=im.resize((160,160),R);contact.paste(thumb,(x,y+20),thumb);dr.text((x+6,y+4),f'{i+1:02}',fill='#a9b7c7')
    save(contact,ROOT.parent/'qa/bull_charge_contact.jpg',quality=95)
    validate(frames,records)
    with zipfile.ZipFile(ROOT.parent/'bull_dark_charge_animation_pack.zip','w',zipfile.ZIP_DEFLATED,compresslevel=4) as z:
        for p in sorted(ROOT.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.writing'):z.write(p,p.relative_to(ROOT.parent))
    print('ZIP ready',flush=True)

def validate(frames,records):
    atlas=Image.open(ROOT/'bull_charge_atlas_9x3.png');assert atlas.mode=='RGBA' and atlas.size==(4608,1536)
    anim=Image.open(ROOT/'bull_charge.apng');assert anim.n_frames==27
    rows=[];duration=0
    for i,refim in enumerate(frames):
        im=Image.open(ROOT/f'frames/bull_charge_{i+1:02}.png');a=np.array(im);ref=np.array(refim)
        assert im.mode=='RGBA' and im.size==(512,512) and np.array_equal(a,ref)
        assert a[:,:,3].min()==0 and not np.any(a[a[:,:,3]==0,:3])
        x,y=i%9*512,i//9*512;assert np.array_equal(np.array(atlas.crop((x,y,x+512,y+512))),ref)
        sh=Image.open(ROOT/f'sheets/bull_charge_sheet_{i//9+1:02}.png');assert sh.mode=='RGBA' and sh.size==(1536,1536)
        j=i%9;x,y=j%3*512,j//3*512;assert np.array_equal(np.array(sh.crop((x,y,x+512,y+512))),ref)
        anim.seek(i);duration+=anim.info['duration'];assert np.array_equal(np.array(anim.convert('RGBA')),ref)
        rows.append({'frame':i+1,'nonzeroAlphaPixels':int(np.count_nonzero(a[:,:,3])),'bullVisiblePixelsAt2x':records[i]['bullVisiblePixels']})
    assert duration==1125
    assert not np.any(np.array(frames[-1])) and records[-1]['bullVisiblePixels']==0 and records[-2]['bullVisiblePixels']==0
    assert np.array_equal(np.array(frames[0]),np.array(Image.open(ROOT/'source/idle_entry_frame.png')))
    assert all(records[i+1]['darkTransition']>=records[i]['darkTransition'] for i in range(26))
    assert len({hashlib.sha256(np.array(im).tobytes()).hexdigest() for im in frames})==27
    report={'passed':True,'frameCount':27,'frameSize':[512,512],'atlasSize':[4608,1536],'threeSmallSheets':[1536,1536],'fps':24,'durationMs':1125,'alphaVerified':True,'firstFrameMatchesIdleExactly':True,'finalFrameAllRGBAZero':True,'bullFullyOutsideCanvasBeforeFinalFrame':True,'allExportsPixelExact':True,'frames':rows}
    (ROOT/'validation.json').write_text(json.dumps(report,indent=2));print('Verified transparency, exact sheets/APNG, idle entry, full bull exit, and blank last frame.',flush=True)

if __name__=='__main__':main()
