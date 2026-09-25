"""Alfred module prototype. Units mm; STEP source geometry retained in assembly coordinates."""
import sys, json, math, shutil, hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
import cadquery as cq
import xml.etree.ElementTree as ET

SRC=HERE/'source-cad'
OUT=HERE.parent; OUT.mkdir(exist_ok=True)
CAD=OUT/'CAD'; CAD.mkdir(exist_ok=True)
REF=OUT/'reference-envelopes'; REF.mkdir(exist_ok=True)
def box(x,y,z,w,d,h): return cq.Workplane('XY').box(w,d,h,centered=False).translate((x,y,z)).val()
def cyl(x,y,z,r,h): return cq.Solid.makeCylinder(r,h,cq.Vector(x,y,z))
def read(n): return cq.importers.importStep(str(SRC/(n+'.STEP'))).val()
def save(n,s,folder=CAD):
    assert s.isValid(), n
    cq.exporters.export(s,str(folder/(n+'.STEP')))
    cq.exporters.export(s,str(folder/(n+'.STL')),tolerance=.035,angularTolerance=.12)
    print('EXPORTED',n,len(s.Solids()),flush=True)

def board_info(file):
    b=ET.parse(HERE/'board-sources'/file).getroot().find('./drawing/board')
    wires=[v for v in b.findall('./plain/wire') if v.get('layer')=='20']
    xs=[float(v.get(a)) for v in wires for a in ['x1','x2']]; ys=[float(v.get(a)) for v in wires for a in ['y1','y2']]
    lo=(min(xs),min(ys)); size=(max(xs)-lo[0],max(ys)-lo[1])
    holes=[(float(v.get('x'))-lo[0],float(v.get('y'))-lo[1]) for v in b.findall('./elements/element') if 'MOUNTINGHOLE' in v.get('package','')]
    return dict(file=file,source_sha256=hashlib.sha256((HERE/'board-sources'/file).read_bytes()).hexdigest(),size=size,holes=holes,origin=lo)

data={n:board_info(f) for n,f in [('mic','mic0.brd'),('amp','amp0.brd'),('servo','servo0.brd'),('power','power.brd')]}
# The microphone acoustic pad is at (8.255,7.822) in its source board coordinates.
positions={'mic':(5.245,3.978,16),'amp':(7,36,16),'servo':(37,29,16),'power':(13.34,77,14.5),'pi':(52,61,16)}
data['pi']=dict(size=(65,30),holes=[(3.5,3.5),(61.5,3.5),(3.5,26.5),(61.5,26.5)],source='Raspberry Pi Zero 2 W mechanical drawing')

tray=box(3.5,3.8,9,120,94,2.5)
# Corner screws use existing enclosure PCB supports.
for x,y in [(7.5,7.8),(119.5,7.8),(7.5,93.8),(119.5,93.8)]: tray=tray.cut(cyl(x,y,8,1.7,5))
# Ventilation under Pi, maintaining a perimeter for mounts and central stiffness.
for x in range(58,101,7): tray=tray.cut(box(x,68,8,3,16,5))
# Microphone header solder-tail clearance; acoustic passage through tray.
tray=tray.fuse(cyl(13.5,11.8,11.4,3,4.6)).cut(cyl(13.5,11.8,8,1,10))
# Recess for a 0.2 mm compressed annular gasket; board seats remain at 11.5.
tray=tray.cut(cyl(13.5,11.8,15.8,2.3,1))
mounts=[]
for n,d in data.items():
    x,y,z=positions[n]
    for hx,hy in d['holes']:
        px,py=x+hx,y+hy
        if z>11.5: tray=tray.fuse(cyl(px,py,11.4,2.8,z-11.4))
        # M2 screw through module + printed pedestal; nut accessible beneath tray.
        tray=tray.cut(cyl(px,py,8,1.1,z-7))
        mounts.append(dict(module=n,x=px,y=py,seat_z=z,hole_diameter=2.2))

# Removable switch carrier: two feet on tray; perfboard is 20.32 x 15.24.
sx,sy=102.86,5.93
switchbase=box(sx-.8,sy-.8,11.5,19.38,16.84,2)
switchbase=switchbase.cut(box(sx+2,sy+2,11,13.78,11.24,5))
for xx in [sx-.8,sx+16.98]: switchbase=switchbase.fuse(box(xx,sy-.8,13.4,2.4,16.84,2.6))
# End stops locate board while keeping component/solder field open. Thin removable tape retains it.
for yy in [sy-1.2,sy+15.24]: switchbase=switchbase.fuse(box(sx-.8,yy,13,19.38,1.2,4.8))
switchbase=switchbase.cut(cyl(119.5,7.8,11,3.4,3.3))
# Carrier is bonded at the two side rails to tray; top board plane 17.6, switch top21.9.
stem=read('07_Button_stem').intersect(box(100,0,22.1,25,30,45))
save('07_Button_stem_modules',stem)
save('18_Switch_carrier',switchbase)
save('17_Electronics_tray',tray)

# Enlarge only the upper lip of existing USB slot, maintaining front cosmetic design.
plinth=read('01_Plinth').cut(box(15.5,99.8,6.5,28,8,15))
save('01_Plinth_modules',plinth)
speaker_mount=read('03_Speaker_mount').cut(box(91.5,18,34.5,8,6,6))
save('03_Speaker_mount_modules',speaker_mount)

