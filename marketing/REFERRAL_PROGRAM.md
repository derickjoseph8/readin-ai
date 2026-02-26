# ReadIn AI - Referral Program

## Program Name: "Brilliant Together"

---

## Program Overview

The ReadIn AI referral program rewards users for spreading the word. Both the referrer and the referred user receive benefits, creating a win-win growth engine.

---

## Reward Structure

### Standard Referral Rewards

| Action | Referrer Gets | New User Gets |
|--------|---------------|---------------|
| Friend signs up for trial | - | 7-day free trial |
| Friend converts to paid | 1 month free | 1 month free (2 months total) |
| Friend stays 3+ months | $10 account credit | - |

### Reward Caps
- Maximum 12 free months per year from referrals
- No limit on $10 credits (can be used for upgrades)
- Credits never expire

---

## How It Works

### For Referrers

1. **Get Your Link**
   - Log in to dashboard
   - Go to Settings → Referrals
   - Copy your unique referral link: `getreadin.us/r/USERNAME`

2. **Share With Friends**
   - Share via email, social media, WhatsApp, etc.
   - Each link tracks who you referred

3. **Earn Rewards**
   - When friend starts trial → they get extended trial
   - When friend pays → you both get 1 month free
   - When friend stays 3 months → you get $10 credit

### For New Users

1. **Click Referral Link**
   - Link takes them to signup page
   - Referral code auto-applied

2. **Sign Up & Try**
   - Standard 7-day trial
   - Full access to all features

3. **Convert & Save**
   - When they pay, they get 1 extra month free
   - That's 2 months for the price of 1 on first payment

---

## Referral Link Format

```
Standard: https://www.getreadin.us/r/{username}
Short: https://readin.us/r/{username}
With UTM: https://www.getreadin.us/r/{username}?utm_source=referral&utm_medium=share
```

### QR Code
Each user gets a unique QR code that links to their referral URL.

---

## Referral Dashboard

### Dashboard Features

**Overview Stats**:
- Total referrals sent
- Trials started
- Conversions
- Rewards earned
- Pending rewards

**Referral History Table**:
| Date | Friend | Status | Your Reward |
|------|--------|--------|-------------|
| Feb 26 | john@... | Paid (2 months) | 1 month free ✓ |
| Feb 24 | sarah@... | Trial (Day 3) | Pending... |
| Feb 20 | mike@... | Expired | - |

**Share Tools**:
- Copy link button
- Share to Twitter
- Share to LinkedIn
- Share to WhatsApp
- Download QR code
- Email template

---

## Email Templates for Sharing

### Template 1: Professional

**Subject**: This AI tool changed my meetings

```
Hey [Name],

I've been using this AI tool called ReadIn AI and it's been a game-changer for my meetings.

It listens to my calls and gives me real-time talking points - like having an expert whispering in my ear. Saved me multiple times when I didn't know the answer.

Use my link to get an extra month free when you subscribe:
[REFERRAL_LINK]

Let me know what you think!

[Your Name]
```

### Template 2: Casual

**Subject**: You need this for your meetings

```
Hey!

Found this amazing app - ReadIn AI. It gives you AI-powered talking points during meetings in real-time.

No more freezing when someone asks a tough question.

Try it free and get a bonus month when you subscribe:
[REFERRAL_LINK]

Trust me on this one.

[Your Name]
```

### Template 3: Job Seeker Focus

**Subject**: This helped me ace my interviews

```
Hi [Name],

Remember when I mentioned I was preparing for interviews? I found this tool called ReadIn AI that helped me SO much.

It runs during your interview and suggests answers based on what they ask. Like having a coach right there with you.

Here's my referral link (you get an extra month free):
[REFERRAL_LINK]

Good luck with your job search!

[Your Name]
```

---

## Social Share Messages

### Twitter/X

**Option 1**:
```
Just discovered @ReadInAI and my meetings have never been better. AI-powered talking points in real-time = no more awkward silences.

Get a free month with my link: [LINK] #AI #Productivity
```

