"""GridTrust AI: reproducible, entirely synthetic SCADA event/reliability simulator.

There is no utility integration and no operational control interface.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_score, recall_score, confusion_matrix

BASE_TIME = datetime(2026, 10, 9, 8, 0, 0, tzinfo=timezone.utc)
SCENARIOS = {
    'S01': 'Normal iş rejimi',
    'S02': 'Rabitə gecikməsi',
    'S03': 'Rabitənin kəsilməsi',
    'S04': 'Ölçmə xətası',
    'S05': 'Xətt hadisəsi',
    'S06': 'Qəza və rabitə itkisi',
    'S07': 'Rabitənin bərpası',
}
ASSETS = [
    {'id':'M-35','name':'35 kV giriş','type':'Giriş','parent':None,'x':0,'y':2,'feeder':'—'},
    {'id':'T-01','name':'35/10 kV transformator','type':'Transformator','parent':'M-35','x':1,'y':2,'feeder':'—'},
    {'id':'B-10','name':'10 kV şin','type':'Şin','parent':'T-01','x':2,'y':2,'feeder':'—'},
    {'id':'SW-01','name':'F-01 açarı','type':'Açar','parent':'B-10','x':3,'y':3,'feeder':'F-01'},
    {'id':'RTU-01','name':'F-01 uzaq terminalı','type':'Telemetriya','parent':'SW-01','x':4,'y':3,'feeder':'F-01'},
    {'id':'Y-01','name':'F-01 yükləri','type':'Yük','parent':'RTU-01','x':5,'y':3,'feeder':'F-01'},
    {'id':'SW-02','name':'F-02 açarı','type':'Açar','parent':'B-10','x':3,'y':1,'feeder':'F-02'},
    {'id':'RTU-02','name':'F-02 uzaq terminalı','type':'Telemetriya','parent':'SW-02','x':4,'y':1,'feeder':'F-02'},
    {'id':'Y-02','name':'F-02 yükləri','type':'Yük','parent':'RTU-02','x':5,'y':1,'feeder':'F-02'},
]
FEATURES = ['gecikme_nisbeti','catismayan_paket','olcme_ferqi','alarm_sayi','aciq_telemetriya']


def graph() -> nx.Graph:
    g = nx.Graph()
    for a in ASSETS:
        g.add_node(a['id'], **a)
        if a['parent']:
            g.add_edge(a['parent'], a['id'])
    return g


def electric_state(seed:int=42, scale:float=1.0) -> dict[str,float]:
    """Numerical balanced three-phase steady-state feeder approximation.
    Pandapower is used if installed. Local fallback is explicitly flagged.
    """
    try:
        import pandapower as pp
        net = pp.create_empty_network(sn_mva=100.0)
        hi = pp.create_bus(net, vn_kv=35, name='35 kV')
        low = pp.create_bus(net, vn_kv=10, name='10 kV')
        f1 = pp.create_bus(net, vn_kv=10, name='F-01')
        f2 = pp.create_bus(net, vn_kv=10, name='F-02')
        pp.create_ext_grid(net,hi,vm_pu=1.0)
        pp.create_transformer_from_parameters(net,hi,low,sn_mva=16,vn_hv_kv=35,vn_lv_kv=10,vkr_percent=0.6,vk_percent=6.0,pfe_kw=12,i0_percent=0.1)
        pp.create_line_from_parameters(net,low,f1,length_km=3.0,r_ohm_per_km=.32,x_ohm_per_km=.31,c_nf_per_km=0,max_i_ka=.35,name='F-01')
        pp.create_line_from_parameters(net,low,f2,length_km=2.0,r_ohm_per_km=.35,x_ohm_per_km=.32,c_nf_per_km=0,max_i_ka=.35,name='F-02')
        pp.create_load(net,f1,p_mw=2.0*scale,q_mvar=.8*scale)
        pp.create_load(net,f2,p_mw=1.4*scale,q_mvar=.5*scale)
        pp.runpp(net)
        assert net.converged
        return dict(source='pandapower',u1=float(net.res_bus.vm_pu.loc[f1]*10),u2=float(net.res_bus.vm_pu.loc[f2]*10),
                    i1=float(net.res_line.i_ka.iloc[0]*1000),i2=float(net.res_line.i_ka.iloc[1]*1000),
                    p1=2.0*scale,q1=.8*scale,p2=1.4*scale,q2=.5*scale,
                    trans_load=float(net.res_trafo.loading_percent.iloc[0]),loss_kw=float(net.res_line.pl_mw.sum()*1000))
    except ImportError:
        # Reproducible engineering preview: 3-phase apparent-power current and R/X voltage drop.
        result = {'source':'Üçfazalı təqribi hesablama (pandapower quraşdırılmayıb)'}
        for k,p,q,length,r,x in [(1,2.0,.8,3,.32,.31),(2,1.4,.5,2,.35,.32)]:
            p,q=p*scale,q*scale
            u=10-(r*length*p+x*length*q)/10
            current=1000*math.hypot(p,q)/(math.sqrt(3)*u)
            result.update({f'u{k}':u,f'i{k}':current,f'p{k}':p,f'q{k}':q})
        result['trans_load']=100*math.hypot(result['p1']+result['p2'],result['q1']+result['q2'])/16
        result['loss_kw']=sum(3*((result[f'i{k}']/1000)**2)*(.32 if k==1 else .35)*(3 if k==1 else 2)*1000 for k in (1,2))
        return result


def generate(scenario:str='S01', seed:int=42) -> dict[str,Any]:
    if scenario not in SCENARIOS:
        raise ValueError('Naməlum ssenari')
    rng=np.random.default_rng(seed)
    rows=[]; events=[]; truth=[]
    for tick in range(8):
        scale=float(1+0.035*math.sin(tick/2)+rng.normal(0,.004))
        physical=electric_state(seed,scale)
        trouble=tick >= 3
        offline=trouble and scenario in ('S03','S06')
        if scenario=='S07': offline=2<=tick<=4
        delayed=trouble and scenario=='S02'
        bad=trouble and scenario=='S04'
        fault=trouble and scenario in ('S05','S06')
        # Physical hidden state is exclusively for validation. Never feed it to inference.
        hidden_switch='AÇIQ' if ((scenario in ('S03','S06')) and tick>=5) or (fault and tick>=4) else 'BAĞLI'
        truth.append({'tick':tick,'hidden_switch':hidden_switch,'actual_fault':int(fault),
                      'actual_comm_loss':int(offline),'actual_sensor_error':int(bad)})
        observed_switch='BAĞLI' if not fault else ('AÇIQ' if tick>=4 else 'BAĞLI')
        event_time=BASE_TIME+timedelta(seconds=10*tick)
        if not offline:
            delay=15 if delayed else 1
            # Recovery: one old packet arrives at tick 5, followed by a fresh packet at tick 6.
            if scenario=='S07' and tick==5: src_time=BASE_TIME+timedelta(seconds=10)
            else: src_time=event_time
            received=event_time+timedelta(seconds=delay)
            current=physical['i1']*(1.55 if bad else 1.0)*(1+rng.normal(0,.001))
            rows.append({'tick':tick,'record_id':f'{scenario}-{seed}-{tick}-01','scenario':scenario,'equipment_id':'RTU-01',
                'feeder':'F-01','event_time_utc':src_time.isoformat(),'received_time_utc':received.isoformat(),
                'voltage_kv':round(physical['u1'],4),'current_a':round(current,4),
                'active_power_mw':round(physical['p1'],4),'reactive_power_mvar':round(physical['q1'],4),
                'switch_status':observed_switch,'quality_flag':'GOOD','communication':'UP'})
        rows.append({'tick':tick,'record_id':f'{scenario}-{seed}-{tick}-02','scenario':scenario,'equipment_id':'RTU-02',
            'feeder':'F-02','event_time_utc':event_time.isoformat(),'received_time_utc':(event_time+timedelta(seconds=1)).isoformat(),
            'voltage_kv':round(physical['u2'],4),'current_a':round(physical['i2'],4),
            'active_power_mw':round(physical['p2'],4),'reactive_power_mvar':round(physical['q2'],4),
            'switch_status':'BAĞLI','quality_flag':'GOOD','communication':'UP'})
        if tick==3 and scenario != 'S01':
            typ={'S02':'GECİKMƏ','S03':'RABİTƏ_İTKİSİ','S04':'ÖLÇMƏ_XƏTASI','S05':'RELE_HADİSƏSİ',
                'S06':'RELE_VƏ_RABİTƏ','S07':'RABİTƏ_İTKİSİ'}[scenario]
            events.append({'tick':tick,'event_id':f'EV-{scenario}-{seed}-1','equipment_id':'RTU-01','type':typ,'feeder':'F-01'})
        if fault and tick==4 and scenario=='S05':
            events.append({'tick':tick,'event_id':f'EV-{scenario}-{seed}-2','equipment_id':'SW-01','type':'AÇAR_HADİSƏSİ','feeder':'F-01'})
    data=pd.DataFrame(rows).sort_values(['tick','equipment_id']).reset_index(drop=True)
    return {'scenario':scenario,'seed':seed,'telemetry':data,'events':pd.DataFrame(events,columns=['tick','event_id','equipment_id','type','feeder']),
            'truth':pd.DataFrame(truth),'electric':electric_state(seed),'sha256':sha256(data.to_csv(index=False).encode()).hexdigest()}


def inspect(run:dict, tick:int, expected_seconds:float=10.0) -> dict[str,Any]:
    """Only observed telemetry and event data are permitted here; no `run['truth']` access."""
    df=run['telemetry']
    clock=BASE_TIME+timedelta(seconds=10*tick+1)
    delivered=pd.to_datetime(df['received_time_utc'], utc=True) <= pd.Timestamp(clock)
    visible=df[(df['equipment_id']=='RTU-01') & (df['tick']<=tick) & delivered].copy()
    latest=visible.iloc[-1].to_dict() if not visible.empty else None
    current=visible[visible['tick']==tick]
    arrival_delay=None
    if latest:
        arrival_delay=(pd.Timestamp(latest['received_time_utc'])-pd.Timestamp(latest['event_time_utc'])).total_seconds()
        age=(clock-pd.Timestamp(latest['event_time_utc']).to_pydatetime()).total_seconds()
        # Backfilled data cannot establish current state.
        has_fresh=(not current.empty) and age <= 1.5*expected_seconds and arrival_delay<=2*expected_seconds
    else: age=math.inf;has_fresh=False
    if run['scenario']=='S07' and tick==5:
        status='BƏRPA OLUNUR'
    elif current.empty:
        status='RABİTƏ YOXDUR' if age>1.5*expected_seconds else 'TƏSDİQLƏNMİR'
    elif not has_fresh:
        status='GECİKMİŞ MƏLUMAT'
    else:
        status='TƏSDİQLƏNMİŞ'
    previous=latest['switch_status'] if latest else 'MƏLUM DEYİL'
    confirmed=previous if has_fresh else 'MƏLUM DEYİL'
    # Physical consistency only on a sufficiently fresh measurement.
    residual=None;possible_issue=False
    if has_fresh:
        p=float(latest['active_power_mw']);q=float(latest['reactive_power_mvar']);v=float(latest['voltage_kv']);i=float(latest['current_a'])
        if v>0:
            estimate=1000*math.hypot(p,q)/(math.sqrt(3)*v)
            residual=abs(i-estimate)/max(estimate,1.0)
            possible_issue=residual>.20
    ev=run['events']; observed_events=ev[ev['tick']<=tick]
    # Real-world operator event type must be based on observed evidence only.
    if status=='RABİTƏ YOXDUR':
        message='Uzaq terminaldan yeni məlumat alınmır. Açarın cari vəziyyəti təsdiqlənmir.'
        action='Rabitə xəttini və müstəqil göstəriciləri yoxlayın.'
    elif status=='BƏRPA OLUNUR':
        message='Rabitə bərpa mərhələsindədir. Gələn köhnə paket cari statusu təsdiqləmir.'
        action='Yenilənmiş etibarlı ölçmə gələnədək gözləyin.'
    elif status=='GECİKMİŞ MƏLUMAT':
        message='Məlumatın çatma vaxtı və ya yenilənmə müddəti gözləniləndən uzundur.'
        action='Zaman möhürlərini və rabitə yolunu yoxlayın.'
    elif possible_issue:
        message='Cərəyan göstəricisi güc və gərginlik göstəriciləri ilə uyğun gəlmir.'
        action='Ölçmə cihazını və miqyaslama əmsallarını yoxlayın.'
    elif not observed_events.empty and any('RELE' in x for x in observed_events['type']):
        message='Rele hadisəsi qeydə alınıb; mümkün xətt hadisəsi araşdırılmalıdır.'
        action='Rele jurnalını və şəbəkə statuslarını müqayisə edin.'
    else:
        message='Mövcud ölçmələrdə kritik uyğunsuzluq görünmür.'
        action='Adi monitorinqi davam etdirin.'
    feature=np.array([min((arrival_delay or 1)/expected_seconds,10),int(current.empty),min(residual or 0,10),len(observed_events),int(not has_fresh)],dtype=float)
    return {'tick':tick,'status':status,'last_known':previous,'current_confirmed':confirmed,
        'last_seen':latest['event_time_utc'] if latest else None,'age_s':float(age),'delay_s':arrival_delay,
        'physical_residual':residual,'measurement_suspect':possible_issue,'message':message,'recommendation':action,
        'related_events':observed_events.to_dict('records'),'features':feature,'confirmed':bool(has_fresh)}


def train_anomaly(seed:int=42) -> IsolationForest:
    rng=np.random.default_rng(seed)
    # Synthetic normal operation only, no scenario labels nor truth features.
    normal=np.column_stack([rng.normal(.1,.025,500).clip(0),np.zeros(500),
        rng.normal(.018,.012,500).clip(0),rng.poisson(.025,500),np.zeros(500)])
    model=IsolationForest(n_estimators=120,contamination=.03,random_state=seed)
    model.fit(normal)
    return model


def score_anomaly(model:IsolationForest, finding:dict) -> float:
    return float(model.decision_function(finding['features'].reshape(1,-1))[0])


def evaluate(seed:int=42) -> dict[str,Any]:
    model=train_anomaly(seed)
    labels=[];pred_ai=[];pred_rule=[];records=[]
    for s in SCENARIOS:
        for k in range(5):
            run=generate(s,seed+100+k)
            for t in range(8):
                res=inspect(run,t)
                actual=int((s!='S01') and t>=3 and not (s=='S07' and t>=6))
                ml=int(score_anomaly(model,res)<0)
                rule=int(res['status']!='TƏSDİQLƏNMİŞ' or res['measurement_suspect'] or bool(res['related_events']))
                labels.append(actual);pred_ai.append(ml);pred_rule.append(rule)
                records.append({'scenario':s,'seed':seed+100+k,'tick':t,'ground_truth_anomaly':actual,
                                'ai_flag':ml,'rules_flag':rule})
    def stats(pred):
        tn,fp,fn,tp=confusion_matrix(labels,pred,labels=[0,1]).ravel()
        return {'dəqiqlik':round(float(precision_score(labels,pred,zero_division=0)),3),
                'tapılma':round(float(recall_score(labels,pred,zero_division=0)),3),
                'yanlış_xəbərdarlıq':round(float(fp/max(fp+tn,1)),3),'TP':int(tp),'TN':int(tn),'FP':int(fp),'FN':int(fn)}
    return {'model':'Isolation Forest','qayda':stats(pred_rule),'ai':stats(pred_ai),
            'n_training':500,'n_test':len(labels),'results':pd.DataFrame(records),'synthetic':True}


def export_run(run:dict) -> bytes:
    """Portable audit JSON, no synthetic hidden truth included in operator export."""
    return json.dumps({'scenario':run['scenario'],'seed':run['seed'],'hash':run['sha256'],
      'telemetry':run['telemetry'].to_dict('records'),'events':run['events'].to_dict('records')},
      ensure_ascii=False,indent=2).encode('utf-8')