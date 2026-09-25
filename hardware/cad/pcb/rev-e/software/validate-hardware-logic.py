from pathlib import Path
from itertools import product
import json
O=Path(__file__).resolve().parent.parent;by={a['ref']:a for a in json.loads((O/'design-data.json').read_text())}
assert by['U4']['pins']=={'1':'UV_SENSE','2':'GND','3':'PI_3V3','4':'PI_3V3','5':'UV_DELAY','6':'SUPPLY_OK'}
assert by['U11']['pins']=={'1':'SERVO_REQUEST','2':'PI_3V3','3':None,'4':'GND','5':'SERVO_ARMED','6':'SUPPLY_OK','7':'PI_3V3','8':'PI_3V3'}
assert by['U5']['pins']['1']=='SERVO_ARMED' and by['U5']['pins']['2']=='SERVO_REQUEST'
# Exhaust all eight-event binary request/supply-good sequences; start with reset asserted.
count=0
for events in product(product([False,True],repeat=2),repeat=8):
 q=False;prev=False;last_fault=True;armed_since_fault=False
 for req,good in events:
  rise=req and not prev
  if not good:q=False;armed_since_fault=False
  elif rise:q=True;armed_since_fault=True
  en=q and req
  assert not en or (good and armed_since_fault)
  if not req:assert not en
  if last_fault and good and req and prev:assert not en
  prev=req;last_fault=not good
 count+=1
print('Latch sequences:',count,'PASS (truth-table model, not analog simulation)')
# Datasheet +/-1% positive and negative thresholds, divider +/-0.1%, sense leakage +/-100 nA conservatively.
def limit(th,sgn):
 rt=32100*(1+sgn*.001);rb=10000*(1-sgn*.001)
 return th*(1+sgn*.01)*(1+rt/rb)+sgn*100e-9*rt
vals={'fall_nom':1.15*4.21,'fall_min':limit(1.15,-1),'fall_max':limit(1.15,1),'rise_nom':1.157*4.21,'rise_min':limit(1.157,-1),'rise_max':limit(1.157,1),'rail_25C_servo_off':5.1-2.85*(.0164+.0283),'rail_25C_allocation':5.1-4.1*.0164-2.85*.0283}
print(json.dumps(vals,indent=2))
