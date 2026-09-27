# Edge cases and where they are tested

Each row is enforced in `public/core.js` (the same code runs on the server and
in the demo) and tested in `test/core.test.js` or `test/server.test.js`.
Run them with `npm test`.

## Login
| Case | Behaviour |
|---|---|
| Phone typed as `+91 98765 43210`, `098765…`, `9198765…` | Normalised to 10 digits |
| Landline, 5-digit or 11-digit number | Rejected: "Enter a valid 10-digit Indian mobile number" |
| Wrong OTP | "Wrong OTP. 4 tries left", locked after 5 tries |
| OTP older than 5 minutes, or reused | Rejected, ask for a new one |
| OTP requested again and again (SMS cost abuse) | At most 3 per 10 minutes per phone |
| Live mode | The OTP is never returned in the response, and there is no demo login |
| Expired or logged-out session | 401, and the app returns to login |

## Booking
| Case | Behaviour |
|---|---|
| Date in the past, or today's slot already started | Rejected |
| More than 30 days ahead, or 30 Feb | Rejected |
| 8 acres in a morning slot | Rejected. At most 7.5 acres fit in 5 hours (1.5 acres/hour); pick a full day |
| 1.3 acres | Rejected. Half-acre steps |
| 21 workers | Rejected. 1–20 per booking |
| The same work, field and time booked twice | 409 `DUPLICATE_BOOKING` |
| More than 10 open bookings | 409, finish or cancel one first |
| Nobody available nearby | Booking still allowed with a warning. Travel is priced at an assumed 15 km and locked |
| Earlier late-cancellation fee | Added to the next booking. It comes back if that booking is cancelled free or expires |
| IST midnight | "Today" follows India time, not the server's time zone |

## Matching and races
| Case | Behaviour |
|---|---|
| Two tractor owners tap "Accept" together | The first wins. The second gets "no longer open". Node handles one request at a time, so no double booking |
| Provider already booked at an overlapping time | Cannot accept. A full day overlaps both half days |
| Wrong service, skill not listed, unverified, paused, outside travel radius | Cannot accept, with the reason given |
| Customer who is also a provider | Cannot accept their own booking |
| Worker withdraws, then tries to rejoin | Refused, so providers can't flip-flop |

## During the job
| Case | Behaviour |
|---|---|
| Start before 1 h ahead of the slot | Refused |
| Wrong PIN | Refused. After 5 wrong tries, locked for 15 minutes |
| Only 3 of 4 workers came | Starts with 3, and the price is recalculated for 3 |
| Tractor did 2.5 acres instead of 2 | Actual acres entered, capped at 2× booked, price recalculated |
| Mechanic parts bill | Whole rupees from ₹0 to ₹50,000, shown on the bill |
| Rating before completion, rating twice, 6 stars | Refused |

## Cancellation, no-show, expiry
| Case | Behaviour |
|---|---|
| Cancel before anyone accepts, or more than 12 h ahead | Free |
| Cancel within 12 h after a provider accepted | ₹50 per provider, carried to the next booking |
| Provider still not there 2 h after the start time | Customer cancels free, provider gets a strike |
| Provider withdraws within 12 h | Strike. 3 strikes pause the account until an admin restores it |
| Rain | One free date change. Providers still free on the new date stay, others are released without a strike |
| Nobody accepts by 2 h after the start time | Booking expires |
| Some workers accepted but the job never started | Expires at the end of the slot |

## Privacy and complaints
| Case | Behaviour |
|---|---|
| Stranger opens a booking link | 403 |
| Provider views an open job | Sees first name, village, landmark and earning. Never the phone number or PIN |
| Provider views a job they accepted | Sees the customer's name and phone. Never the PIN |
| Complaint after 48 h, or without a reason | Refused |
| Refund bigger than the bill | Refused |

## Server
| Case | Behaviour |
|---|---|
| Malformed JSON | 400 |
| Body over 64 KB | 413 |
| `/../server.js` path traversal | Blocked |
| Server restart | Data survives. It's written atomically (temp file, then rename) |
