"""
Seed the knowledge base with ReadIn AI articles for Novah.
Run this script once to populate the knowledge base.
"""

from database import SessionLocal
from models import KnowledgeBaseArticle

# Knowledge base articles for Novah
ARTICLES = [
    # Pricing & Billing
    {
        "title": "ReadIn AI Pricing Plans",
        "category": "pricing",
        "tags": ["pricing", "plans", "cost", "billing", "subscription", "price"],
        "summary": "ReadIn AI offers three plans: Free Trial (7 days), Premium ($29.99/month), and Team ($19.99/user/month).",
        "content": """ReadIn AI Pricing Plans:

**Free Trial**
- 7-day free trial for new users
- Full access to all Premium features
- No credit card required to start
- Automatically expires after 7 days

**Premium Plan - $29.99/month**
- Unlimited real-time AI assistance
- Advanced meeting transcription
- AI-powered talking points
- Meeting summaries and action items
- Priority support
- All integrations included

**Team Plan - $19.99/user/month**
- Everything in Premium
- 5 seats included in base price
- Team admin dashboard
- Shared meeting insights
- Centralized billing
- Team analytics and reporting

All plans include:
- Desktop app for Windows and Mac
- Real-time audio transcription
- AI-generated talking points
- Meeting history and search
- Export options (PDF, TXT, DOCX)

For enterprise pricing or custom plans, please contact our sales team."""
    },
    {
        "title": "Billing and Payment Information",
        "category": "billing",
        "tags": ["billing", "payment", "invoice", "charge", "credit card", "refund"],
        "summary": "We accept major credit cards. Subscriptions renew monthly. Refunds available within 14 days.",
        "content": """Billing and Payment Information:

**Payment Methods**
- Visa, Mastercard, American Express
- PayPal (coming soon)
- Wire transfer for Enterprise plans

**Billing Cycle**
- Subscriptions are billed monthly
- Billing date is based on your signup date
- Invoices sent via email automatically

**Cancellation**
- Cancel anytime from Settings > Billing
- Access continues until end of billing period
- No cancellation fees

**Refunds**
- Full refund within 14 days of purchase
- Pro-rated refunds for annual plans
- Contact support for refund requests

**Receipts & Invoices**
- Available in Settings > Billing > Billing History
- Downloadable as PDF
- Can be sent to a different email for accounting

For billing questions, contact billing@getreadin.us"""
    },
    {
        "title": "How to Cancel Subscription",
        "category": "billing",
        "tags": ["cancel", "subscription", "cancellation", "stop", "end subscription"],
        "summary": "Cancel your subscription anytime from Settings > Billing. Your access continues until the end of your billing period.",
        "content": """How to Cancel Your Subscription:

1. Log in to your ReadIn AI dashboard
2. Go to Settings > Billing
3. Click "Manage Subscription"
4. Select "Cancel Subscription"
5. Confirm cancellation

**What happens when you cancel:**
- Your access continues until the end of your current billing period
- You won't be charged again
- Your data is retained for 30 days after cancellation
- You can reactivate anytime

**Need help canceling?**
Contact support@getreadin.us and we'll assist you."""
    },

    # Features
    {
        "title": "ReadIn AI Features Overview",
        "category": "feature",
        "tags": ["features", "what does it do", "capabilities", "how it works"],
        "summary": "ReadIn AI provides real-time AI assistance during meetings with transcription, talking points, and summaries.",
        "content": """ReadIn AI Features:

**Real-Time AI Assistance**
- Listens to your meetings through system audio
- Instantly generates talking points you can glance at
- Helps you respond naturally and confidently

**Live Transcription**
- Accurate speech-to-text in real-time
- Supports multiple languages
- Speaker identification

**AI-Powered Talking Points**
- Contextual suggestions based on conversation
- Key points highlighted
- Natural phrasing suggestions

**Meeting Summaries**
- Automatic summary generation after meetings
- Key decisions captured
- Action items extracted

**Meeting History**
- Searchable archive of all meetings
- Full transcripts available
- Export to PDF, TXT, or DOCX

**Integrations**
- Works with Zoom, Google Meet, Microsoft Teams
- Calendar integration
- Slack notifications (coming soon)

**Privacy & Security**
- End-to-end encryption
- SOC 2 compliant
- GDPR compliant
- Data never shared with third parties"""
    },
    {
        "title": "How to Use ReadIn AI",
        "category": "guide",
        "tags": ["how to", "get started", "tutorial", "setup", "use"],
        "summary": "Download the app, start a meeting, and ReadIn AI automatically listens and provides real-time assistance.",
        "content": """Getting Started with ReadIn AI:

**Step 1: Download the App**
- Go to getreadin.us/download
- Download for Windows or Mac
- Install and launch the app

**Step 2: Sign In**
- Create an account or sign in
- Your 7-day free trial starts automatically

**Step 3: Configure Audio**
- Click the settings icon
- Select your audio input source
- Choose "System Audio" to capture meeting audio

**Step 4: Start Your Meeting**
- Join your video call (Zoom, Meet, Teams, etc.)
- Click "Start" in ReadIn AI
- The app will begin listening

**Step 5: Get AI Assistance**
- Talking points appear in real-time
- Glance at suggestions as needed
- Rephrase naturally in your own words

**Tips:**
- Position the ReadIn window where you can see it during calls
- Use the minimize feature to keep it compact
- Review meeting summaries afterward for key points"""
    },
    {
        "title": "Supported Platforms and Requirements",
        "category": "feature",
        "tags": ["windows", "mac", "requirements", "system", "platform", "compatibility"],
        "summary": "ReadIn AI works on Windows 10+ and macOS 11+. Requires 4GB RAM and internet connection.",
        "content": """System Requirements:

**Windows**
- Windows 10 or later
- 4GB RAM minimum (8GB recommended)
- 500MB disk space
- Internet connection required

**macOS**
- macOS 11 (Big Sur) or later
- 4GB RAM minimum (8GB recommended)
- 500MB disk space
- Internet connection required
- Microphone permissions required

**Supported Meeting Platforms**
- Zoom
- Google Meet
- Microsoft Teams
- Webex
- Any platform with audio output

**Browser Requirements (for web features)**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+"""
    },

    # Troubleshooting
    {
        "title": "Audio Not Working",
        "category": "troubleshooting",
        "tags": ["audio", "not working", "no sound", "microphone", "problem", "issue"],
        "summary": "If audio isn't being captured, check your audio settings and permissions in the app.",
        "content": """Troubleshooting Audio Issues:

**Check Audio Source**
1. Open ReadIn AI Settings
2. Go to Audio Settings
3. Make sure correct audio source is selected
4. For meeting capture, select "System Audio" or your virtual audio device

**Check Permissions (macOS)**
1. Go to System Preferences > Security & Privacy > Privacy
2. Select Microphone
3. Ensure ReadIn AI is checked

**Check Permissions (Windows)**
1. Go to Settings > Privacy > Microphone
2. Make sure "Allow apps to access your microphone" is On
3. Ensure ReadIn AI has permission

**Still not working?**
- Restart the ReadIn AI app
- Restart your computer
- Reinstall the app from getreadin.us/download
- Contact support@getreadin.us"""
    },
    {
        "title": "App Won't Start or Crashes",
        "category": "troubleshooting",
        "tags": ["crash", "not starting", "error", "frozen", "bug", "problem"],
        "summary": "If the app crashes or won't start, try reinstalling or contact support.",
        "content": """Fixing App Startup Issues:

**Basic Steps**
1. Make sure you have the latest version
2. Restart your computer
3. Try running as Administrator (Windows)

**Reinstall the App**
1. Uninstall ReadIn AI
2. Download the latest version from getreadin.us/download
3. Install fresh

**Check System Requirements**
- Windows 10+ or macOS 11+
- At least 4GB RAM
- 500MB free disk space

**Clear App Data**
- Windows: Delete %APPDATA%/ReadIn AI
- macOS: Delete ~/Library/Application Support/ReadIn AI

**Still having issues?**
Contact support@getreadin.us with:
- Your operating system version
- Error message (if any)
- Screenshot of the issue"""
    },
    {
        "title": "Login Issues",
        "category": "troubleshooting",
        "tags": ["login", "password", "forgot password", "cant login", "sign in"],
        "summary": "If you can't log in, try resetting your password or contact support.",
        "content": """Fixing Login Issues:

**Forgot Password**
1. Go to getreadin.us/forgot-password
2. Enter your email address
3. Check your inbox for reset link
4. Create a new password

**Email Not Found**
- Make sure you're using the email you signed up with
- Check for typos
- Try signing up if you haven't yet

**Account Locked**
- Accounts lock after 5 failed attempts
- Wait 15 minutes and try again
- Or contact support to unlock

**Two-Factor Authentication Issues**
- Use your backup codes if you lost your phone
- Contact support to reset 2FA

**Contact Support**
Email: support@getreadin.us"""
    },

    # Account
    {
        "title": "How to Delete My Account",
        "category": "account",
        "tags": ["delete account", "remove account", "close account", "data deletion"],
        "summary": "To delete your account, go to Settings > Account > Delete Account. All data will be permanently removed.",
        "content": """Deleting Your Account:

**How to Delete**
1. Log in to your dashboard
2. Go to Settings > Account
3. Scroll to "Delete Account"
4. Enter your password to confirm
5. Click "Delete Account"

**What Gets Deleted**
- Your profile and settings
- All meeting recordings and transcripts
- Subscription and billing info
- All associated data

**Important Notes**
- This action is permanent and cannot be undone
- Cancel your subscription first to avoid charges
- Download any data you want to keep before deleting

**Data Retention**
- Data is deleted within 30 days
- Some anonymized analytics may be retained

**Need Help?**
Contact support@getreadin.us"""
    },
    {
        "title": "Privacy and Data Security",
        "category": "security",
        "tags": ["privacy", "security", "data", "gdpr", "encryption", "safe"],
        "summary": "ReadIn AI uses end-to-end encryption and is SOC 2 and GDPR compliant. Your data is never shared.",
        "content": """Privacy and Security at ReadIn AI:

**Data Encryption**
- End-to-end encryption for all data
- TLS 1.3 for data in transit
- AES-256 for data at rest

**Compliance**
- SOC 2 Type II certified
- GDPR compliant
- CCPA compliant
- HIPAA compliant (Enterprise plan)

**Data Handling**
- Audio processed in real-time, not stored permanently
- Transcripts encrypted and stored securely
- Data never sold to third parties
- You own your data

**Access Controls**
- Two-factor authentication available
- Session management
- Role-based access for teams

**Data Retention**
- Active accounts: Data retained while active
- Cancelled accounts: 30-day retention, then deleted
- You can request deletion anytime

**Privacy Policy**
Full details at getreadin.us/privacy"""
    },

    # General FAQ
    {
        "title": "What is ReadIn AI?",
        "category": "faq",
        "tags": ["what is", "about", "explain", "introduction"],
        "summary": "ReadIn AI is a real-time AI assistant that helps you in live conversations by providing instant talking points.",
        "content": """What is ReadIn AI?

ReadIn AI is your real-time AI assistant for live conversations. It listens to your meetings and instantly shows you talking points you can glance at and rephrase naturally.

**Who is it for?**
- Sales professionals
- Customer success managers
- Consultants and advisors
- Anyone who wants to be more confident in meetings

**Key Benefits**
- Never get caught off guard in meetings
- Have the right information at your fingertips
- Sound more knowledgeable and prepared
- Capture key points automatically

**How it Works**
1. Run ReadIn AI during your meeting
2. It listens to the conversation
3. AI generates relevant talking points in real-time
4. You glance at suggestions and respond naturally

Try it free for 7 days at getreadin.us"""
    },
    {
        "title": "Contact and Support",
        "category": "support",
        "tags": ["contact", "support", "help", "email", "phone"],
        "summary": "Contact us at support@getreadin.us or through the chat widget in your dashboard.",
        "content": """Contact ReadIn AI:

**Support**
- Email: support@getreadin.us
- Chat: Use the chat widget in your dashboard
- Response time: Within 24 hours (usually faster)

**Sales**
- Email: sales@getreadin.us
- For enterprise inquiries and demos

**Billing**
- Email: billing@getreadin.us
- For payment and invoice questions

**Hours**
- Support: Monday-Friday, 9am-6pm EST
- Chat: 24/7 with AI assistance, human agents during business hours

**Self-Service**
- Help Center: getreadin.us/docs
- FAQ: getreadin.us/faq"""
    }
]


def seed_knowledge_base():
    """Seed the knowledge base with articles."""
    db = SessionLocal()

    try:
        # Check if articles already exist
        existing = db.query(KnowledgeBaseArticle).count()
        if existing > 0:
            print(f"Knowledge base already has {existing} articles.")
            user_input = input("Do you want to add more articles anyway? (y/n): ")
            if user_input.lower() != 'y':
                print("Aborted.")
                return

        # Add articles
        for article_data in ARTICLES:
            article = KnowledgeBaseArticle(
                title=article_data["title"],
                content=article_data["content"],
                summary=article_data["summary"],
                category=article_data["category"],
                tags=article_data["tags"],
                is_published=True
            )
            db.add(article)
            print(f"Added: {article_data['title']}")

        db.commit()
        print(f"\nSuccessfully added {len(ARTICLES)} articles to the knowledge base!")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_knowledge_base()
