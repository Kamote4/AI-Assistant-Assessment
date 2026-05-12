# Sample Enquiries

Six representative enquiries for testing. These correspond directly to the sample buttons in the UI.

---

## 1. New Client

```
Hi there, I'm looking to engage your services for a new strata scheme. We have a 42-unit
residential apartment building in North Sydney that currently self-manages, and the owners
corporation committee recently voted to bring in a professional management company. Could you
please send me an information pack about your services, management fees, and what the onboarding
process looks like? We're hoping to transition before the end of the financial year.
```

**Expected classification:** New Client
**Expected confidence:** High (0.90+)
**Expected urgency:** Low–Medium
**Expected needs_human_review:** false

---

## 2. Support Request

```
Good morning. I'm the treasurer for the owners corporation at 88 Harbour View Drive (Lot 14).
We passed a resolution at our AGM last month to update our by-laws regarding short-term rental
accommodation. Could you please advise on the process for having the updated by-laws registered,
what documentation we need to provide, the estimated timeline, and any associated costs?
```

**Expected classification:** Support Request
**Expected confidence:** High (0.88+)
**Expected urgency:** Low
**Expected needs_human_review:** false

---

## 3. Complaint

```
I am writing to formally complain about the complete lack of action on the maintenance issue I
reported six weeks ago. The stairwell lighting on levels 3 and 4 has been broken since September,
creating a genuine safety hazard. I have sent three emails to your office with no response
whatsoever. If this matter is not resolved within five working days I will be escalating to NSW
Fair Trading.
```

**Expected classification:** Complaint
**Expected confidence:** High (0.92+)
**Expected urgency:** High
**Expected needs_human_review:** true (complaints always flagged)

---

## 4. General Question

```
Hello, I recently received my quarterly levy notice and I'm a bit confused. There are two separate
line items listed — one for the administrative fund and one for the capital works fund. Could you
please explain the difference between these two? I want to understand what each one is used for
before I make payment.
```

**Expected classification:** General Question
**Expected confidence:** High (0.90+)
**Expected urgency:** Low
**Expected needs_human_review:** false

---

## 5. Vague Input

```
Hi, can you help me with my strata issue? It's quite urgent.
```

**Expected classification:** Unknown / Needs Human Review
**Expected confidence:** Low (below 0.70)
**Expected urgency:** Medium or High
**Expected needs_human_review:** true

---

## 6. Nonsensical Input

```
purple forty seven banana sky orange umbrella cat twelve sixteen
```

**Expected classification:** Unknown / Needs Human Review
**Expected confidence:** Very low (near 0.0)
**Expected urgency:** Unknown
**Expected needs_human_review:** true
