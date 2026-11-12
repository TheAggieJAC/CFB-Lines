"""Market + results power ratings with an SP+ prior.
Usage: python3 model2.py [backtest|fit] [current_week]
Rating of team i: r_i. Predicted home margin = r_home - r_away + HFA*(not neutral).
Objective (weighted least squares):
  lines:   w_line * decay * (r_h - r_a + hfa - line_margin)^2
  results: w_res  * decay * (r_h - r_a + hfa - capped_margin)^2
  prior:   lam    * (r_i - a - b*SP_i)^2      (FCS teams: SP = -35, weak lam)
a, b, hfa are free.
"""
import sys, json, numpy as np, pandas as pd
import os
D = os.path.dirname(os.path.abspath(__file__)) + "/"
teams = pd.read_csv(D + "teams.csv")
lines = pd.read_csv(D + "lines.csv")
res = pd.read_csv(D + "results.csv")
lines["margin"] = np.where(lines.fav == lines.home, lines.spread, -lines.spread)
res["margin"] = (res.home_pts - res.away_pts).clip(-28, 28)
SP = dict(zip(teams.team, teams.sp))
P = dict(HL=2.0, W_RES=0.25, LAM=2.0, LAM_FCS=0.02, CAP=28)

def fit(cur_week, p=P, line_max_week=None, res_max_week=None):
    L = lines[lines.week <= (line_max_week if line_max_week is not None else cur_week - 1)]
    R = res[res.week <= (res_max_week if res_max_week is not None else cur_week - 1)]
    allt = sorted(set(teams.team) | set(L.home) | set(L.away) | set(R.home) | set(R.away))
    idx = {t: i for i, t in enumerate(allt)}; n = len(allt)
    nv = n + 3  # r..., a, b, hfa
    rows, ys, ws = [], [], []
    def game(df, base_w):
        for g in df.itertuples():
            x = np.zeros(nv); x[idx[g.home]] = 1; x[idx[g.away]] = -1
            x[n + 2] = 0 if g.neutral else 1
            rows.append(x); ys.append(g.margin)
            ws.append(base_w * 0.5 ** ((cur_week - 1 - g.week) / p["HL"]))
    game(L, 1.0); game(R, p["W_RES"])
    for t in allt:
        x = np.zeros(nv); x[idx[t]] = 1; x[n] = -1
        fbs = t in SP
        x[n + 1] = -(SP[t] if fbs else -35.0)
        rows.append(x); ys.append(0.0); ws.append(p["LAM"] if fbs else p["LAM_FCS"])
    X = np.array(rows); y = np.array(ys); w = np.sqrt(np.array(ws))
    A = X * w[:, None]; b = y * w
    # tiny ridge on a to pin level
    reg = np.zeros((nv, nv)); reg[n, n] = 1e-6
    coef = np.linalg.solve(A.T @ A + reg, A.T @ b)
    r = dict(zip(allt, coef[:n]))
    gcount = pd.concat([L.home, L.away]).value_counts().to_dict()
    rcount = pd.concat([R.home, R.away]).value_counts().to_dict()
    return r, coef[n + 2], dict(a=coef[n], b=coef[n + 1]), gcount, rcount

def pred(r, hfa, g):
    return r[g.home] - r[g.away] + (0 if g.neutral else hfa)

def backtest(p, weeks=(8, 9, 10, 11)):
    e = []
    for wk in weeks:
        r, h, *_ = fit(wk, p)
        for g in lines[lines.week == wk].itertuples():
            if g.home in r and g.away in r: e.append(pred(r, h, g) - g.margin)
    e = np.array(e); return np.mean(np.abs(e)), np.mean(np.abs(e) > 2), len(e)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "fit"
    if mode == "backtest":
        best = None
        for HL in [2, 3, 5]:
            for W in [0, 0.1, 0.25, 0.5]:
                for LAM in [0.05, 0.15, 0.4, 1.0]:
                    p = dict(P, HL=HL, W_RES=W, LAM=LAM)
                    mae, frac, n = backtest(p)
                    if best is None or mae < best[0]: best = (mae, HL, W, LAM)
                    print(f"HL={HL} W_RES={W} LAM={LAM}  MAE={mae:.2f}  >2pt={frac:.0%} n={n}")
        print("BEST", best)
