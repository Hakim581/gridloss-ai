"""GridTrust AI — Azərbaycan dilində Streamlit sınaq paneli."""
import json

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from gridtrust_engine import (
    ASSETS, SCENARIOS, evaluate, export_run, generate, graph, inspect,
    score_anomaly, train_anomaly
)

st.set_page_config(page_title='GridTrust AI | Şəbəkənin ağıllı izahı', page_icon='⚡', layout='wide', initial_sidebar_state='expanded')
st.markdown('''<style>
.block-container{padding-top:1.5rem;max-width:1200px}
h1,h2,h3{letter-spacing:-.02em}
[data-testid="stMetric"]{border:1px solid #D9E2E8;border-radius:12px;padding:13px}
[data-testid="stSidebar"]{border-right:1px solid #dde5ee}
</style>''',unsafe_allow_html=True)

@st.cache_resource
def model():
    return train_anomaly(42)

@st.cache_data
def performance():
    return evaluate(42)

if 'run' not in st.session_state:
    st.session_state.run=generate('S01',42)
    st.session_state.tick=7
    st.session_state.uses=0

st.sidebar.markdown('## ⚡ GridTrust AI')
st.sidebar.caption('Elektrik şəbəkəsi üçün ağıllı məlumat yoxlaması')
page=st.sidebar.radio('Bölmələr',[
    'Baş səhifə','Simulyasiya','Süni intellekt təhlili','Sınaq nəticələri','Layihəni anla'
], label_visibility='collapsed')
st.sidebar.divider()
st.sidebar.caption('**Sınaq proqramı • Sintetik məlumatlar**')
st.sidebar.caption('Real SCADA sisteminə qoşulmur. Elektrik açarlarına əmr göndərmir.')

run=st.session_state.run
finding=inspect(run,st.session_state.tick)
score=score_anomaly(model(),finding)
is_anomaly=score<0
status=finding['status']


def network_figure(incident:bool=True):
    g=graph()
    fig=go.Figure()
    for u,v in g.edges:
        a,b=g.nodes[u],g.nodes[v]
        fig.add_trace(go.Scatter(x=[a['x'],b['x']],y=[a['y'],b['y']],mode='lines',
            line={'color':'#A4B6C3','width':3},hoverinfo='skip',showlegend=False))
    xs=[];ys=[];labels=[];colours=[];hover=[]
    for a in ASSETS:
        bad=incident and a['feeder']=='F-01' and (status!='TƏSDİQLƏNMİŞ' or finding['measurement_suspect'])
        xs.append(a['x']);ys.append(a['y']);labels.append(a['id'])
        colours.append('#dc782f' if bad else '#087E8B')
        hover.append(f"{a['name']}<br>Avadanlıq: {a['id']}<br>Qidalandırıcı: {a['feeder']}")
    fig.add_trace(go.Scatter(x=xs,y=ys,mode='markers+text',text=labels,textposition='bottom center',
        marker={'size':20,'color':colours,'line':{'width':2,'color':'white'}},
        hovertext=hover,hoverinfo='text',showlegend=False))
    fig.update_layout(margin=dict(l=10,r=10,t=10,b=10),height=310,
        paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False,range=[-.5,5.6]),yaxis=dict(visible=False,range=[.45,3.65]),
        dragmode=False)
    return fig


def badge():
    st.info('**NÜMAYİŞ REJİMİ:** Bütün avadanlıqlar və məlumatlar sintetikdir. Sistem yalnız təhlil və qərar dəstəyi üçündür.',icon='ℹ️')


def short_status():
    if status=='TƏSDİQLƏNMİŞ': st.success('Cari ölçmə təsdiqlənib.')
    elif status=='RABİTƏ YOXDUR': st.error('Rabitə itirilib. Açarın cari vəziyyəti naməlumdur.')
    else: st.warning(f'Cari məlumatın vəziyyəti: {status.lower()}.')


def incident_details():
    st.markdown('### Sistem nə müəyyənləşdirdi?')
    st.write(finding['message'])
    st.markdown('**Nəyi bilmirik?**')
    st.write('Rabitə və ya ölçmə etibarlılığı pozulduqda avadanlığın cari fiziki vəziyyətini təkcə köhnə məlumatla təsdiqləmək olmaz.' if not finding['confirmed'] else 'Cari məlumat təsdiqlidir, lakin görünməyən nasazlıqları istisna etmək olmaz.')
    st.markdown('**Operator nə etməlidir?**')
    st.write(finding['recommendation'])

st.title('GridTrust AI')
st.caption('Rabitə və ölçmə məlumatlarının etibarlılığı • Hadisələrin izahı • Operatora qərar dəstəyi')
badge()

