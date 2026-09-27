# KhetSaathi (खेत साथी): product plan

*"Uber for farm help" for villages and Tier-3 towns.*

## 1. The problem

Many families in villages and small towns own land but don't work it full-time.
Examples: a schoolteacher, a shopkeeper, or a son working in the district town.
When the field needs something, they spend days on the phone:

| Need | How it happens today | What hurts |
|---|---|---|
| Tractor for ploughing or sowing | Call 3–4 tractor owners you know | Everyone wants a tractor in the same 2-week window. No price transparency, and the owner goes to whoever pays more. |
| Daily workers (weeding, watering, transplanting, cutting) | A labour contractor, or neighbours | Workers don't show up, wages are unclear, and you lose half a day to supervision |
| Mechanic (tractor, diesel pump, sprayer) | Take the machine to town | Tractor off the road for days in peak season |
| Someone who knows farming | Ask relatives | No reliable way to hire a day of expert supervision or advice |

On the other side, tractor owners sit idle outside peak weeks. Farm workers find
work through word of mouth only, and village mechanics have no way to be found.

**KhetSaathi connects the two sides.** Book in 30 seconds, see the price up front,
pay in cash after the work is done.

## 2. Who uses it

| Persona | Needs | Design answer |
|---|---|---|
| **Vinod, 42, schoolteacher with 5 acres** (customer). Android phone, reads Hindi, uses WhatsApp and UPI | A tractor on Saturday morning, 4 workers for transplanting next week | 4 big picture tiles, Hindi first, price locked at booking, a PIN so he knows the right person came |
| **Ramesh, 35, tractor owner** (provider) | More paid hours, with no bargaining over every job | Jobs within his chosen distance, his earning shown before he accepts, the customer's phone once he accepts |
| **Geeta, 30, farm worker** (provider). Basic phone skills | Steady daily work near home | 10 km radius, fixed daily wage shown up front, one-tap "Accept" |
| **Anil, mechanic** (provider) | Service calls in peak season | Visit fee is guaranteed; parts are billed on site and shown to the customer |
| **Ram Prasad, 60, experienced farmer** (provider) | Respect and income for his knowledge | "Look after my field for the day" and "Crop advice visit" |
| **Ops team** (admin) | Trust and safety | A verification queue, strikes, complaints with refunds, and a GMV and fill-rate dashboard |

## 3. What the MVP does (built and tested)

**Customer:** OTP login → pick a service → type of work, village, landmark, date,
time slot (morning, afternoon or full day), quantity → see the price breakdown and
how many providers are free nearby → book → get a **4-digit start PIN** → see who
is coming and their phone number → cancel (fee rules apply), or move the date
once for free (for rain) → rate → raise a complaint within 48 h.

**Provider:** join (type, skills, home village, travel radius, tractor number)
→ admin verifies → toggle "available" → see nearby jobs with their earning →
accept → start the job with the customer's PIN → mark it complete (enter the
actual acres or hours, or the parts bill for mechanics) → earnings, rating,
jobs done and strikes.

**Admin:** GMV, fee revenue, fill rate, a verification queue, restoring
paused providers, and resolving complaints with a bounded refund.

**Farm workers are different from rides.** One booking for 4 workers needs 4
separate acceptances. If only 3 turn up, the job starts with 3 and the price
drops to match.

## 4. Pricing and unit economics

Prices come from typical Purvanchal (eastern UP) rates in 2025–26. They are a
catalogue in `public/core.js`, so they can be changed per district.

| Service | Price |
|---|---|
| Tractor ploughing / rotavator / sowing / harvester | ₹1,200 / ₹1,400 / ₹1,000 / ₹2,200 per acre |
| Trolley transport | ₹700 per hour |
| Farm worker | ₹450–500 per day (half day is 60%) |
| Mechanic visit | ₹250–300 plus parts on site |
| Experienced farmer | ₹700 per day, ₹300 per advice visit |
| Travel (tractor or mechanic) | First 5 km free, then ₹15/km, **locked at booking** |
| **Platform fee (customer pays)** | **5% of the work, minimum ₹10, maximum ₹99** |

