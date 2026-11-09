"""Validate all production PNGs and animated previews; write validation.json."""
from pathlib import Path
from PIL import Image
import numpy as np, json, hashlib

r=Path(__file__).resolve().parents[1]
frames=[]; report=[]
a=Image.open(r/'rocket_atlas_9x3.png'); assert a.mode=='RGBA' and a.size==(4608,1536)
for i in range(27):
    p=r/f'frames/rocket_{i+1:02}.png'; im=Image.open(p); ar=np.array(im); alpha=ar[:,:,3]
    assert im.mode=='RGBA' and im.size==(512,512)
    assert alpha.min()==0 and alpha.max()>0 and np.any((alpha>0)&(alpha<255))
    assert all(alpha[y,x]==0 for y,x in [(0,0),(0,511),(511,0),(511,511)])
    assert not np.any(ar[alpha==0,:3])
    assert not np.any(alpha[:,0]) and not np.any(alpha[:,-1])
    assert np.array_equal(np.array(a.crop(((i%9)*512,(i//9)*512,(i%9+1)*512,(i//9+1)*512))),ar)
    sheet=Image.open(next((r/'sheets').glob(f'rocket_sheet_{i//9+1:02}_*.png')))
    k=i%9;assert sheet.mode=='RGBA' and sheet.size==(1536,1536)
    assert np.array_equal(np.array(sheet.crop(((k%3)*512,(k//3)*512,(k%3+1)*512,(k//3+1)*512))),ar)
    report.append({'file':p.name,'mode':im.mode,'size':list(im.size),'transparentPixels':int((alpha==0).sum()),'partialAlphaPixels':int(((alpha>0)&(alpha<255)).sum()),'alphaMin':int(alpha.min()),'alphaMax':int(alpha.max()),'cornersTransparent':True,'atlasMatches':True,'sheetMatches':True})
    frames.append(ar)
assert len(list((r/'frames').glob('*.png')))==27
assert len({hashlib.sha256(f.tobytes()).hexdigest() for f in frames})==27
for ext in ['apng','webp']:
    anim=Image.open(r/f'preview/rocket_launch.{ext}');assert anim.n_frames==27
    duration=0
    for i in range(27):
        anim.seek(i); ar=np.array(anim.convert('RGBA')); duration+=anim.info.get('duration',0)
        assert np.array_equal(ar[:,:,3],frames[i][:,:,3])
        visible=ar[:,:,3]>0;assert np.array_equal(ar[visible],frames[i][visible])
    if ext=='apng':assert duration==1125
motion=json.loads((r/'source/motion.json').read_text())['frames']
assert all(m['rocketCenterX']==256 and m['rotation']==0 for m in motion)
assert all(m['rocketCenterY']==256 for m in motion[:9])
assert all(motion[i+1]['rocketCenterY']<=motion[i]['rocketCenterY'] for i in range(26))
assert all(not m['rocketVisible'] for m in motion[24:])
summary={'passed':True,'frameCount':27,'uniqueFrames':27,'frameSize':[512,512],'atlasSize':[4608,1536],'layout':[9,3],'smallSheetCount':3,'smallSheetSize':[1536,1536],'fps':24,'durationMs':1125,'pngColorMode':'RGBA','transparentBackgroundVerified':True,'atlasAndSheetsPixelExact':True,'apngAndWebpPixelExact':True,'rocketFixedHorizontalCenter':256,'noRotation':True,'singleMasterSha256':hashlib.sha256((r/'source/rocket_master.png').read_bytes()).hexdigest(),'frames':report}
(r/'validation.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k!='frames'},indent=2))