if page=='Baş səhifə':
    st.subheader('Şəbəkədə indi nə baş verir?')
    a,b,c=st.columns(3)
    a.metric('Rabitə və məlumat','Normal' if finding['confirmed'] else 'Yoxlama tələb olunur')
    b.metric('Açarın cari vəziyyəti',finding['current_confirmed'])
    c.metric('Süni intellektin yoxlaması','Qeyri-adi' if is_anomaly else 'Adi nümunə')
    x,y=st.columns([1.35,1],gap='large')
    with x:
        st.markdown('#### Şəbəkənin sadə sxemi')
        st.plotly_chart(network_figure(),use_container_width=True,config={'displayModeBar':False})
        st.caption('35/10 kV şəbəkənin şərti sxemi; gerçək obyektlərin yeri deyil.')
        with st.expander('Hesablanmış elektrik göstəricilərini göstər'):
            e=run['electric']
            st.write(f"**Hesablama üsulu:** {e['source']}")
            st.dataframe(pd.DataFrame([
                {'Xətt':'F-01','Gərginlik (kV)':round(e['u1'],3),'Cərəyan (A)':round(e['i1'],2),'Aktiv güc (MVt)':round(e['p1'],2)},
                {'Xətt':'F-02','Gərginlik (kV)':round(e['u2'],3),'Cərəyan (A)':round(e['i2'],2),'Aktiv güc (MVt)':round(e['p2'],2)}
            ]),hide_index=True,use_container_width=True)
            st.write(f"Transformator yüklənməsi: {e['trans_load']:.1f}%")
    with y:
        short_status()
        incident_details()
        st.info('**Süni intellektin rolu:** qayda yoxlamalarını əvəz etmir; qeyri-adi məlumat kombinasiyalarını əlavə olaraq aşkarlayır.')
    st.divider()
    st.markdown('**Yoxlamaq istəyirsən?** Soldan “Simulyasiya” bölməsinə keç, hadisə seç və “Ssenarini işə sal” düyməsini bas.')

elif page=='Simulyasiya':
    st.subheader('Hadisəni özün yarat və nəticəni gör')
    st.write('Bir ssenari seç. Proqram sintetik ölçmələr yaradacaq, onları yoxlayacaq və nə baş verdiyini izah edəcək.')
    left,right=st.columns([1,2],gap='large')
    with left:
        option=st.selectbox('Sınaq hadisəsi',list(SCENARIOS),format_func=lambda x:f'{x} — {SCENARIOS[x]}',index=list(SCENARIOS).index(run['scenario']))
        seed=st.number_input('Təkrarlana bilən sınaq nömrəsi',1,99999,value=int(run['seed']),step=1,help='Eyni nömrə eyni sintetik məlumatı yaradır.')
        if st.button('▶ Ssenarini işə sal',type='primary',use_container_width=True):
            st.session_state.run=generate(option,int(seed));st.session_state.tick=7;st.session_state.uses+=1
            st.rerun()
        if st.button('↺ Normal vəziyyətə qayıt',use_container_width=True):
            st.session_state.run=generate('S01',42);st.session_state.tick=7;st.rerun()
        st.caption('Məlumatlar real şəbəkədən alınmır. Yalnız simulyasiya hesablamalarıdır.')
    with right:
        st.write(f"**Hazırkı ssenari:** {SCENARIOS[run['scenario']]}")
        st.session_state.tick=st.slider('Hadisənin zaman addımı',0,7,int(st.session_state.tick),help='Addımlar 10 saniyəlik sintetik zaman fərqini göstərir.')
        finding=inspect(run,st.session_state.tick)
        score=score_anomaly(model(),finding)
        is_anomaly=score<0;status=finding['status']
        short_status()
        aa,bb=st.columns(2)
        aa.metric('Son məlum açar vəziyyəti',finding['last_known'])
        bb.metric('Cari təsdiqlənmiş vəziyyət',finding['current_confirmed'])
        st.plotly_chart(network_figure(),use_container_width=True,config={'displayModeBar':False})
    st.divider()
    incident_details()
    with st.expander('Bu qərar hansı göstəricilərə əsaslanır?'):
        st.write(f"Gecikmə (saniyə): {finding['delay_s'] if finding['delay_s'] is not None else 'Məlum deyil'}")
        st.write(f"Ölçmə uyğunsuzluğu: {finding['physical_residual'] if finding['physical_residual'] is not None else 'Qiymətləndirilmir'}")
        st.write(f"Əlaqəli hadisələr: {len(finding['related_events'])}")
        st.write(f"Məlumatın son etibarlı vaxtı: {finding['last_seen'] or 'Məlum deyil'}")
    st.download_button('Ssenarinin məlumatlarını endir',export_run(run),file_name=f'GridTrust_{run["scenario"]}_{run["seed"]}.json',mime='application/json')

