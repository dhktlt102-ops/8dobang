# 팔도방랑이 주간 점검 도우미
#   python3 tools/notes.py export   -> work/sites.json(박지 목록), work/notes.json(현재 규정 데이터)를 만들어요
#   python3 tools/notes.py import   -> work/notes.json을 검사해서 index.html의 EMBED_NT 한 줄에 다시 써 넣어요
import json, os, re, sys, datetime
PAGE = "index.html"
NT = re.compile(r'/\*EMBED_NT\*/const EMBED_NT=(.*?);/\*EMBED_NT_END\*/', re.S)
STATUS = {"ok", "check", "risk", "ban"}
REGION = {"수도권", "강원", "충청", "전라", "경상", "제주"}
TYPE = {"섬", "산", "해변", "야영장"}
ID = re.compile(r"^[a-z][a-z0-9_]{1,40}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def page(): return open(PAGE, encoding="utf-8").read()

def base_sites(t):
    a = t.index("const BASE=["); b = t.index("\n];", a)
    pm = re.search(r'PAID=new Set\(\[(.*?)\]\)', t); paid = set(re.findall(r'"([a-z0-9_]+)"', pm[1])) if pm else set()
    out = []
    for c in re.split(r'(?=\{id:")', t[a:b])[1:]:
        m = re.match(r'\{id:"([a-z0-9_]+)",name:"([^"]*)",loc:"([^"]*)",lat:([\d.]+),lng:([\d.]+),region:"([^"]*)",type:"([^"]*)"', c)
        if not m: continue
        st = re.search(r'\bstatus:"(\w+)"', c); fe = re.search(r'\bfee:"(\w+)"', c)
        out.append({"id": m[1], "name": m[2], "loc": m[3], "lat": float(m[4]), "lng": float(m[5]), "region": m[6], "type": m[7],
                    "status": st[1] if st else "check", "fee": fe[1] if fe else ("paid" if m[1] in paid else "free"), "unverified": bool(re.search(r"\bunv:1", c))})
    return out

def s(v, n):  # plain text only: no angle brackets / backticks / control chars
    v = re.sub(r"[<>`\x00-\x1f]", "", str(v)).strip()
    return v[:n]

def src_list(v):
    out = []
    for x in (v if isinstance(v, list) else [])[:5]:
        if isinstance(x, list) and len(x) == 2 and str(x[1]).startswith(("http://", "https://")):
            out.append([s(x[0], 120), s(x[1], 300)])
    return out

def pairs(v):
    out = []
    for x in (v if isinstance(v, list) else [])[:6]:
        if isinstance(x, list) and len(x) == 2: out.append([s(x[0], 60), s(x[1], 160)])
    return out

def clean(nt, base_ids):
    today = datetime.date.today().isoformat()
    notes = {}
    for k, n in (nt.get("notes") or {}).items():
        if k not in base_ids or not isinstance(n, dict): continue
        o = {"checked": s(n.get("checked") or today, 10)}
        if n.get("status") in STATUS: o["status"] = n["status"]
        if n.get("rule"): o["rule"] = s(n["rule"], 400)
        if n.get("src"): o["src"] = src_list(n["src"])
        notes[k] = o
    added, seen = [], set(base_ids)
    for a in (nt.get("added") or [])[:80]:
        try:
            lat, lng = float(a["lat"]), float(a["lng"])
        except Exception:
            continue
        if not (isinstance(a, dict) and ID.match(str(a.get("id", ""))) and a["id"] not in seen and 33 <= lat <= 38.7 and 124 <= lng <= 131.9 and a.get("name")): continue
        seen.add(a["id"])
        added.append({"id": a["id"], "name": s(a["name"], 40), "loc": s(a.get("loc", ""), 60), "lat": round(lat, 5), "lng": round(lng, 5),
                      "region": a.get("region") if a.get("region") in REGION else "", "type": a.get("type") if a.get("type") in TYPE else "산",
                      "status": a.get("status") if a.get("status") in STATUS else "check", "fee": "paid" if a.get("fee") == "paid" else "free",
                      "rule": s(a.get("rule", ""), 400), "src": src_list(a.get("src")), "access": s(a.get("access", ""), 200),
                      "toilets": pairs(a.get("toilets")), "food": pairs(a.get("food"))})
    upd = nt.get("updated") if DATE.match(str(nt.get("updated", ""))) else today
    return {"updated": upd, "notes": notes, "added": added}

if __name__ == "__main__":
    t = page(); base = base_sites(t); ids = {b["id"] for b in base}
    if sys.argv[1:] == ["export"]:
        os.makedirs("work", exist_ok=True)
        json.dump(base, open("work/sites.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(json.loads(NT.search(t).group(1)), open("work/notes.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("exported", len(base), "sites")
    elif sys.argv[1:] == ["import"]:
        nt = clean(json.load(open("work/notes.json", encoding="utf-8")), ids)
        line = "/*EMBED_NT*/const EMBED_NT=%s;/*EMBED_NT_END*/" % json.dumps(nt, ensure_ascii=False, separators=(",", ":"))
        t2, n = NT.subn(lambda m: line, t); assert n == 1
        open(PAGE, "w", encoding="utf-8").write(t2)
        print("imported: notes", len(nt["notes"]), "added", len(nt["added"]), "updated", nt["updated"])
    else:
        sys.exit("usage: notes.py export|import")
