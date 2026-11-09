"""Build a 27-frame seamless bull idle from one master. Pillow/NumPy/SciPy."""
from pathlib import Path
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
import numpy as np
import math, io, os, json, hashlib, zipfile

ROOT=Path(__file__).resolve().parents[1]
SIZE=512; SS=2; HI=SIZE*SS; COUNT=27; FPS=24
R=Image.Resampling.LANCZOS

def save(im,path,**kw):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    b=io.BytesIO();im.save(b,format={'.png':'PNG','.apng':'PNG','.gif':'GIF','.jpg':'JPEG'}[path.suffix],**kw)
    tmp=path.with_name(path.name+'.writing');tmp.write_bytes(b.getvalue());os.replace(tmp,path)

def smooth(t):
    t=np.clip(t,0,1);return t*t*(3-2*t)

def prepare(source):
    ar=np.array(Image.open(source).convert('RGBA'))
    labels,_=ndi.label(ar[:,:,3]>180);counts=np.bincount(labels.ravel());counts[0]=0
    mask=labels==counts.argmax()
    mask=ndi.binary_opening(mask,iterations=3)
    mask=ndi.binary_fill_holes(ndi.binary_closing(mask,iterations=3))
    mask=ndi.binary_erosion(mask,iterations=1)
    alpha=np.round(ndi.gaussian_filter(mask.astype(float),.9)*255).astype(np.uint8);alpha[alpha<2]=0
    core=mask&(ar[:,:,3]>=245);_,idx=ndi.distance_transform_edt(~core,return_indices=True)
    edge=(alpha>0)&~core;ar[edge,:3]=ar[idx[0][edge],idx[1][edge],:3]
    ar[:,:,3]=alpha;ar[alpha==0,:3]=0
    master=Image.fromarray(ar);save(master,ROOT/'source/bull_master.png')
    return master

def neutral_canvas(master):
    box=master.getbbox();crop=master.crop(box)
    height=336;scale=height/crop.height
    sprite=crop.resize((round(crop.width*scale*SS),height*SS),R)
    # The face axis is fixed at x=256; the tail naturally extends rightward.
    originx=256-(620-box[0])*scale
    canvas=Image.new('RGBA',(HI,HI));canvas.alpha_composite(sprite,(round(originx*SS),78*SS))
    save(canvas.resize((512,512),R),ROOT/'source/bull_neutral_512.png')
    return canvas

def fields(frame):
    t=frame/COUNT;p=math.tau*t;breathe=math.sin(p);tail=math.sin(2*p)
    y,x=np.mgrid[0:HI,0:HI].astype(np.float32);x/=SS;y/=SS
    planted=smooth((384-y)/38)
    chest=np.exp(-(((x-255)/100)**2+((y-286)/92)**2))*planted
    head=smooth((264-y)/76)
    angle=math.radians(.55)*math.sin(p)
    dx=(x-256)*.014*breathe*chest-(y-246)*angle*head+.65*breathe*head
    dy=-2.3*breathe*chest+(x-256)*angle*head-1.3*breathe*head
    tailmask=np.exp(-(((x-372)/24)**2+((y-235)/59)**2))
    dx+=3.6*tail*tailmask;dy-=1.4*tail*tailmask
    q=(t-.43)/.34
    tap=6.0*math.sin(math.pi*q)**4 if 0<q<1 else 0.
    hoofmask=np.exp(-(((x-172)/19)**2+((y-397)/34)**2))
    dy-=tap*hoofmask
    coords=np.array([(y-dy)*SS,(x-dx)*SS],dtype=np.float32)
    return coords,{'frame':frame+1,'breath':round(breathe,6),'headAngleDegrees':round(math.degrees(angle),6),'frontHoofLiftPx':round(tap,6),'tailSwingPx':round(3.6*tail,6)}

def render(premult,frame):
    coords,record=fields(frame)
    out=np.empty_like(premult)
    for ch in range(4):out[:,:,ch]=ndi.map_coordinates(premult[:,:,ch],coords,order=1,mode='constant',cval=0,prefilter=False)
    alpha=out[:,:,3];valid=alpha>1e-7
    out[valid,:3]/=alpha[valid,None]
    out[:,:,:3]=np.clip(out[:,:,:3],0,255);out[:,:,3]=np.clip(alpha*255,0,255)
    im=Image.fromarray(np.round(out).astype(np.uint8)).resize((SIZE,SIZE),R)
    a=np.array(im);a[a[:,:,3]==0,:3]=0
    return Image.fromarray(a),record

