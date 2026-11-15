"""Independent recomputation of the market sizing in docs/strategy_review_2026-11-14.md (section 5).
Every input is copied from the report's assumption table; this script only checks the arithmetic."""
fee = 0.0236                                    # Razorpay 2% + GST (#13)
net = lambda p: p * (1 - fee)

# TAM (#1-#6, #11): unique potential users x PW blended collection per paying user
users = 566_000 + 87_000 + 140_000 + 30_000
tam_cr = users * 3683 / 1e7
# SAM (#9, #10): in-college + interns x paying share x supplement wallet, then net of 18% GST
sam_payers = 653_000 * 0.20
sam_gross_cr = sam_payers * 1200 / 1e7
sam_net_cr = sam_gross_cr / 1.18

def som(colleges, organic, conv=0.010, repeats=0, pass_price=599, pass_share=0.75, annual=1499):
    reach = colleges * 320 * 0.95                 # 2 ambassadors x ~160 reach, x0.95 occupancy (#19-#20)
    installs = reach * 0.25 + organic             # reach-to-install 25% (#15)
    payers = installs * conv + repeats            # install-to-paid (#14)
    per_payer = pass_share * net(pass_price) * 1.1 + (1 - pass_share) * net(annual)   # 1.1 passes/yr (#17)
    return reach, installs, payers, per_payer, payers * per_payer

rows = {
    "TAM users": users, "TAM Rs cr": round(tam_cr, 1),
    "SAM payers": round(sam_payers), "SAM gross Rs cr": round(sam_gross_cr, 2), "SAM net Rs cr": round(sam_net_cr, 2),
}
y3 = som(70, 1500, repeats=3)
y1 = som(20, 375, pass_price=499, pass_share=0.80)
for name, (reach, inst, pay, ppp, rev) in {"Y3": y3, "Y1": y1}.items():
    rows.update({f"{name} reach": round(reach), f"{name} installs": round(inst), f"{name} payers": round(pay, 1),
                 f"{name} net/payer Rs": round(ppp, 1), f"{name} revenue Rs": round(rev)})
for c in (0.007, 0.014):
    rows[f"Y3 payers @ {c:.1%}"] = round(som(70, 1500, conv=c)[2], 1)
rows["SAM/SOM gap (revenue x)"] = round(sam_net_cr * 1e7 / y3[4])
for k, v in rows.items():
    print(f"{k:28} {v:>14,}")

# ---- Derivations the report states but did not show (added after judge round 2) ----
print("\n# Worksheet: derivations")
cohorts = {"2022-23": 99_463, "2023-24": 109_115, "2024-25": 117_756, "2025-26": 128_875, "2026-27": 140_664}
in_college = 0.95 * sum(cohorts.values())
print(f"in-college students = 0.95 x {sum(cohorts.values()):,} (5 cohorts) = {in_college:,.0f}")
print(f"interns = 0.95 x ~92,000 (2021-22 cohort proxy) = {0.95*92_000:,.0f}")
# Effective colleges: a college whose ambassador leaves is uncovered for part of the year (TEAM ASSUMPTION: 30% of a year)
def effective(nominal, churn, uncovered=0.30):
    return nominal * (1 - churn * uncovered)
print(f"Y3 effective colleges = 80 x (1 - 0.40 x 0.30) = {effective(80, 0.40):.1f}  (report uses 70)")
# Bull case: 150 colleges, 4 ambassadors, 30% churn, 30% install, 1.9% conversion, 5,000 organic, +50 PG payers
eff = effective(150, 0.30)
reach = eff * 4 * 160 * 0.95
installs = reach * 0.30 + 5_000
payers = installs * 0.019 + 50
print(f"bull: effective colleges {eff:.1f}; reach {reach:,.0f}; installs {installs:,.0f}; payers {payers:,.0f} (report: ~600)")
print(f"bull revenue at report's Rs 6.6 lakh implies Rs {660_000/payers:,.0f} net per payer (base mix gives Rs 848)")
bear_eff = effective(40, 0.50)
bear_payers = (bear_eff * 1 * 160 * 0.95 * 0.125 + 750) * 0.007
print(f"bear: effective colleges {bear_eff:.1f}; payers {bear_payers:,.1f} (report: ~10-12)")
