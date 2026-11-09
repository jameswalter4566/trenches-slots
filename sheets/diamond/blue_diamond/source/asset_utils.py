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

def export(kind,frames,records):
    dest=ROOT/kind;dest.mkdir(parents=True,exist_ok=True);names=[];meta={}
    atlas=Image.new('RGBA',(4608,1536))
    for i,im in enumerate(frames):
        name=f'diamond_{kind}_{i+1:02}.png';names.append(name);save(im,dest/'frames'/name,compress_level=6)
        x,y=i%9*S,i//9*S;atlas.paste(im,(x,y))
        meta[name]={'frame':{'x':x,'y':y,'w':S,'h':S},'rotated':False,'trimmed':False,'spriteSourceSize':{'x':0,'y':0,'w':S,'h':S},'sourceSize':{'w':S,'h':S},'pivot':{'x':.5,'y':.5}}
    save(atlas,dest/f'diamond_{kind}_atlas_9x3.png',compress_level=6)
    for k in range(3):
        sheet=Image.new('RGBA',(1536,1536))
        for j in range(9):sheet.paste(frames[k*9+j],(j%3*S,j//3*S))
        save(sheet,dest/f'sheets/diamond_{kind}_sheet_{k+1:02}.png',compress_level=6)
    (dest/f'diamond_{kind}_atlas_9x3.json').write_text(json.dumps({'frames':meta,'animations':{f'diamond_{kind}':names},'meta':{'image':f'diamond_{kind}_atlas_9x3.png','format':'RGBA8888','size':{'w':4608,'h':1536},'scale':'1','frameRate':FPS,'loop':kind=='idle'}},indent=2))
    (dest/'motion.json').write_text(json.dumps({'fps':FPS,'durationMs':1125,'loop':kind=='idle','frames':records},indent=2))
    save(frames[0],dest/f'diamond_{kind}.apng',save_all=True,append_images=frames[1:],duration=[42,41,42]*9,loop=0 if kind=='idle' else 1,blend=0,disposal=0)

def validate(kind,frames):
    dest=ROOT/kind;atlas=Image.open(dest/f'diamond_{kind}_atlas_9x3.png');assert atlas.size==(4608,1536) and atlas.mode=='RGBA'
    apng=Image.open(dest/f'diamond_{kind}.apng');assert apng.n_frames==N
    rows=[];duration=0
    for i,ref in enumerate(frames):
        im=Image.open(dest/f'frames/diamond_{kind}_{i+1:02}.png');a=np.array(im)
        assert im.mode=='RGBA' and im.size==(S,S) and np.array_equal(a,np.array(ref))
        alpha=a[:,:,3];assert alpha.min()==0
        assert not np.any(a[alpha==0,:3]);assert not np.any(alpha[[0,-1],:]) and not np.any(alpha[:,[0,-1]])
        if kind=='idle' or i<26:assert alpha.max()>0 and np.any((alpha>0)&(alpha<255))
        x,y=i%9*S,i//9*S;assert np.array_equal(np.array(atlas.crop((x,y,x+S,y+S))),a)
        sheet=Image.open(dest/f'sheets/diamond_{kind}_sheet_{i//9+1:02}.png');assert sheet.size==(1536,1536) and sheet.mode=='RGBA'
        j=i%9;x,y=j%3*S,j//3*S;assert np.array_equal(np.array(sheet.crop((x,y,x+S,y+S))),a)
        apng.seek(i);duration+=apng.info['duration'];assert np.array_equal(np.array(apng.convert('RGBA')),a)
        rows.append({'frame':i+1,'bounds':im.getbbox(),'transparentPixels':int((alpha==0).sum()),'partialAlphaPixels':int(((alpha>0)&(alpha<255)).sum())})
    assert duration==1125 and len({hashlib.sha256(np.array(f).tobytes()).hexdigest() for f in frames})==N
    if kind=='glow':assert not np.any(np.array(frames[-1]))
    return {'passed':True,'frames':N,'frameSize':[512,512],'atlasSize':[4608,1536],'smallSheets':3,'alphaVerified':True,'noEdgeClipping':True,'pixelExactAtlasesSheetsAPNG':True,'finalFrameBlank':kind=='glow','durationMs':duration,'perFrame':rows}

def previews(allframes):
    seq=allframes['idle']+allframes['glow'];out=[]
    for im in seq:
        row=Image.new('RGB',(800,400))
        for j,color in enumerate(['#0a0e19','#472067']):
            tile=Image.new('RGBA',(400,400),color);tile.alpha_composite(im.resize((400,400),R));row.paste(tile,(j*400,0))
        out.append(row)
    save(out[0],ROOT/'preview/diamond_idle_then_glow.gif',save_all=True,append_images=out[1:],duration=[50]*27+[60]*26+[650],loop=0,disposal=2)
    for kind,frames in allframes.items():
        contact=Image.new('RGB',(1350,510),'#0a0e19');d=ImageDraw.Draw(contact)
        for i,im in enumerate(frames):
            x,y=i%9*150,i//9*170;thumb=im.resize((150,150),R);contact.paste(thumb,(x,y+20),thumb);d.text((x+6,y+4),f'{i+1:02}',fill='#bcc6d5')
        save(contact,ROOT.parent/f'qa/diamond_{kind}_contact.jpg',quality=94)