elif page=='Süni intellekt təhlili':
    st.subheader('Süni intellekt nəyi yoxlayır?')
    st.write('Öyrədilmiş **Isolation Forest** alqoritmi daxil olan məlumatlar içində qeyri-adi kombinasiyaları axtarır. Bununla yanaşı, rabitə və elektrik fizikasına aid dəqiq yoxlama qaydaları ayrıca işləyir.')
    col1,col2=st.columns(2)
    with col1:
        st.metric('Öyrədilmiş modelin qərar balı',f'{score:.3f}')
        st.caption('Bal mənfidirsə model qeyri-adilik görüb. Bu, qəzanın ehtimal faizi deyil.')
        st.write('**Modelin qiymətləndirməsi:**','Qeyri-adi nümunə' if is_anomaly else 'Adi nümunə')
    with col2:
        st.metric('Qayda əsaslı məlumat statusu',finding['status'])
        st.caption('Bu status AI qərarı deyil; alınma vaxtı və ölçmə mövcudluğu əsasında hesablanır.')
        st.write('**Ölçmə uyğunsuzluğu:**','Aşkarlanıb' if finding['measurement_suspect'] else ('Qiymətləndirilməyib' if finding['physical_residual'] is None else 'Aşkarlanmayıb'))
    st.markdown('#### Model hansı göstəricilərə baxdı?')
    from gridtrust_engine import FEATURES
    st.dataframe(pd.DataFrame({'Göstərici':['Gecikmə nisbəti','Çatışmayan paket','Elektrik ölçmə fərqi','Qeydə alınmış hadisələr','Yeni ölçmə təsdiqlənmir'],
                               'Hesablanmış dəyər':[round(float(v),4) for v in finding['features']]}),hide_index=True,use_container_width=True)
    incident_details()
    st.warning('Model **nasazlığın dəqiq yerini və səbəbini sübut etmir**. Səbəb ehtimalları həmişə ölçmə və hadisə sübutları ilə təsdiqlənməlidir.')

elif page=='Sınaq nəticələri':
    st.subheader('Modelin həqiqi sınaq nəticələri')
    st.write('Buradakı qiymətlər yalnız **sintetik test dəstində proqramın həqiqətən hesabladığı** nəticələrdir. Real “Azərişıq” şəbəkəsi üzrə dəqiqlik iddiası deyil.')
    if st.button('Hesablamaları və müqayisəni işə sal',type='primary'):
        st.session_state.show_eval=True
    if st.session_state.get('show_eval'):
        with st.spinner('Sınaq məlumatları hesablanır...'):
            ev=performance()
        st.markdown(f"**Sınaq nümunələri:** {ev['n_test']} • **Modelin öyrənmə nümunələri:** {ev['n_training']}")
        tab=pd.DataFrame([{'Metod':'Süni intellekt','Dəqiqlik':ev['ai']['dəqiqlik'],'Tapılma':ev['ai']['tapılma'],'Yanlış xəbərdarlıq':ev['ai']['yanlış_xəbərdarlıq']},
                          {'Metod':'Yoxlama qaydaları','Dəqiqlik':ev['qayda']['dəqiqlik'],'Tapılma':ev['qayda']['tapılma'],'Yanlış xəbərdarlıq':ev['qayda']['yanlış_xəbərdarlıq']}])
        st.dataframe(tab,hide_index=True,use_container_width=True)
        st.caption('Dəqiqlik: aşkar edilənlərin neçə faizi doğrudur. Tapılma: real sınaq hadisələrinin neçə faizi aşkarlanıb.')
        st.download_button('Hesablanmış nəticələri CSV kimi endir',ev['results'].to_csv(index=False).encode(),file_name='gridtrust_test_results.csv',mime='text/csv')
    else:
        st.info('Sınaq hələ işə salınmayıb. Yuxarıdakı düyməyə bas.')
    st.markdown('#### Təhlükəsizlik qaydası')
    st.write('Rabitə kəsiləndə son məlum açar vəziyyəti **cari təsdiqlənmiş vəziyyət** kimi göstərilə bilməz.')