printed={'01_Plinth_modules':plinth,'17_Electronics_tray':tray,'18_Switch_carrier':switchbase,'07_Button_stem_modules':stem,'03_Speaker_mount_modules':speaker_mount}
for n in ['02_Bottom_cover','04_Speaker_lid','05_Microphone_duct','06_Microphone_duct_lid','08_Torso','09_Alfred_head','10_Moving_jaw','11_Name_plaque','12_Servo_cradle','13_Drive_link','14_Rear_cover','15_Fit_coupon','16_Button_cap']:
    s=read(n)
    # Preserve original exports for unchanged parts.
    for ext in ['STEP','STL']: shutil.copy2(SRC/(n+'.'+ext),CAD/(n+'.'+ext))
    if n=='15_Fit_coupon': continue
    if n=='13_Drive_link':
        # local X->global(0,33/L,12/L), Y->(0,-12/L,33/L), Z->X
        L=math.hypot(12,33)
        mat=cq.Matrix([[0,0,1,79.5],[33/L,-12/L,0,62],[12/L,33/L,0,143],[0,0,0,1]])
        s=s.transformGeometry(mat)
    printed[n]=s

refs={}
for n,d in data.items():
    x,y,z=positions[n];w,h=d['size']
    s=box(x,y,z,w,h,1.6)
    for hx,hy in d['holes']:s=s.cut(cyl(x+hx,y+hy,z-1,1.25 if n!='pi' else 1.35,4))
    if n=='mic':s=s.cut(cyl(13.5,11.8,z-1,.5125,4))
    refs[n+'_PCB']=s

# Conservative component/connector envelopes, distinct from exact planar PCB models.
refs.update({
 'amp_terminal_and_wires':box(9,47,17.6,14,19,14),
 'amp_signal_header':box(7,36,17.6,18,5,16),
 'servo_headers_and_plug':box(38,29,17.6,60,8,21),
 'servo_terminal_and_wires':box(61,45,17.6,15,15,15),
 'servo_reservoir_capacitor':cyl(48.811,50.209,17.6,4,20),
 'servo_components':box(41,39,17.6,54,14,3),
 'pi_components':box(53,62,17.6,62,22,5),
 'pi_GPIO_header_and_wires':box(55,85,17.6,59,6,21),
 'pi_SD_service':box(36,69,16,16,14,7),
 'pi_USB_service':box(77,55,17.6,36,6,7),
 'power_USB_connector':box(19,95,16.1,9,6.5,3.3),
 'power_external_plug':box(16.5,101.5,14.7,14,27,6),
 'power_terminal_and_wires':box(16,71,16.1,15,13,15),
 'mic_components':box(10,9,17.6,7,5,2.5),
 'mic_header_and_wires':box(5.6,5.2,17.6,15.8,2.7,16),
 'speaker_body':box(28.5,1,16,70,17,30),
 'speaker_cable_service':box(92,18,35,7,11,5),
 'switch_perfboard':box(sx,sy,16,17.78,15.24,1.6),
 'switch_body':box(108.75,10.55,17.6,6,6,3.4),
 'switch_actuator':cyl(111.75,13.55,21,1.5,.9),
 'power_distribution_reserve':box(102,32,13,18,21,24),
})
for i,(x,y) in enumerate([(7.5,7.8),(119.5,7.8),(7.5,93.8),(119.5,93.8)]):
    refs['tray_screw_head_'+str(i)]=cyl(x,y,11.5,3.1,2.5)
refs['mic_solder_tail_clearance']=box(5.6,5.2,14.5,15.8,2.7,1.5)
for n,s in refs.items():save(n,s,REF)

# Static exact BRep intersections: printed parts against each other and electronics against prints.
def overlap(a,b):
    # Bounding-box filter before kernel intersection.
    A=a.BoundingBox();B=b.BoundingBox()
    if any(getattr(A,k+'max')<=getattr(B,k+'min')+1e-6 or getattr(B,k+'max')<=getattr(A,k+'min')+1e-6 for k in 'xyz'):return 0.
    return a.intersect(b).Volume()
collisions=[]
items=list(printed.items())
for i,(n,a) in enumerate(items):
    print('CHECK',n,flush=True)
    for m,b in items[i+1:]:
        v=overlap(a,b)
        if v>1e-4:collisions.append(dict(a=n,b=m,volume_mm3=round(v,5)))
for n,a in refs.items():
    for m,b in printed.items():
        v=overlap(a,b)
        if v>1e-4:collisions.append(dict(a=n,b=m,volume_mm3=round(v,5)))
ref_conflicts=[]
ri=list(refs.items())
for i,(n,a) in enumerate(ri):
    for m,b in ri[i+1:]:
        # Each module's own PCB, components and service envelopes intentionally overlap.
        if n.split('_')[0]==m.split('_')[0]:continue
        v=overlap(a,b)
        if v>1e-4:ref_conflicts.append(dict(a=n,b=m,volume_mm3=round(v,5)))
asm=cq.Assembly(name='Alfred_module_prototype')
for n,s in printed.items():asm.add(s,name=n,color=cq.Color(.65,.45,.26) if n.startswith(('01','08','09','10','11','14','16')) else cq.Color(.22,.42,.49))
for n,s in refs.items():asm.add(s,name='REF_'+n,color=cq.Color(.15,.6,.3,.65))
asm.save(str(OUT/'Alfred_module_assembly.STEP'))
(OUT/'placement.json').write_text(json.dumps(dict(positions=positions,boards=data,mounts=mounts),indent=2))
(OUT/'clearance-check.json').write_text(json.dumps(dict(method='OpenCascade BRep intersections; conceptual envelopes include service volumes; physical servo/horn not yet modeled',collisions=collisions,between_module_envelopes=ref_conflicts),indent=2))
print('COLLISIONS',json.dumps(collisions),flush=True)
print('MODULE CONFLICTS',json.dumps(ref_conflicts),flush=True)
