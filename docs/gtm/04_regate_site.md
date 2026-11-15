# Re-gate the public site (production change: needs your explicit yes)

**Why:** the textbooks are unlicensed private copies; the public site shows short excerpts. The strategy review rates this
the top legal risk and recommends a login gate and no public excerpts until rights are settled. You chose a public site
with excerpts on 12 Nov; this reverses that choice, so it is your call. Do it AFTER the 17 Nov demo (freeze).

**What "yes" does (2 minutes):**
1. Adds a password to `.env` (you choose it; never printed): `APP_PASSWORD=<your password>`
2. Redeploys: `DOMAIN=mentor.medevolv.in deploy/oci/push.sh 130.210.60.153`
3. Verifies the site asks for the password and the atlas and sme-cashflow sites still load.

The password gate already exists in `app.py` (`APP_PASSWORD`); no code change is needed. Hiding excerpts entirely is a
separate small code change, to be done with tests.