**Option 2**:
```
POV: You're in a tough meeting and AI is feeding you perfect talking points in real-time.

That's @ReadInAI. Use my link for a free bonus month: [LINK]
```

### LinkedIn

```
🎯 Game-changer alert for anyone who spends time in meetings.

I've been using ReadIn AI - it's an AI assistant that gives you real-time talking points during calls. Whether it's a sales pitch, client meeting, or interview, you always have the perfect response.

The result? More confidence, better conversations, and honestly, better outcomes.

If you want to try it, use my referral link and we both get a free month: [LINK]

#AI #Productivity #MeetingIntelligence
```

### WhatsApp

```
Hey! 👋

Have you tried ReadIn AI? It's this app that gives you AI talking points during meetings - like having a cheat sheet that updates in real time.

Use my link and you get a free extra month: [LINK]

Let me know if you try it! 🚀
```

---

## Gamification & Leaderboard

### Referral Tiers

| Tier | Referrals | Badge | Bonus |
|------|-----------|-------|-------|
| Starter | 1-2 | 🌟 | - |
| Advocate | 3-5 | ⭐⭐ | Extra 1 month |
| Champion | 6-10 | 🏆 | Extra 2 months |
| Ambassador | 11-25 | 👑 | Extra 3 months + swag |
| Legend | 26+ | 💎 | Lifetime discount (20%) |

### Monthly Leaderboard

**Top 10 referrers each month win**:
- 1st Place: 6 months free + ReadIn AI hoodie
- 2nd Place: 3 months free + ReadIn AI t-shirt
- 3rd Place: 2 months free
- 4th-10th: 1 month free

### Leaderboard Display
- First name + last initial only (privacy)
- Country flag
- Number of referrals this month
- All-time referrals

---

## Regional Adaptations

### Africa & UAE Program Enhancements

**Additional Rewards**:

| Reward Type | Details |
|-------------|---------|
| Mobile Data | Partner with MTN/Safaricom for data rewards |
| Airtime | $5 airtime for first referral conversion |
| M-Pesa Bonus | KES 500 M-Pesa credit (Kenya) |

**Localized Sharing**:
- WhatsApp-first sharing (dominant in Africa)
- SMS share option
- Local language share messages (Swahili, French)

### Team Referrals

**When a referred user signs up for Team plan**:
- Referrer gets: 2 months free (instead of 1)
- New user team gets: 1 month free per seat

**When a referred user signs up for Enterprise**:
- Referrer gets: 3 months free + $100 credit
- Custom discussion with sales team

---

## Technical Implementation

### Referral Code System

```
Code Format: [USERNAME] or [RANDOM_8_CHARS]
Examples:
- john_smith
- AB12CD34

Storage:
- User table: referral_code, referred_by
- Referral table: referrer_id, referred_id, status, reward_issued, created_at
```

### Tracking Flow

```
1. User A shares link: getreadin.us/r/userA
2. User B clicks link
3. Cookie set: referral_code=userA (30-day expiry)
4. User B signs up → referral_code saved to account
5. User B converts to paid → trigger reward for both
6. User B stays 3 months → trigger bonus for User A
```

### Cookie Handling
- First-touch attribution (first referral link wins)
- 30-day cookie window
- Stored in localStorage as backup
- URL parameter override available

### Fraud Prevention

**Rules**:
1. Cannot refer yourself (email/device check)
2. Cannot refer same household (IP grouping)
3. Referred user must have unique payment method
4. Minimum 1 week between referral rewards
5. Manual review for 5+ referrals in 24 hours

**Detection**:
- Device fingerprinting
- IP analysis
- Payment method uniqueness
- Email domain patterns
- Behavior analysis

---

## API Endpoints

### Get Referral Info
```
GET /api/v1/referral/info
Response:
{
  "referral_code": "john_smith",
  "referral_link": "https://www.getreadin.us/r/john_smith",
  "stats": {
    "total_referrals": 12,
    "active_trials": 2,
    "conversions": 8,
    "pending_rewards": 1,
    "total_earned_months": 8,
    "total_earned_credits": 30
  },
  "tier": "champion",
  "leaderboard_rank": 45
}
```

