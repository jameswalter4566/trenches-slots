"""Articulated rear-and-slam with original body/head and matching folded legs."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi
import numpy as np
import math, io, os, json, zipfile, hashlib

ROOT=Path(__file__).resolve().parents[1]
S=512; SS=2; HI=S*SS; N=27; FPS=24; R=Image.Resampling.LANCZOS
LEGS=[
 {'name':'left','root':(177,286),'knee':(172,345),'ankle':(173,383),'tip':(169,412),'sign':1,'poly':[(148,279),(165,275),(190,284),(204,300),(209,316),(205,330),(195,345),(188,360),(187,373),(194,385),(198,401),(193,416),(137,416),(138,396),(148,381),(152,366),(151,350),(148,335),(143,317),(143,296)]},
 {'name':'right','root':(300,286),'knee':(289,345),'ankle':(292,383),'tip':(296,413),'sign':-1,'poly':[(286,279),(305,271),(320,275),(327,287),(325,306),(318,325),(308,339),(307,355),(307,371),(313,383),(320,396),(320,416),(266,416),(266,396),(275,383),(279,370),(277,354),(273,341),(268,329),(266,317),(272,302)]}
]

def save(im,path,**kw):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 b=io.BytesIO();im.save(b,format={'.png':'PNG','.apng':'PNG','.gif':'GIF','.jpg':'JPEG'}[path.suffix],**kw)
 tmp=path.with_name(path.name+'.writing');tmp.write_bytes(b.getvalue());os.replace(tmp,path)

def smooth(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)

FOLDED={'left':{'root':(350,463),'tip':(435,725),'poly':[(315,452),(353,444),(405,473),(444,480),(460,515),(458,547),(467,575),(477,613),(496,635),(513,685),(495,707),(433,733),(371,738),(362,690),(356,660),(351,638),(320,631),(291,607),(277,572),(280,520),(292,484)]},'right':{'root':(800,485),'tip':(648,716),'poly':[(777,470),(817,475),(843,507),(857,551),(842,603),(813,635),(750,654),(725,701),(712,725),(644,725),(577,698),(588,652),(612,613),(628,567),(644,524),(678,490),(714,478)]}}

def prepare_folded(path):
 im=Image.open(path).convert('RGBA');a=np.array(im)
 for name,leg in FOLDED.items():
  m=Image.new('L',im.size);ImageDraw.Draw(m).polygon(leg['poly'],fill=255)
  mask=np.array(m.filter(ImageFilter.GaussianBlur(.7))).astype(float)/255
  b=a.copy();b[:,:,3]=np.round(b[:,:,3]*mask).astype(np.uint8);b[b[:,:,3]==0,:3]=0
  save(Image.fromarray(b),ROOT/f'source/{name}_folded_keypose.png')

def folded_transform(im,name,root,tip):
 leg=FOLDED[name];src=np.array(leg['tip'])-np.array(leg['root']);dst=np.array(tip)-np.array(root)
 scale=np.linalg.norm(dst)/np.linalg.norm(src);angle=math.atan2(dst[1],dst[0])-math.atan2(src[1],src[0]);c,s=math.cos(angle),math.sin(angle)
 tx,ty=root;sx,sy=leg['root']
 mat=(c/(scale*SS),s/(scale*SS),sx-(c*tx+s*ty)/scale,-s/(scale*SS),c/(scale*SS),sy+(s*tx-c*ty)/scale)
 return im.convert('RGBa').transform((HI,HI),Image.Transform.AFFINE,mat,resample=Image.Resampling.BICUBIC).convert('RGBA')

def prepare(master_path,entry_path):
 master=Image.open(master_path).convert('RGBA');box=master.getbbox();crop=master.crop(box);scale=336/crop.height
 sprite=crop.resize((round(crop.width*scale*SS),336*SS),R)
 base=Image.new('RGBA',(HI,HI));base.alpha_composite(sprite,(round((256-(620-box[0])*scale)*SS),78*SS))
 save(base,ROOT/'source/bull_original_aligned.png')
 save(Image.open(entry_path).convert('RGBA'),ROOT/'source/idle_entry_frame.png')
 a=np.array(base);yy,xx=np.mgrid[0:HI,0:HI];x=xx/SS;y=yy/SS;removed=np.zeros((HI,HI),bool)
 for leg in LEGS:
  maskim=Image.new('L',(HI,HI));ImageDraw.Draw(maskim).polygon([(round(px*SS),round(py*SS)) for px,py in leg['poly']],fill=255)
  mask=np.array(maskim)>0;removed|=mask
  kx,ky=leg['knee'];ax,ay=leg['ankle']
  kneecap=(x-kx)**2+(y-ky)**2<19**2
  anklecap=(x-ax)**2+(y-ay)**2<14**2
  masks={'upper':mask&(y<=ky+5),'lower':mask&(y>=ky-5)&(y<=ay+3),'hoof':mask&(y>=ay-3),'knee_cap':mask&((x-kx)**2+(y-ky)**2<17**2),'ankle_cap':mask&((x-ax)**2+(y-ay)**2<11**2)}
  for part,m in masks.items():
   b=a.copy();b[~m]=0;save(Image.fromarray(b),ROOT/f'source/{leg["name"]}_{part}.png')
 # Retain the complete shoulders as overlap backing. Remove only the vacated
 # lower forelegs; generous clearances prevent stray edge pixels below the arms.
 left_bottom=295+34*np.sqrt(np.clip(1-((x-175)/34)**2,0,1))
 right_bottom=295+33*np.sqrt(np.clip(1-((x-295)/33)**2,0,1))
 clear=((x<209)&(x>122)&(y>=left_bottom))|((x>262)&(x<328)&(y>=right_bottom))
 body=a.copy();body[clear]=0;save(Image.fromarray(body),ROOT/'source/body_plate.png')
 (ROOT/'source/rig.json').write_text(json.dumps({'canvas':[512,512],'scale':SS,'legs':LEGS},indent=2))

def timeline(f):
 if f<=4: rear=0.;dip=8*float(smooth(f/4))
 elif f<=11:rear=float(smooth((f-4)/7));dip=8*(1-rear)
 elif f<=13:rear=1.-(f-11)*.003;dip=0.
 elif f<=17:rear=1-((f-13)/4)**2;dip=12*float(smooth((f-16)/1))
 else:
  rear=0.;dip={18:7.,19:-4.,20:-1.5,21:1.,22:0.,23:0.,24:0.,25:0.,26:0.}[f]
 fade=1-float(smooth((f-23)/3))
 return rear,dip,fade

def offset(y,rear,dip):
 return (-48*rear+dip)*smooth((414-y)/150)

def rotated(v,deg):
 a=math.radians(deg);c,s=math.cos(a),math.sin(a)
 return np.array([c*v[0]-s*v[1],s*v[0]+c*v[1]])

def transform_piece(im,source_pivot,target_pivot,deg):
 a=math.radians(deg);c,s=math.cos(a),math.sin(a);sx,sy=source_pivot;tx,ty=target_pivot
 mat=(c,s,(sx-c*tx-s*ty)*SS,-s,c,(sy+s*tx-c*ty)*SS)
 return im.convert('RGBa').transform((HI,HI),Image.Transform.AFFINE,mat,resample=Image.Resampling.BICUBIC).convert('RGBA')

def body_pose(premult,rear,dip):
 # Invert a monotonic vertical deformation; head pixels translate without recoloring.
 ys=np.arange(HI,dtype=np.float32)/SS;forward=ys+offset(ys,rear,dip)
 inv=np.interp(ys,forward,ys).astype(np.float32)*SS
 yy,xx=np.mgrid[0:HI,0:HI].astype(np.float32);coords=np.array([np.broadcast_to(inv[:,None],xx.shape),xx])
 out=np.empty_like(premult)
 for c in range(4):out[:,:,c]=ndi.map_coordinates(premult[:,:,c],coords,order=1,mode='constant',cval=0,prefilter=False)
 a=out[:,:,3];visible=a>1e-7;out[visible,:3]/=a[visible,None];out[:,:,3]*=255
 out=np.round(np.clip(out,0,255)).astype(np.uint8);out[out[:,:,3]==0,:3]=0
 return Image.fromarray(out)

def star(draw,x,y,r,opacity):
 points=[(x,y-r),(x+r*.22,y-r*.22),(x+r*.65,y),(x+r*.22,y+r*.22),(x,y+r),(x-r*.22,y+r*.22),(x-r*.65,y),(x-r*.22,y-r*.22)]
 draw.polygon([(round(a*SS),round(b*SS)) for a,b in points],fill=(255,204,61,round(opacity)))

def effects(f):
 out=Image.new('RGBA',(HI,HI));front=Image.new('RGBA',(HI,HI));age=f-17
 if age<0:return out,front
 strength=1-float(smooth(age/9));d=ImageDraw.Draw(front)
 for j,cx in enumerate([169,296]):
  if age<=3:
   glow=Image.new('RGBA',(HI,HI));gd=ImageDraw.Draw(glow);rx=13+age*5;ry=6+age*2
   gd.ellipse(((cx-rx)*SS,(410-ry)*SS,(cx+rx)*SS,(410+ry)*SS),fill=(255,210,90,round(175*(1-age/4))))
   out.alpha_composite(glow.filter(ImageFilter.GaussianBlur(6*SS)))
  for k in range(8):
   ang=math.radians(202+k*19+j*5);speed=8+(k%3)*3
   radius=10+age*speed;px=cx+math.cos(ang)*radius;py=409+math.sin(ang)*radius+age*age*.55
   star(d,px,py,3.5+(k%3),230*strength)
   if age<5:d.line((cx*SS,409*SS,px*SS,py*SS),fill=(255,173,25,round(85*strength)),width=SS)
 # The impact expands along the ground plane.
 if age<7:
  radius=30+age*25;ry=7+age*3.5
  d.ellipse(((234-radius)*SS,(412-ry)*SS,(234+radius)*SS,(412+ry)*SS),outline=(255,207,90,round(135*(1-age/7))),width=2*SS)
 # Persistent dust travels away from the two impact points and fades naturally.
 for side,cx in [(-1,165),(1,302)]:
  r=13+age*3;w,h=round(r*4*SS),round(r*2.6*SS);yy,xx=np.mgrid[0:h,0:w]
  x=(xx-w/2)/(r*SS);y=(yy-h/2)/(r*SS);density=np.zeros((h,w),np.float32)
  for ox,oy,rr in [(-.6,.07,.67),(0,-.12,.9),(.55,.08,.63)]:density+=np.exp(-3*(((x-ox)/rr)**2+((y-oy)/rr)**2))
  a=np.zeros((h,w,4),np.uint8);a[:,:,:3]=[191,166,129]
  a[:,:,3]=np.clip(density*.34*float(smooth((age+.4)/2))*strength*255,0,145).astype(np.uint8)
  out.alpha_composite(Image.fromarray(a),(round((cx+side*age*7)*SS-w/2),round(414*SS-h/2)))
 return out,front

def render(parts,body,f):
 rear,dip,fade=timeline(f);back,front=effects(f);character=body_pose(body,rear,dip);tips=[]
 for leg in LEGS:
  sign=leg['sign'];root=np.array(leg['root'],float);root[1]+=float(offset(root[1],rear,dip))
  upper_angle=12*sign*rear;lower_angle=-105*sign*rear;hoof_angle=-8*sign*rear
  knee=root+rotated(np.array(leg['knee'])-np.array(leg['root']),upper_angle)
  ankle=knee+rotated(np.array(leg['ankle'])-np.array(leg['knee']),lower_angle)
  tip=ankle+rotated(np.array(leg['tip'])-np.array(leg['ankle']),hoof_angle);tips.append(tip.tolist())
  limb=Image.new('RGBA',(HI,HI))
  for part,sp,tp,ang in [('upper',leg['root'],root,upper_angle),('lower',leg['knee'],knee,lower_angle),('knee_cap',leg['knee'],knee,(upper_angle+lower_angle)*.5),('ankle_cap',leg['ankle'],ankle,hoof_angle),('hoof',leg['ankle'],ankle,hoof_angle)]:
   limb.alpha_composite(transform_piece(parts[(leg['name'],part)],sp,tp,ang))
  blend=float(smooth((rear-.50)/.40))
  if blend>0:
   folded=folded_transform(parts[(leg['name'],'folded_keypose')],leg['name'],root,tip)
   limb=Image.blend(limb.convert('RGBa'),folded.convert('RGBa'),blend).convert('RGBA')
  character.alpha_composite(limb)
 back.alpha_composite(character);back.alpha_composite(front)
 a=np.array(back.resize((S,S),R));a[:,:,3]=np.round(a[:,:,3].astype(float)*fade).astype(np.uint8);a[a[:,:,3]==0,:3]=0
 im=Image.fromarray(a)
 if f==0:im=Image.open(ROOT/'source/idle_entry_frame.png').convert('RGBA')
 rec={'frame':f+1,'rearAmount':round(rear,6),'bodyDipPx':round(dip,4),'opacity':round(fade,6),'frontHoofTips':[[round(v,4) for v in tip] for tip in tips],'coatRecoloring':False}
 return im,rec

def main():
 parts={(leg['name'],part):Image.open(ROOT/f'source/{leg["name"]}_{part}.png').convert('RGBA') for leg in LEGS for part in ['upper','lower','hoof','knee_cap','ankle_cap','folded_keypose']}
 body=np.array(Image.open(ROOT/'source/body_plate.png')).astype(np.float32);body[:,:,3]/=255;body[:,:,:3]*=body[:,:,3,None]
 frames=[];records=[]
 for f in range(N):
  im,rec=render(parts,body,f);frames.append(im);records.append(rec);save(im,ROOT/f'frames/bull_slam_{f+1:02}.png',compress_level=6)
 print('27 articulated frames rendered',flush=True)
 atlas=Image.new('RGBA',(4608,1536));fm={}
 for i,im in enumerate(frames):
  x,y=i%9*512,i//9*512;atlas.paste(im,(x,y));fm[f'bull_slam_{i+1:02}.png']={'frame':{'x':x,'y':y,'w':512,'h':512},'rotated':False,'trimmed':False,'spriteSourceSize':{'x':0,'y':0,'w':512,'h':512},'sourceSize':{'w':512,'h':512},'pivot':{'x':.5,'y':.5}}
 save(atlas,ROOT/'bull_slam_atlas_9x3.png',compress_level=6)
 for k in range(3):
  sh=Image.new('RGBA',(1536,1536))
  for j in range(9):sh.paste(frames[k*9+j],(j%3*512,j//3*512))
  save(sh,ROOT/f'sheets/bull_slam_sheet_{k+1:02}.png',compress_level=6)
 (ROOT/'bull_slam_atlas_9x3.json').write_text(json.dumps({'frames':fm,'animations':{'bull_slam':list(fm)},'meta':{'image':'bull_slam_atlas_9x3.png','format':'RGBA8888','size':{'w':4608,'h':1536},'scale':'1','frameRate':24}},indent=2))
 (ROOT/'source/motion.json').write_text(json.dumps({'fps':24,'durationMs':1125,'loop':False,'frames':records},indent=2))
 save(frames[0],ROOT/'bull_slam.apng',save_all=True,append_images=frames[1:],duration=[42,41,42]*9,loop=1,disposal=0,blend=0)
 review=[]
 for im in frames:
  row=Image.new('RGB',(768,384))
  for j,bg in enumerate(['#0b101c','#4b1b75']):
   tile=Image.new('RGBA',(384,384),bg);tile.alpha_composite(im.resize((384,384),R));row.paste(tile,(384*j,0))
  review.append(row)
 save(review[0],ROOT/'preview/bull_rear_slam.gif',save_all=True,append_images=review[1:],duration=[70]*26+[700],loop=0,disposal=2)
 contact=Image.new('RGB',(9*180,3*200),'#0b101c');d=ImageDraw.Draw(contact)
 for i,im in enumerate(frames):
  x,y=i%9*180,i//9*200;thumb=im.resize((180,180),R);contact.paste(thumb,(x,y+20),thumb);d.text((x+6,y+3),f'{i+1:02}',fill='#a9b7c7')
 save(contact,ROOT.parent/'qa/bull_rear_slam_contact.jpg',quality=95)
 validate(frames,records)
 archive_bytes=io.BytesIO()
 with zipfile.ZipFile(archive_bytes,'w',zipfile.ZIP_DEFLATED,compresslevel=4) as z:
  for p in sorted(ROOT.rglob('*')):
   if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.writing'):z.write(p,p.relative_to(ROOT.parent))
 archive_path=ROOT.parent/'bull_rear_and_slam_animation_pack.zip'
 archive_tmp=archive_path.with_name(archive_path.name+'.writing')
 archive_tmp.write_bytes(archive_bytes.getvalue());os.replace(archive_tmp,archive_path)
 print('ZIP ready',flush=True)

def validate(frames,records):
 atlas=Image.open(ROOT/'bull_slam_atlas_9x3.png');assert atlas.mode=='RGBA' and atlas.size==(4608,1536)
 anim=Image.open(ROOT/'bull_slam.apng');assert anim.n_frames==27
 counts=[];duration=0
 for i,ref in enumerate(frames):
  im=Image.open(ROOT/f'frames/bull_slam_{i+1:02}.png');a=np.array(im);r=np.array(ref)
  assert im.mode=='RGBA' and im.size==(512,512) and np.array_equal(a,r)
  assert a[:,:,3].min()==0 and not np.any(a[a[:,:,3]==0,:3])
  x,y=i%9*512,i//9*512;assert np.array_equal(np.array(atlas.crop((x,y,x+512,y+512))),r)
  sh=Image.open(ROOT/f'sheets/bull_slam_sheet_{i//9+1:02}.png');assert sh.size==(1536,1536)
  j=i%9;x,y=j%3*512,j//3*512;assert np.array_equal(np.array(sh.crop((x,y,x+512,y+512))),r)
  anim.seek(i);duration+=anim.info['duration'];assert np.array_equal(np.array(anim.convert('RGBA')),r)
  counts.append(int(np.count_nonzero(a[:,:,3])))
 assert duration==1125 and not np.any(np.array(frames[-1]))
 assert np.array_equal(np.array(frames[0]),np.array(Image.open(ROOT/'source/idle_entry_frame.png')))
 assert all(records[11]['frontHoofTips'][j][1]<records[0]['frontHoofTips'][j][1]-85 for j in [0,1])
 report={'passed':True,'frameCount':27,'frameSize':[512,512],'atlasSize':[4608,1536],'smallSheets':3,'smallSheetSize':[1536,1536],'fps':24,'durationMs':1125,'originalArtworkRigged':True,'noCoatOrEyeRecoloring':True,'firstFrameMatchesOriginalIdle':True,'bothFrontHoovesLiftMoreThan85px':True,'alphaVerified':True,'allExportsPixelExact':True,'finalFrameAllRGBAZero':True,'nonzeroAlphaPixels':counts}
 (ROOT/'validation.json').write_text(json.dumps(report,indent=2));print('Validation passed: original colors, articulated hoof lift, matching exports, blank ending.',flush=True)

if __name__=='__main__':main()