Why this shape:
- Providers keep 100% of their rate. That's the pitch that gets tractor owners
  to join, when they are the scarce side.
- The fee cap of ₹99 keeps big harvester jobs fair. The ₹10 floor makes small
  jobs worth handling.
- There is **no surge pricing**. In a village, fairness is the brand. Peak demand
  is handled by opening bookings up to 30 days ahead.

Rough unit economics per cluster of about 25 villages:

| Assumption | Value |
|---|---|
| Average order value | ₹1,800 |
| Average fee | ₹75 (about 4.2%) |
| Orders per month in season | 1,500 |
| Fee revenue per month | ₹1.1 lakh |
| Costs: 1 field agent, SMS/OTP, hosting | about ₹45k |

A cluster pays for itself at about 600 orders a month. Later revenue lines:
input delivery (seed, fertiliser), equipment insurance, and credit for providers
based on their earnings history.

## 5. Getting users (the hard part)

Rural marketplaces are won offline first. The plan, in order:

1. **Supply before demand.** Sign up 10 tractors, 40 workers, 3 mechanics and
   5 experienced farmers in one cluster before telling a single customer. The
   field agent registers them on their own phones, using the app's "Join"
   screen, and verifies documents in person.
2. **One cluster, not a state.** Start with the 9 villages seeded in the app
   (Gorakhpur district). Density beats reach: a customer who books and nobody
   comes will not try again.
3. **Channels that work in villages:**
   - The *pradhan* and the local kirana or seed shop. They get a QR poster and
     ₹20 per first booking they refer.
   - WhatsApp groups for each village. Share a booking link and a 30-second
     Hindi voice note.
   - FPOs (Farmer Producer Organisations) and Krishi Vigyan Kendras.
   - Wall paintings at the bus stop and the mandi.
   - An **assisted booking line**: a missed-call number where an agent books
     for the caller. Not everyone will use an app on day one.
4. **Launch timing.** Go live 3 weeks before kharif transplanting (late June)
   or rabi sowing (late October), when the pain is at its worst.
5. **Retention.** A "Book again" button on each booking. For absentee owners,
   season reminders ("Wheat sowing in 10 days, book your tractor").

**Metrics to watch each week:** fill rate (jobs that started ÷ jobs booked), time
until someone accepts, provider no-show rate, repeat booking rate within 30 days,
and orders per active provider. The admin screen already shows GMV, fee revenue
and fill rate.

## 6. Roadmap

| Phase | What | Why |
|---|---|---|
| **0. Now** | Web app (installable PWA) + API + tests + demo | Prove the flow with real people in 1 cluster |
| **1. Pilot (4–6 weeks)** | Real SMS OTP (MSG91 / Twilio), SMS or WhatsApp alerts to providers, Postgres, an assisted-booking agent console | Real users, real phones |
| **2. App** | Android app: wrap the PWA as a Trusted Web Activity (Bubblewrap), or use Capacitor for push notifications and offline use | Push notifications are what make providers respond fast |
| **3. Scale** | UPI collection and payouts (Razorpay Route), per-district price lists, provider KYC with Aadhaar and DL via DigiLocker, voice UI in Bhojpuri and Awadhi | Trust and reach |

## 7. Risks and how the design answers them

| Risk | Mitigation built in |
|---|---|
| The provider doesn't turn up | Strikes (3 pauses the account). The customer can cancel free after 2 h. The job goes back to other providers when someone withdraws. |
| The customer cancels after a tractor has planned the day | ₹50 per provider for cancelling within 12 h, collected on the customer's next booking (cash economy, so no card on file) |
| Fake "job started" by the provider | The job only starts with the customer's 4-digit PIN. 5 wrong tries locks it for 15 minutes. |
| Arguments over price | Price locked at booking. The actual acres are capped at 2× what was booked. The mechanic's parts bill is shown and can be disputed within 48 h. |
| Privacy (phone numbers of women workers, for example) | A phone number is shared only between the customer and the providers who accepted. Open job offers show only the first name and the village. |
| Bad providers | Manual verification before the first job, public rating, admin can pause |