def validate(frames,records,premult):
    atlas=Image.open(ROOT/'bull_idle_atlas_9x3.png');assert atlas.mode=='RGBA' and atlas.size==(4608,1536)
    anim=Image.open(ROOT/'bull_idle.apng');assert anim.n_frames==27 and anim.info['loop']==0
    rows=[];duration=0
    for i,refim in enumerate(frames):
        p=ROOT/f'frames/bull_idle_{i+1:02}.png';im=Image.open(p);a=np.array(im);ref=np.array(refim)
        assert im.mode=='RGBA' and im.size==(512,512) and np.array_equal(a,ref)
        alpha=a[:,:,3];assert alpha.min()==0 and alpha.max()==255 and np.any((alpha>0)&(alpha<255))
        assert not np.any(a[alpha==0,:3])
        assert not np.any(alpha[[0,-1],:]) and not np.any(alpha[:,[0,-1]])
        x,y=i%9*512,i//9*512;assert np.array_equal(np.array(atlas.crop((x,y,x+512,y+512))),ref)
        sheet=Image.open(ROOT/f'sheets/bull_idle_sheet_{i//9+1:02}.png');assert sheet.size==(1536,1536)
        j=i%9;x,y=j%3*512,j//3*512;assert np.array_equal(np.array(sheet.crop((x,y,x+512,y+512))),ref)
        anim.seek(i);duration+=anim.info['duration'];assert np.array_equal(np.array(anim.convert('RGBA')),ref)
        rows.append({'frame':i+1,'transparentPixels':int((alpha==0).sum()),'partialAlphaPixels':int(((alpha>0)&(alpha<255)).sum()),'bounds':list(im.getbbox())})
    assert duration==1125 and len({hashlib.sha256(np.array(im).tobytes()).hexdigest() for im in frames})==27
    wrapped,_=render(premult,27);assert np.array_equal(np.array(wrapped),np.array(frames[0]))
    report={'passed':True,'frames':27,'frameSize':[512,512],'atlasSize':[4608,1536],'smallSheets':3,'smallSheetSize':[1536,1536],'fps':24,'durationMs':1125,'loop':True,'alphaVerified':True,'pixelExactAtlasesSheetsAPNG':True,'allFramesFullyInsideCanvas':True,'wrapMatchesFirstFrameExactly':True,'masterSha256':hashlib.sha256((ROOT/'source/bull_master.png').read_bytes()).hexdigest(),'perFrame':rows}
    (ROOT/'validation.json').write_text(json.dumps(report,indent=2));print('Validation passed: 27 transparent frames, all sheets, APNG, seamless wrap.',flush=True)

def main():
    master=Image.open(ROOT/'source/bull_master.png').convert('RGBA');base=neutral_canvas(master)
    a=np.array(base).astype(np.float32);a[:,:,3]/=255.;a[:,:,:3]*=a[:,:,3,None]
    frames=[];records=[]
    for f in range(COUNT):
        im,rec=render(a,f);frames.append(im);records.append(rec)
        save(im,ROOT/f'frames/bull_idle_{f+1:02}.png',compress_level=6)
    print('All 27 frames rendered',flush=True)
    atlas=Image.new('RGBA',(4608,1536));fm={}
    for i,im in enumerate(frames):
        x,y=i%9*512,i//9*512;atlas.paste(im,(x,y))
        fm[f'bull_idle_{i+1:02}.png']={'frame':{'x':x,'y':y,'w':512,'h':512},'rotated':False,'trimmed':False,'spriteSourceSize':{'x':0,'y':0,'w':512,'h':512},'sourceSize':{'w':512,'h':512},'pivot':{'x':.5,'y':.5}}
    save(atlas,ROOT/'bull_idle_atlas_9x3.png',compress_level=6)
    for k in range(3):
        sheet=Image.new('RGBA',(1536,1536))
        for i in range(9):sheet.paste(frames[k*9+i],(i%3*512,i//3*512))
        save(sheet,ROOT/f'sheets/bull_idle_sheet_{k+1:02}.png',compress_level=6)
    (ROOT/'bull_idle_atlas_9x3.json').write_text(json.dumps({'frames':fm,'animations':{'bull_idle':list(fm)},'meta':{'image':'bull_idle_atlas_9x3.png','format':'RGBA8888','size':{'w':4608,'h':1536},'scale':'1','frameRate':24}},indent=2))
    (ROOT/'source/motion.json').write_text(json.dumps({'fps':24,'durationMs':1125,'loop':True,'frames':records},indent=2))
    save(frames[0],ROOT/'bull_idle.apng',save_all=True,append_images=frames[1:],duration=[42,41,42]*9,loop=0,blend=0,disposal=0)
    review=[]
    for im in frames:
        row=Image.new('RGB',(720,360))
        for j,bg in enumerate(['#090d18','#4b1b75']):
            tile=Image.new('RGBA',(360,360),bg);tile.alpha_composite(im.resize((360,360),R));row.paste(tile,(j*360,0))
        review.append(row)
    save(review[0],ROOT/'preview/bull_idle_dark_and_purple.gif',save_all=True,append_images=review[1:],duration=[40]*27,loop=0,disposal=2)
    contact=Image.new('RGB',(1350,510),'#0b101c');draw=ImageDraw.Draw(contact)
    for i,im in enumerate(frames):
        x,y=i%9*150,i//9*170;thumb=im.resize((150,150),R);contact.paste(thumb,(x,y+20),thumb);draw.text((x+6,y+4),f'{i+1:02}',fill='#a9b7c7')
    save(contact,ROOT.parent/'qa/bull_idle_contact.jpg',quality=94)
    validate(frames,records,a)
    with zipfile.ZipFile(ROOT.parent/'bull_idle_animation_pack.zip','w',zipfile.ZIP_DEFLATED,compresslevel=4) as z:
        for p in sorted(ROOT.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.writing'):z.write(p,p.relative_to(ROOT.parent))
    print('ZIP ready',flush=True)

if __name__=='__main__':main()