### Get Referral History
```
GET /api/v1/referral/history
Response:
{
  "referrals": [
    {
      "id": "ref_123",
      "email_masked": "j***@gmail.com",
      "status": "paid",
      "signup_date": "2026-02-20",
      "conversion_date": "2026-02-25",
      "reward_type": "free_month",
      "reward_issued": true
    }
  ]
}
```

### Apply Referral Code
```
POST /api/v1/referral/apply
Body: { "code": "john_smith" }
Response:
{
  "success": true,
  "referrer_name": "John S.",
  "bonus": "1 free month on conversion"
}
```

---

## Email Sequences

### For Referrer

**When friend signs up**:
```
Subject: 🎉 [Friend] just started their ReadIn AI trial!

Hey [Name],

Great news! Someone you referred just started their free trial of ReadIn AI.

Your referral: [Friend email masked]
Status: Trial started

If they subscribe, you'll both get 1 month free!

Keep sharing: [REFERRAL_LINK]

Your referral stats:
- Total referrals: X
- Conversions: Y
- Months earned: Z

Cheers,
The ReadIn AI Team
```

**When friend converts**:
```
Subject: 🎊 You earned a free month of ReadIn AI!

Hey [Name],

Amazing news! Your referral just subscribed to ReadIn AI Premium.

You've earned: 1 FREE month
Your friend earned: 1 FREE month

Your new subscription end date: [DATE]

Keep the momentum going: [REFERRAL_LINK]

Thanks for spreading the word!

The ReadIn AI Team
```

### For Referred User

**Welcome email with referral bonus**:
```
Subject: Welcome! Your friend hooked you up 🎁

Hey [Name],

Welcome to ReadIn AI! Your friend [Referrer name] referred you, which means you get a special bonus.

Your perks:
✓ 7-day free trial (starts now)
✓ When you subscribe: 1 extra month FREE

That's 2 months for the price of 1 on your first payment!

Start your trial: [DASHBOARD_LINK]

Sound brilliant in every meeting,
The ReadIn AI Team
```

---

## Promotion Periods

### Launch Promotion (First 90 days)
- 2x rewards: Referrer gets 2 months free per conversion
- Featured on homepage
- Social media amplification of top referrers

### Holiday Promotions

| Holiday | Promotion | Markets |
|---------|-----------|---------|
| Black Friday | 3x rewards for 1 week | All |
| Cyber Monday | Extra $20 credit per referral | All |
| New Year | 2x rewards for January | All |
| Back to School | Student referrals = 2x | All |
| Ramadan | Special community rewards | Africa/UAE |
| Diwali | 2x rewards week | UAE/Asia |

---

## Terms & Conditions Summary

1. Referral rewards are for new customers only
2. Self-referrals are not permitted
3. Rewards are non-transferable and have no cash value
4. Maximum 12 free months per year from referrals
5. ReadIn AI reserves right to modify program
6. Fraudulent activity results in account termination
7. Rewards applied within 48 hours of qualification
8. Referred user must maintain paid subscription for 30 days for referrer to keep reward

---

## Success Metrics

| Metric | Target (Year 1) |
|--------|-----------------|
| Referral participation rate | 20% of users share |
| Referral conversion rate | 15% of shares → trials |
| Trial-to-paid from referrals | 12% (higher than organic) |
| % of new users from referrals | 25% |
| Referral program CAC | $15 (vs $25 paid) |
| NPS of referred users | 55+ |

---

## Marketing the Referral Program

### In-App Prompts
- After first successful meeting: "Love ReadIn AI? Share with friends"
- After 7 days of use: "Get free months by referring friends"
- Monthly reminder in dashboard

### Email Marketing
- Dedicated referral program email in onboarding sequence
- Monthly "Your referral stats" email
- Top referrer spotlight emails

### Social Proof
- "Join 5,000+ users who've earned free months"
- Show recent referral activity (anonymized)
- Feature success stories

---

*Document created: February 26, 2026*