else:
    st.subheader('Layihəni anla: qaydalar, izahlar, terminlər')
    st.markdown('### 1. GridTrust AI nə üçün yaradılıb?')
    st.write('SCADA elektrik şəbəkəsindən məlumatları göstərir. GridTrust AI isə məlumatın vaxtında gəlib-gəlmədiyini, ölçmələrin bir-biri ilə uyğunluğunu və hadisələrin əlaqəsini analiz edir. Operatora nəyi dəqiq bildiyini, nəyi bilmədiyini və haradan yoxlamaya başlamalı olduğunu izah edir.')
    st.markdown('### 2. Proqramın işləmə ardıcıllığı')
    for title,desc in [
        ('1) Elektrik modeli','Şərti 35/10 kV şəbəkənin gərginliyi, cərəyanı və gücü hesablanır.'),
        ('2) SCADA məlumatlarının yaradılması','Ölçmə və açar məlumatları vaxt möhürləri ilə sintetik şəkildə hazırlanır.'),
        ('3) Etibarlılıq yoxlaması','Gecikmə, rabitə itkisi və köhnə məlumat qaydalarla aşkar edilir.'),
        ('4) Elektrik yoxlaması','Gərginlik, cərəyan, aktiv və reaktiv güc arasında uyğunsuzluq axtarılır.'),
        ('5) Süni intellekt','Isolation Forest qeyri-adi göstərici kombinasiyalarına ayrıca bal verir.'),
        ('6) İzah və tövsiyə','Mövcud sübut əsasında operatora anlaşılan nəticə təqdim olunur.')]:
        with st.expander(title):st.write(desc)
    st.markdown('### 3. Sınaq ssenarilərinin izahı')
    descriptions={
        'S01':'Ölçmələr normal gəlir və rabitə işləyir.',
        'S02':'Ölçmə göndərilib, lakin rabitədə gecikdiyi üçün operatora vaxtında çatmır.',
        'S03':'Bir uzaq terminal əlaqədən çıxır. Açar fiziki olaraq dəyişə bilər, amma sistem bunu təsdiqləyə bilmir.',
        'S04':'Cərəyan ölçməsinə sintetik səhv daxil edilir və fiziki uyğunsuzluq yoxlanılır.',
        'S05':'Süni rele və açar hadisələri yaranır; bu, həqiqi qısaqapanma keçid simulyasiyası deyil.',
        'S06':'Xətt hadisəsi və rabitə itkisi eyni anda olur; qeyri-müəyyənlik açıq göstərilir.',
        'S07':'Rabitə bərpa olunur; əvvəl gələn köhnə paket cari vəziyyətin sübutu sayılmır.'}
    for code,title in SCENARIOS.items():
        with st.expander(f'{code} — {title}'):st.write(descriptions[code])
    st.markdown('### 4. Terminlər lüğəti')
    glossary=[('SCADA','Elektrik şəbəkəsini uzaqdan müşahidə və idarəetmə sistemi.'),
        ('Uzaq terminal','Sahədən məlumat toplayıb mərkəzə göndərən avadanlıq.'),
        ('Telemetriya','Uzaqdan alınan ölçmə və vəziyyət məlumatları.'),
        ('Qidalandırıcı xətt','Yarımstansiyadan elektrik paylayan çıxış xətti.'),
        ('Son məlum vəziyyət','Rabitə kəsilmədən əvvəl alınan son təsdiqlənmiş məlumat.'),
        ('Cari təsdiqlənmiş vəziyyət','Yenilənmiş və etibarlı müşahidə ilə təsdiqlənən cari hal.'),
        ('Anomaliya','Adi məlumat davranışından qeyri-adi yayınma.'),
        ('Isolation Forest','Qeyri-adi nümunələri ayıran maşın öyrənməsi alqoritmi.'),
        ('Elektrik hesablaması','Gərginlik, cərəyan və güc arasındakı fiziki əlaqələrin hesablanması.'),
        ('Pandapower','Elektrik şəbəkəsində yük axını hesablamaları aparan Python kitabxanası.')]
    st.dataframe(pd.DataFrame(glossary,columns=['Termin','Sadə izah']),hide_index=True,use_container_width=True)
    st.markdown('### 5. Təhlükəsizlik və sərhədlər')
    st.write('Bu proqramın real elektrik şəbəkəsinə nəzarət icazəsi yoxdur. Rele parametrlərini dəyişmir, açarları idarə etmir və real obyekt ünvanlarından istifadə etmir. Süni intellekt qərar verməyə kömək edir, lakin operatoru əvəz etmir.')
    st.markdown('### 6. Mənbə və texniki sənəd')
    st.write('Texniki əsas: GRIDTRUST AI — Software Requirements Specification v1.0, 09.10.2026. Fiziki hesablamalar: balanslı üçfazalı dövrə modeli və quraşdırıldıqda pandapower. AI: scikit-learn Isolation Forest. Bu demonstrasiya laboratoriya sınağıdır.')

st.divider()
st.caption(f"GridTrust AI • Ssenari: {run['scenario']} • Sınaq nömrəsi: {run['seed']} • Məlumatlar sintetikdir • İdarəetmə komandaları mövcud deyil")