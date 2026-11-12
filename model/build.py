"""Build data.json for the site. Usage: python3 build.py CUR_WEEK RANKS_JSON
CUR_WEEK = the upcoming week; ratings use lines/results from weeks < CUR_WEEK.
RANKS_JSON = {"Team": rank, ...} current CFP/AP ranks for flagging ranked-on-ranked games."""
import sys, os, json, numpy as np, pandas as pd, datetime
import model2 as m
cur = int(sys.argv[1]); ranks = json.load(open(sys.argv[2]))
r, hfa, ab, lc, rc = m.fit(cur)
# manual adjustments (points) for injuries / news, from teams.csv column 'adj' with a note in 'adj_note'
ADJ = {}
if 'adj' in m.teams.columns:
    for x in m.teams.itertuples():
        if pd.notna(x.adj) and float(x.adj) != 0: r[x.team] += float(x.adj); ADJ[x.team] = dict(pts=float(x.adj), note=str(getattr(x,'adj_note','') or ''))
T = m.teams.copy()
T["raw"] = T.team.map(r)
off = 50 - T.raw.mean()                      # average FBS team = 50.0
T["rating"] = (T.raw + off).round(1)
T["lines_n"] = T.team.map(lambda t: lc.get(t, 0)); T["res_n"] = T.team.map(lambda t: rc.get(t, 0))
T["games"] = T.lines_n
T["conf_level"] = np.where(T.lines_n >= 5, "High", np.where(T.lines_n >= 2, "Medium", "Low"))
T = T.sort_values("rating", ascending=False).reset_index(drop=True)
T["rank"] = np.arange(1, len(T) + 1)
T["conf_rank"] = T.groupby("conf").rating.rank(ascending=False, method="first").astype(int)
T["conf_size"] = T.groupby("conf").team.transform("count")
teams = [dict(team=x.team, conf=x.conf, color=x.color, rating=float(x.rating), rank=int(x["rank"]),
              conf_rank=int(x.conf_rank), conf_size=int(x.conf_size), games=int(x.games),
              results=int(x.res_n), confidence=x.conf_level) for _, x in T.iterrows()]
games = []
for g in m.lines[m.lines.week == cur].itertuples():
    if g.home not in r or g.away not in r: continue
    cm = m.pred(r, hfa, g)                       # Claude home margin
    games.append(dict(away=g.away, home=g.home, neutral=bool(g.neutral),
                      away_rank=ranks.get(g.away), home_rank=ranks.get(g.home),
                      book_margin=float(g.margin), claude_margin=round(float(cm), 2),
                      edge=round(float(cm - g.margin), 2), book_src=getattr(g,'src','close')))
out = dict(updated=datetime.date.today().isoformat(), week=cur, hfa=round(float(hfa), 2),
           offset=round(float(off), 3), method=dict(m.P), teams=teams, games=games,
           adjustments=ADJ, backtest_note="Predicting week-%d lines from data through week %d: mean miss %.2f pts" % (cur, cur-1, m.backtest(m.P, (cur,))[0]))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json"), "w"), indent=1)
print(out["backtest_note"], "HFA", out["hfa"])
for g in games: print(f"{g['away']:>15} @ {g['home']:<15} book {g['book_margin']:+.1f} claude {g['claude_margin']:+.1f} edge {g['edge']:+.1f}  ranks {g['away_rank']}/{g['home_rank']}")
print(T[['rank','team','conf','rating','games','conf_level']].head(30).to_string())
print(T[['rank','team','rating']].tail(5).to_string())
