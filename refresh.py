# 팔도방랑이 예보 갱신: python3 refresh.py index.html  (Open-Meteo에서 예보를 받아 index.html의 EMBED_FC·EMBED_HR 줄만 바꿔요)
import json,re,sys,time,urllib.request,datetime
p=sys.argv[1];t=open(p,encoding="utf-8").read()
def sites():
    out=[(m[0],float(m[1]),float(m[2])) for m in re.findall(r'\{id:"([a-z0-9_]+)",name:"[^"]*",loc:"[^"]*",lat:([\d.]+),lng:([\d.]+)',t)]
    m=re.search(r'/\*EMBED_NT\*/const EMBED_NT=(.*?);/\*EMBED_NT_END\*/',t,re.S)
    if m and m.group(1)!="null":
        for a in json.loads(m.group(1)).get("added",[]):
            if isinstance(a.get("lat"),(int,float)) and isinstance(a.get("lng"),(int,float)) and a.get("id") and a["id"] not in {s[0] for s in out}:
                out.append((a["id"],a["lat"],a["lng"]))
    return out
def get(u):
    for k in range(4):
        try:
            with urllib.request.urlopen(u,timeout=60) as r: return json.loads(r.read())
        except Exception as e:
            err=e; time.sleep(20)
    raise err
def fetch(S):
    M=["ecmwf_ifs025","gfs_seamless","icon_seamless","jma_seamless","ukmo_seamless"];V=["weather_code","temperature_2m_max","temperature_2m_min","precipitation_sum","wind_speed_10m_max"]
    HV=["weather_code","temperature_2m","precipitation","precipitation_probability","wind_speed_10m","wind_gusts_10m","cloud_cover"];HK=["c","t","p","pp","w","g","cc"]
    r1=lambda v:None if v is None else round(v,1)
    F={};H={};t0=ht0=None
    for i in range(0,len(S),23):
        g=S[i:i+23];j=get("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&daily=%s&models=%s&wind_speed_unit=ms&timezone=Asia%%2FSeoul&forecast_days=16"%(",".join(str(x[1]) for x in g),",".join(str(x[2]) for x in g),",".join(V),",".join(M)))
        j=j if isinstance(j,list) else [j]
        for k,x in enumerate(j): F[g[k][0]]=[[[r1(v) for v in x["daily"].get(vn+"_"+m,[])] for vn in V] for m in M]
        t0=j[0]["daily"]["time"][0];time.sleep(2)
    for i in range(0,len(S),35):
        g=S[i:i+35];j=get("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&hourly=%s&wind_speed_unit=ms&timezone=Asia%%2FSeoul&forecast_days=7"%(",".join(str(x[1]) for x in g),",".join(str(x[2]) for x in g),",".join(HV)))
        j=j if isinstance(j,list) else [j]
        for k,x in enumerate(j): H[g[k][0]]={HK[n]:[(None if v is None else (round(v) if n in (0,3,6) else round(v,1))) for v in x["hourly"][vn]] for n,vn in enumerate(HV)}
        ht0=j[0]["hourly"]["time"][0];time.sleep(2)
    now=int(time.time()*1000);at=(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")+" KST"
    return {"fc":{"t0":t0,"at":at,"storedAt":now,"F":F},"hr":{"t0":ht0,"at":at,"storedAt":now,"H":H}}
if "--data" in sys.argv: D=json.load(open(sys.argv[sys.argv.index("--data")+1]))
else: D=fetch(sites())
def put(tag,val):
    global t
    s="/*EMBED_%s*/const EMBED_%s=%s;/*EMBED_%s_END*/"%(tag,tag,json.dumps(val,ensure_ascii=False,separators=(",",":")),tag)
    t,n=re.subn(r'/\*EMBED_%s\*/.*?/\*EMBED_%s_END\*/'%(tag,tag),lambda m:s,t,flags=re.S);assert n==1
if "fc" in D: put("FC",D["fc"])
if "hr" in D: put("HR",D["hr"])
if "nt" in D: put("NT",D["nt"])
open(p,"w",encoding="utf-8").write(t)
print("sites",len(sites()),"fc",len(D.get("fc",{}).get("F",{})),"hr",len(D.get("hr",{}).get("H",{})),"t0",D.get("fc",{}).get("t0"))
