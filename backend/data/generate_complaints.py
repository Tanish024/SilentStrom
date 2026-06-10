"""
generate_complaints.py — Generates 200 synthetic fraud complaints for SilentStorm.

Run:  python generate_complaints.py
Output: complaints.json (same directory)

Campaigns:
  A — 50 KYC fraud (SBI / HDFC KYC Verify app, Hindi+English mix)
  B — 50 Loan scam (Easy Loan Approval / PM Loan App)
  C — 40 Investment scam (Stock Profit Pro / SEBI Trading, 7-day dormancy gap)
  D — 60 Delivery fraud (Amazon / Flipkart Delivery Failed)
  Total = 200
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

OUTPUT = Path(__file__).parent / "complaints.json"

# ── Shared UPI hub IDs per campaign (reused 2-3 per campaign) ─────────
CAMPAIGN_UPIS = {
    "A": ["ravi.kyc@ybl", "sbi.update2024@oksbi", "hdfc.verify@paytm"],
    "B": ["easyloan.proc@ybl", "pmloan.fee@oksbi", "loan.help99@paytm"],
    "C": ["stockpro.invest@ybl", "sebi.trade24@oksbi", "profit.guru@paytm"],
    "D": ["delivery.refund@ybl", "amz.help2024@oksbi", "fkrt.return@paytm"],
}

# ── Phone pools per campaign ──────────────────────────────────────────
CAMPAIGN_PHONES = {
    "A": ["9876543210", "9123456780", "8899001122"],
    "B": ["9988776655", "8877665544", "7766554433"],
    "C": ["9090909090", "8181818181", "7272727272"],
    "D": ["9345678901", "8456789012", "7567890123"],
}

# ── Date ranges ───────────────────────────────────────────────────────
BASE = datetime(2026, 5, 1)

def date_range_A():
    return BASE + timedelta(days=random.randint(0, 30))

def date_range_B():
    return BASE + timedelta(days=random.randint(0, 25))

def date_range_C_with_dormancy():
    """First batch: May 1-15, dormancy gap May 16-22, second batch: May 23 - Jun 5."""
    if random.random() < 0.55:
        return BASE + timedelta(days=random.randint(0, 14))
    else:
        return BASE + timedelta(days=random.randint(22, 35))

def date_range_D():
    return BASE + timedelta(days=random.randint(0, 35))

# ── Complaint text templates ──────────────────────────────────────────

TEMPLATES_A = [
    "SBI se call aaya ki KYC expire ho gaya hai. SBI KYC Verify app download karke OTP diya, phir account se ₹{amt} kat gaye.",
    "Got a call from someone claiming to be HDFC Bank, asked to install HDFC KYC Verify app for KYC update. After sharing OTP, ₹{amt} was debited from my account.",
    "Mujhe SMS aaya SBI KYC update karo warna account block ho jayega. App install kiya aur ₹{amt} nikal liye.",
    "HDFC Bank KYC verification ke naam pe fraud hua. HDFC KYC Verify app se OTP liya aur ₹{amt} le gaye.",
    "Someone posing as SBI called about KYC expiry. Made me download SBI KYC Verify app. Lost ₹{amt} via UPI.",
    "KYC update ke liye HDFC se bola, HDFC KYC Verify app install karwaya, OTP maanga aur ₹{amt} UPI se transfer ho gaye.",
    "Fake SBI customer care ne KYC ke naam pe SBI KYC Verify app install karwaya. ₹{amt} ka fraud hua meri UPI ID se.",
    "Received call from +91-{phone} about HDFC KYC. Installed HDFC KYC Verify and shared OTP. ₹{amt} stolen from my savings.",
    "SBI KYC Verify naam ka app tha, install karne ke baad screen sharing start ho gayi aur ₹{amt} nikal liye account se.",
    "Got WhatsApp message about SBI KYC mandatory update. Downloaded SBI KYC Verify app from link. ₹{amt} debited immediately.",
    "Bank KYC update ke baare mein call aaya. HDFC KYC Verify install kiya, 2 OTP share kiye aur ₹{amt} gaye.",
    "Caller said my SBI account will be frozen without KYC. SBI KYC Verify app ne remote access liya aur ₹{amt} transfer kiye.",
    "HDFC KYC ke naam pe link bheja WhatsApp pe. HDFC KYC Verify install karne ke baad ₹{amt} fraud hua.",
    "SBI se bolke KYC re-verification ke liye call kiya. SBI KYC Verify app se personal details liye aur ₹{amt} chori.",
    "I complained about SBI KYC Verify app fraud. They took my Aadhaar, PAN via the app and transferred ₹{amt} using UPI.",
    "KYC update ka bahana dekar HDFC KYC Verify app install karwaya. UPI se ₹{amt} aur credit card se ₹{amt2} ka fraud.",
    "Fake call about SBI KYC expiry. Installed SBI KYC Verify, they got AnyDesk access and transferred ₹{amt} out.",
    "Maine HDFC KYC Verify app install kiya bank ke naam pe, phir unka agent UPI se ₹{amt} le gaya.",
    "SBI KYC update scam — caller guided me through SBI KYC Verify app. I entered OTP and ₹{amt} vanished.",
    "HDFC wala bolke KYC ke liye call kiya, HDFC KYC Verify app download karwaya. Account se ₹{amt} gaye.",
]

TEMPLATES_B = [
    "Applied for personal loan on Easy Loan Approval app. They asked for ₹{amt} processing fee via UPI. Never got loan.",
    "PM Loan App se loan apply kiya tha. ₹{amt} advance fee maangi, bheja, phir number band ho gaya.",
    "Easy Loan Approval app ne instant loan ka offer diya. Processing fee ₹{amt} UPI se li aur phir app hi band ho gaya.",
    "PM Loan App pe loan sanctioned dikha raha tha. Insurance fee ₹{amt} maangi, di, phir aur ₹{amt2} verification fee maangi.",
    "Loan ke liye Easy Loan Approval pe apply kiya, ₹{amt} GST fee ke naam pe liya aur loan kabhi nahi mila.",
    "Got SMS about instant loan from PM Loan App. Paid ₹{amt} processing fee. No loan disbursed. Phone unreachable now.",
    "Easy Loan Approval app said my CIBIL is approved for ₹5 lakh loan. Asked ₹{amt} file charge. Total scam.",
    "PM Loan App se ₹2 lakh ka loan apply kiya. Processing ₹{amt} aur insurance ₹{amt2} li phir block kar diya.",
    "Easy Loan Approval scam — first ₹{amt} processing, then ₹{amt2} verification, then ₹{amt2} GST. Total fraud.",
    "PM Loan App ka ad dekha Instagram pe. Loan ke liye apply kiya, ₹{amt} registration fee li, scam nikla.",
    "Loan app Easy Loan Approval ne documents liye aur ₹{amt} advance charge kiya. No disbursement. Fraud hai.",
    "PM Loan App offered pre-approved loan. Required ₹{amt} stamp duty via UPI. Money gone, no loan received.",
    "Easy Loan Approval se personal loan lena tha, ₹{amt} processing fee di lekin account mei kuch nahi aaya.",
    "PM Loan App pe loan approved status tha. ₹{amt} insurance mandatory bola. Paid and app stopped working.",
    "Applied through Easy Loan Approval for emergency loan. Paid ₹{amt} for credit check. Total fraud, blocked my number.",
    "PM Loan App ne pehle ₹{amt} registration fee li, phir ₹{amt2} legal fee maangi. Sab fraud tha.",
    "Easy Loan Approval told me CIBIL verified, loan ready. Just pay ₹{amt} disbursement charge. Paid, nothing happened.",
    "PM Loan App WhatsApp pe ad tha. ₹{amt} file opening fee di. Loan sanction letter bhi fake nikla.",
    "Mujhe Easy Loan Approval se call aaya, ₹3 lakh loan offer kiya. ₹{amt} processing fee UPI se le gaye.",
    "PM Loan App se government loan scheme ka jhansa diya. ₹{amt} advance fee li aur gayab ho gaye.",
]

TEMPLATES_C = [
    "Invested ₹{amt} in Stock Profit Pro app. Initially showed 200% returns. When tried to withdraw, asked for more deposit.",
    "SEBI Trading platform pe ₹{amt} invest kiya. Profits dikh rahe the. Withdrawal ke liye ₹{amt2} tax maangi.",
    "Stock Profit Pro app showed my portfolio growing daily. Put in ₹{amt} total. Cannot withdraw. App customer care unreachable.",
    "SEBI Trading naam se trading app tha. ₹{amt} invest kiya, fake profits dikhaye, aur jab nikalne gaya toh block kar diya.",
    "Invested ₹{amt} via Stock Profit Pro after seeing returns in WhatsApp group. All fake. Withdrawal is locked.",
    "SEBI Trading app promised guaranteed returns. Invested ₹{amt} in 3 installments. Dashboard shows ₹{amt2} profit but cannot withdraw.",
    "Stock Profit Pro sent me daily profit screenshots. I invested ₹{amt}. When I asked for withdrawal, they demanded ₹{amt2} tax fee.",
    "SEBI Trading pe IPO investment ka offer tha. ₹{amt} invest kiya. Returns dikhaye lekin withdrawal ke liye aur paisa maanga.",
    "Friend referred Stock Profit Pro for crypto trading. Put ₹{amt} in. Fake dashboard shows profits. Money is stuck.",
    "SEBI Trading app ne mutual fund ke naam pe ₹{amt} liye. Profit dikha raha hai lekin withdraw nahi ho raha.",
    "Stock Profit Pro mentor added me on Telegram. Guided trades, made me invest ₹{amt}. Now says pay ₹{amt2} to unlock.",
    "SEBI Trading platform asked ₹{amt} initial investment. After 2 weeks demanded ₹{amt2} upgrade fee for withdrawal access.",
    "Stock Profit Pro promised 5x returns on intraday trades. Invested ₹{amt} total over a month. Complete fraud.",
    "SEBI Trading se commodity trading ka offer mila. ₹{amt} invest kiya, ab koi response nahi aa raha.",
    "Joined Stock Profit Pro VIP group. Invested ₹{amt} following their calls. All trades were fake. Money gone.",
    "SEBI Trading app had my PAN and bank details. They invested ₹{amt} and now claim ₹{amt2} penalty for early exit.",
    "Stock Profit Pro mein forex trading kiya. ₹{amt} lagaye the, app ne fake profit dikhaya aur block kar diya.",
    "SEBI Trading pe gold trading ka plan tha. ₹{amt} invest kiya. Withdrawal locked. Support number is fake.",
    "Stock Profit Pro Telegram group me add kiya. Daily tips diye, ₹{amt} invest karwaya. Sab fraud nikla.",
    "SEBI Trading se SIP jaise invest kiya ₹{amt}. Dashboard me ₹{amt2} dikh raha hai but withdrawal pe aur fee maang rahe.",
]

TEMPLATES_D = [
    "Got SMS saying Amazon delivery failed. Clicked link, entered address and card details. ₹{amt} debited from account.",
    "Flipkart delivery failed ka message aaya. Form fill kiya with UPI PIN. Account se ₹{amt} kat gaye.",
    "Amazon Delivery Failed ka SMS mila. Link pe click kiya, reschedule ke liye ₹{amt} charge hua aur paise chale gaye.",
    "Flipkart se delivery attempt failed ka mail aaya. Link open kiya, OTP diya aur ₹{amt} fraud hua.",
    "Amazon Delivery Failed SMS se phishing link tha. Address confirm karne pe UPI se ₹{amt} nikal gaye.",
    "Got fake Flipkart delivery notification. Said package held at warehouse. Paid ₹{amt} redelivery charge. Total scam.",
    "Amazon parcel failed delivery ka message WhatsApp pe aaya. Link pe jaake details diye. ₹{amt} stolen.",
    "Flipkart Delivery Failed email mila with tracking number. Clicked reschedule, entered UPI, ₹{amt} debited.",
    "Amazon Delivery Failed SMS with fake tracking link. Entered card CVV for verification. ₹{amt} unauthorized transaction.",
    "Flipkart delivery issue ka call aaya. Agent ne refund ke baahane UPI collect request bheja. ₹{amt} chala gaya.",
    "Fake Amazon delivery failed text. Link opened a page that looked exactly like Amazon. Entered details, lost ₹{amt}.",
    "Flipkart Delivery Failed ka notification aaya. Reschedule ke liye ₹{amt} pay kiya. Order toh exist hi nahi karta.",
    "Amazon se delivery failed bola. WhatsApp pe link bheja. Address update karne pe ₹{amt} deducted via UPI.",
    "Got Flipkart delivery attempt failed SMS. Entered details on phishing site. ₹{amt} taken from my bank.",
    "Amazon Delivery Failed phishing — clicked link, page asked for net banking login. ₹{amt} transferred out.",
    "Flipkart parcel delivery failed ka SMS. Paid ₹{amt} customs/redelivery on fake page. Money gone.",
    "Amazon se call aaya delivery failed hai, refund ke liye app install karo. App installed karke ₹{amt} le gaye.",
    "Flipkart Delivery Failed notification mila. Verification ke liye OTP diya. Account se ₹{amt} nikal liye.",
    "Fake Amazon delivery SMS. Link looked legit. Entered debit card info for redelivery. ₹{amt} debited next day.",
    "Flipkart se delivery failed ka automated call aaya. IVR me details diye. ₹{amt} ka unauthorized charge hua.",
    "Amazon Delivery Failed ke naam pe SMS link bheja. Maine click kiya aur card details diye. ₹{amt} fraud hua.",
    "Flipkart wala bolke call kiya, delivery failed hai refund denge. UPI collect bheja ₹{amt} ka. Galti se approve kar diya.",
    "Amazon package undelivered ka email. Link pe jaake bank details di. ₹{amt} immediately debited ho gaye.",
    "Flipkart Delivery Failed SMS mila. Reschedule button pe click kiya. Fake payment page se ₹{amt} kata.",
    "Got Amazon delivery issue call. Caller asked to share screen via AnyDesk for refund. They transferred ₹{amt} out.",
    "Flipkart se bola delivery fail, ₹{amt} re-attempt fee do. UPI se pay kiya. Order number fake tha.",
    "Amazon Delivery Failed SMS laga genuine. Link pe address update karne gaya. Background me ₹{amt} UPI se nikal gaye.",
    "Flipkart delivery failed. Refund ke liye call kiya toh fake customer care ne ₹{amt} le liye UPI se.",
    "Received Amazon Delivery Failed text with link. Page asked phone number and OTP. ₹{amt} debited.",
    "Flipkart Delivery Failed ka WhatsApp msg. Link se form bhara, card details diye. ₹{amt} ka transaction hua.",
]

AMOUNTS = [
    "5,000", "8,000", "10,000", "12,000", "15,000", "18,000", "20,000",
    "25,000", "30,000", "35,000", "40,000", "45,000", "50,000", "75,000", "1,00,000",
]
AMOUNTS_SMALL = [
    "1,500", "2,000", "2,500", "3,000", "3,500", "4,000", "4,500", "5,000",
]

def pick_amt():
    return random.choice(AMOUNTS)

def pick_amt_small():
    return random.choice(AMOUNTS_SMALL)


def generate_campaign(
    campaign: str,
    count: int,
    templates: list[str],
    date_fn,
    id_offset: int,
) -> list[dict]:
    upis = CAMPAIGN_UPIS[campaign]
    phones = CAMPAIGN_PHONES[campaign]
    lang_pool = ["hi", "en", "hi-en"] if campaign in ("A", "C") else ["en", "hi", "hi-en"]
    complaints = []

    for i in range(count):
        cid = f"C{campaign}-{id_offset + i + 1:04d}"
        template = templates[i % len(templates)]
        phone = random.choice(phones)
        text = template.replace("{amt}", pick_amt()).replace("{amt2}", pick_amt_small()).replace("{phone}", phone)

        # Each complaint references 1-2 of the shared hub UPIs
        n_upis = random.choice([1, 1, 2])
        selected_upis = random.sample(upis, min(n_upis, len(upis)))

        # Each complaint has 1 phone (from the shared pool)
        selected_phones = [phone]

        dt = date_fn()
        complaints.append({
            "id": cid,
            "text": text,
            "upi_ids_raw": selected_upis,
            "phone_raw": selected_phones,
            "language": random.choice(lang_pool),
            "date": dt.strftime("%Y-%m-%d"),
        })

    return complaints


def main():
    all_complaints = []

    # Campaign A — 50 KYC fraud
    all_complaints.extend(generate_campaign("A", 50, TEMPLATES_A, date_range_A, 0))

    # Campaign B — 50 Loan scam
    all_complaints.extend(generate_campaign("B", 50, TEMPLATES_B, date_range_B, 0))

    # Campaign C — 40 Investment scam (with 7-day dormancy gap)
    all_complaints.extend(generate_campaign("C", 40, TEMPLATES_C, date_range_C_with_dormancy, 0))

    # Campaign D — 60 Delivery fraud
    all_complaints.extend(generate_campaign("D", 60, TEMPLATES_D, date_range_D, 0))

    assert len(all_complaints) == 200, f"Expected 200, got {len(all_complaints)}"

    # Shuffle so campaigns are interleaved (more realistic)
    random.shuffle(all_complaints)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(all_complaints, f, indent=2, ensure_ascii=False)

    print(f"✅ Generated {len(all_complaints)} complaints → {OUTPUT}")

    # Print campaign breakdown
    from collections import Counter
    campaign_counts = Counter(c["id"][:2] for c in all_complaints)
    for k, v in sorted(campaign_counts.items()):
        print(f"   {k}: {v} complaints")


if __name__ == "__main__":
    main()
